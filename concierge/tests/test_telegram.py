"""Tests for the Telegram bot module — handlers and config loading."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# python-telegram-bot is an optional dependency; skip if not installed
pytest.importorskip("telegram", reason="python-telegram-bot not installed")

from concierge.bridge.cc_connect import BridgeConfig, CLIBackend
from concierge.bridge import telegram as tg_mod
from concierge.models import MessageClass


def _make_config(tmp_path):
    return BridgeConfig(
        backend=CLIBackend.CLAUDE,
        telegram_token="123:abc",
        allowed_user_id=42,
        assistant_name="TestBot",
        data_dir=tmp_path,
    )


class TestHandleStart:
    @pytest.mark.asyncio
    async def test_sends_greeting(self, tmp_path):
        tg_mod._config = _make_config(tmp_path)
        try:
            update = MagicMock()
            update.message.reply_text = AsyncMock()
            ctx = MagicMock()

            await tg_mod.handle_start(update, ctx)

            update.message.reply_text.assert_called_once()
            msg = update.message.reply_text.call_args[0][0]
            assert "TestBot" in msg
        finally:
            tg_mod._config = None


class TestHandleError:
    @pytest.mark.asyncio
    async def test_sends_apology(self):
        update = MagicMock()
        update.effective_message.reply_text = AsyncMock()
        ctx = MagicMock()
        ctx.error = RuntimeError("test error")

        await tg_mod.handle_error(update, ctx)

        update.effective_message.reply_text.assert_called_once()
        msg = update.effective_message.reply_text.call_args[0][0]
        assert "wrong" in msg.lower()


class TestLoadConfigFromEnv:
    def test_missing_token_raises_system_exit(self):
        env = {k: v for k, v in os.environ.items() if k != "BUREAU_TELEGRAM_TOKEN"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(SystemExit, match="BUREAU_TELEGRAM_TOKEN"):
                tg_mod.load_config_from_env()

    def test_with_token_and_no_wizard_config(self, tmp_path):
        env = {
            "BUREAU_TELEGRAM_TOKEN": "123:abc",
            "BUREAU_TELEGRAM_USER_ID": "42",
        }
        with (
            patch.dict(os.environ, env),
            patch("concierge.bridge.telegram.load_config", return_value=None),
        ):
            cfg = tg_mod.load_config_from_env()
        assert cfg.telegram_token == "123:abc"
        assert cfg.allowed_user_id == 42
        assert cfg.backend == CLIBackend.CLAUDE


class TestHandleMessage:
    @pytest.mark.asyncio
    async def test_full_flow(self, tmp_path):
        """Verify the handler runs the full pipeline and replies."""
        tg_mod._config = _make_config(tmp_path)
        from concierge.pipeline.queue import PriorityQueue

        tg_mod._queue = PriorityQueue(max_size=50)

        try:
            update = MagicMock()
            update.message.text = "What should I have for dinner?"
            update.message.caption = None
            update.message.photo = []
            update.message.document = None
            update.message.date = MagicMock()
            update.message.reply_text = AsyncMock()
            update.effective_chat.send_action = AsyncMock()
            ctx = MagicMock()

            with patch(
                "concierge.bridge.telegram.generate_response",
                new_callable=AsyncMock,
                return_value="How about pasta?",
            ):
                await tg_mod.handle_message(update, ctx)

            update.message.reply_text.assert_called_once_with("How about pasta?")
        finally:
            tg_mod._config = None
            tg_mod._queue = None
