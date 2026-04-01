"""Telegram bot — long-polling I/O layer for the Bureau Concierge pipeline.

Receives messages via Telegram Bot API, feeds them through the classification
and feature-selection pipeline, generates LLM responses, and sends them back.
All handlers are filtered to a single allowed user ID for security.
"""

# Design rationale:
# Long-polling (not webhooks) because this is a single-user personal bot —
# no infrastructure beyond a running process is needed.  Session state is
# loaded/saved per message (stateless between messages) via the existing
# state.py persistence layer.  The PriorityQueue lives in-memory for the
# bot's lifetime and rebuilds naturally on restart; persistence isn't needed
# because feature candidates are ephemeral.  Background checks are wired
# into PTB's APScheduler-backed JobQueue so they run even when no messages
# arrive.  The typing indicator is sent before pipeline processing so the
# user sees immediate feedback.

from __future__ import annotations

import logging
import os
from pathlib import Path

from telegram import ChatAction, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from concierge.bridge.adapter import update_to_envelope
from concierge.bridge.cc_connect import BridgeConfig, CLIBackend
from concierge.bridge.response import generate_response
from concierge.classifier.classify import classify_message
from concierge.pipeline.orchestrator import run_pipeline
from concierge.pipeline.queue import PriorityQueue
from concierge.state import load_session_state, save_session_state

logger = logging.getLogger(__name__)

# Module-level state initialised in main() and shared across handlers.
# This avoids threading BridgeConfig through PTB's callback context.
_config: BridgeConfig | None = None
_queue: PriorityQueue | None = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Handlers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Respond to /start with a greeting."""
    assert _config is not None
    assert update.message is not None
    await update.message.reply_text(
        f"Hi! I'm {_config.assistant_name}. How can I help?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a single incoming message through the full Concierge pipeline.

    Steps: typing indicator -> envelope -> classify -> session update ->
    pipeline -> LLM response -> send reply -> persist state.
    """
    assert _config is not None
    assert _queue is not None
    assert update.message is not None
    assert update.effective_chat is not None

    # 1. typing indicator
    await update.effective_chat.send_action(ChatAction.TYPING)

    # 2. build envelope from extracted primitives
    has_photo = bool(update.message.photo)
    has_document = bool(update.message.document)
    has_attachment = has_photo or has_document

    attachment_type: str | None = None
    if has_photo:
        attachment_type = "photo"
    elif has_document:
        attachment_type = "document"

    envelope = update_to_envelope(
        text=update.message.text or update.message.caption or "",
        has_attachment=has_attachment,
        attachment_type=attachment_type,
        timestamp=update.message.date,
    )

    # 3. load session + classify
    session = load_session_state(_config.session_state_path)
    classify_message(envelope, session.active_feature_id)

    # 4. update session
    if envelope.classification is not None:
        session.record_classification(envelope.classification)
    session.last_message_at = envelope.timestamp

    # 5. run pipeline
    feature = run_pipeline(
        envelope, session, _queue, data_dir=_config.data_dir,
    )

    # 6. generate response
    response = await generate_response(
        envelope,
        feature,
        _config.data_dir,
        assistant_name=_config.assistant_name,
        backend=_config.backend.value,
    )

    # 7. send
    await update.message.reply_text(response)

    # 8. persist state
    save_session_state(session, _config.session_state_path)


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and send an apology to the user if possible."""
    logger.error("Update %s caused error: %s", update, context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "Something went wrong. I'll be back shortly."
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Background jobs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def register_background_jobs(
    job_queue: object,
    config: BridgeConfig,
) -> None:
    """Wire BackgroundRunner checks into PTB's APScheduler-backed job queue."""
    from telegram.ext import JobQueue as _JobQueue

    # runtime guard — job_queue may be None when PTB is built without the
    # optional job-queue extra
    if not isinstance(job_queue, _JobQueue):
        logger.warning("JobQueue unavailable; background checks disabled")
        return

    from concierge.background.runner import BackgroundRunner

    runner = BackgroundRunner(data_dir=config.data_dir)

    async def run_background(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        due = runner.get_due_checks()
        for check in due:
            runner.run_check(check)

    # run every hour, first run 10 s after startup
    job_queue.run_repeating(run_background, interval=3600, first=10)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Config + entry point
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def load_config_from_env() -> BridgeConfig:
    """Build a :class:`BridgeConfig` from environment + wizard config.

    The Telegram token is *always* read from the ``BUREAU_TELEGRAM_TOKEN``
    environment variable (never persisted in config files).
    """
    token = os.environ.get("BUREAU_TELEGRAM_TOKEN")
    if not token:
        raise SystemExit("BUREAU_TELEGRAM_TOKEN env var is required")

    from concierge.setup.wizard import load_config

    config_path = (
        Path.home() / ".config" / "bureau" / "concierge" / "bridge.yml"
    )
    wizard_config = load_config(config_path)

    if wizard_config is not None:
        return BridgeConfig(
            backend=wizard_config.backend,
            telegram_token=token,
            allowed_user_id=wizard_config.allowed_user_id,
            assistant_name=wizard_config.assistant_name,
            data_dir=wizard_config.data_dir,
        )

    # fallback when no wizard config exists
    return BridgeConfig(
        backend=CLIBackend.CLAUDE,
        telegram_token=token,
        allowed_user_id=int(os.environ.get("BUREAU_TELEGRAM_USER_ID", "0")),
        assistant_name="Concierge",
    )


def main() -> None:
    """Start the Telegram bot with long-polling."""
    global _config, _queue  # noqa: PLW0603 — module-level state shared across handlers

    _config = load_config_from_env()
    _queue = PriorityQueue(max_size=50)

    app = ApplicationBuilder().token(_config.telegram_token).build()

    # all handlers are filtered to the single allowed user
    user_filter = filters.User(_config.allowed_user_id)

    app.add_handler(CommandHandler("start", handle_start, filters=user_filter))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, handle_message),
    )
    app.add_handler(MessageHandler(filters.PHOTO & user_filter, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL & user_filter, handle_message))
    app.add_error_handler(handle_error)

    register_background_jobs(app.job_queue, _config)

    logger.info(
        "Starting Concierge bot (backend=%s, user=%d)",
        _config.backend.value,
        _config.allowed_user_id,
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)
