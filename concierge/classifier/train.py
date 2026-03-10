"""DistilBERT classifier training and ONNX export.

Fine-tunes distilbert-base-uncased on synthetic training data (2000 examples,
4 classes: REPLY, QUERY, CONVERSE, COMMAND) and exports to quantized ONNX.

Usage:
    uv run python -m concierge.classifier.train

The script reads training data from concierge/classifier/training_data/*.jsonl,
trains the model, and writes the quantized ONNX model to
concierge/classifier/model.onnx.
"""

# Design rationale:
# Fine-tuning DistilBERT on synthetic data gives ~5ms inference at INT8
# precision, compared to ~500ms-2s for LLM-based classification.  The
# training data is LLM-generated (one agent per class, 500 examples each)
# to avoid the chicken-and-egg problem of needing real user data before
# the concierge is deployed.  INT8 quantization halves the model size
# (~250MB -> ~65MB) with negligible accuracy loss for text classification.
# The label encoding (REPLY=0, QUERY=1, CONVERSE=2, COMMAND=3) matches
# the _CLASS_MAP in model.py exactly.

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, random_split
from transformers import (
    AutoTokenizer,
    DistilBertForSequenceClassification,
    get_linear_schedule_with_warmup,
)

logger = logging.getLogger(__name__)

LABEL_MAP = {"REPLY": 0, "QUERY": 1, "CONVERSE": 2, "COMMAND": 3}
MODEL_NAME = "distilbert-base-uncased"
MAX_LENGTH = 128
BATCH_SIZE = 16
LEARNING_RATE = 2e-5
MAX_EPOCHS = 5
PATIENCE = 2
WARMUP_RATIO = 0.1

TRAINING_DATA_DIR = Path(__file__).parent / "training_data"
OUTPUT_PATH = Path(__file__).parent / "model.onnx"


class ClassificationDataset(Dataset):
    def __init__(self, texts: list[str], labels: list[int], tokenizer):
        self.encodings = tokenizer(
            texts, max_length=MAX_LENGTH, truncation=True,
            padding="max_length", return_tensors="pt",
        )
        self.labels = torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return {
            "input_ids": self.encodings["input_ids"][idx],
            "attention_mask": self.encodings["attention_mask"][idx],
            "labels": self.labels[idx],
        }


def load_training_data() -> tuple[list[str], list[int]]:
    """Load all JSONL files from the training_data directory."""
    texts, labels = [], []
    for path in sorted(TRAINING_DATA_DIR.glob("*.jsonl")):
        with open(path) as f:
            for line in f:
                obj = json.loads(line)
                texts.append(obj["text"])
                labels.append(LABEL_MAP[obj["label"]])
    logger.info("Loaded %d examples (%d classes)", len(texts), len(set(labels)))
    return texts, labels


def train() -> dict[str, float]:
    """Fine-tune DistilBERT and export to quantized ONNX.

    Returns a dict of validation metrics.
    """
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    logger.info("Using device: %s", device)

    # Load data
    texts, labels = load_training_data()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    dataset = ClassificationDataset(texts, labels, tokenizer)

    # Train/val split (80/20, seeded for reproducibility)
    val_size = int(0.2 * len(dataset))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42),
    )
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE)

    # Model
    model = DistilBertForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABEL_MAP),
    ).to(device)

    # Optimizer + scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    total_steps = len(train_loader) * MAX_EPOCHS
    warmup_steps = int(WARMUP_RATIO * total_steps)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps,
    )

    # Training loop
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(1, MAX_EPOCHS + 1):
        # --- Train ---
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            loss = outputs.loss
            loss.backward()
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            train_loss += loss.item()

        train_loss /= len(train_loader)

        # --- Validate ---
        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                outputs = model(**batch)
                val_loss += outputs.loss.item()
                preds = outputs.logits.argmax(dim=-1)
                correct += (preds == batch["labels"]).sum().item()
                total += len(batch["labels"])

        val_loss /= len(val_loader)
        val_accuracy = correct / total

        logger.info(
            "Epoch %d/%d -- train_loss=%.4f val_loss=%.4f val_acc=%.4f",
            epoch, MAX_EPOCHS, train_loss, val_loss, val_accuracy,
        )

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            # Save best model state
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                logger.info("Early stopping at epoch %d", epoch)
                break

    # Restore best model
    model.load_state_dict(best_state)
    model = model.to("cpu")
    model.eval()

    # --- ONNX export ---
    unquantized_path = OUTPUT_PATH.with_suffix(".unquantized.onnx")
    dummy = tokenizer("hello", return_tensors="pt", max_length=MAX_LENGTH,
                      padding="max_length", truncation=True)
    torch.onnx.export(
        model,
        (dummy["input_ids"], dummy["attention_mask"]),
        str(unquantized_path),
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch"},
            "attention_mask": {0: "batch"},
            "logits": {0: "batch"},
        },
        opset_version=14,
        dynamo=False,
    )

    # --- INT8 quantization ---
    from onnxruntime.quantization import QuantType, quantize_dynamic
    try:
        quantize_dynamic(
            str(unquantized_path),
            str(OUTPUT_PATH),
            weight_type=QuantType.QInt8,
        )
        unquantized_path.unlink()
    except Exception:
        logger.warning(
            "INT8 quantization failed, using unquantized model", exc_info=True,
        )
        unquantized_path.rename(OUTPUT_PATH)

    model_size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    logger.info("Model exported to %s (%.1f MB)", OUTPUT_PATH, model_size_mb)

    # --- Final validation ---
    from onnxruntime import InferenceSession
    ort_session = InferenceSession(str(OUTPUT_PATH))

    onnx_correct = 0
    onnx_total = 0
    for batch in val_loader:
        inputs = {
            "input_ids": batch["input_ids"].numpy(),
            "attention_mask": batch["attention_mask"].numpy(),
        }
        ort_inputs = {k: v for k, v in inputs.items()
                      if k in {i.name for i in ort_session.get_inputs()}}
        logits = ort_session.run(None, ort_inputs)[0]
        preds = np.argmax(logits, axis=-1)
        onnx_correct += (preds == batch["labels"].numpy()).sum()
        onnx_total += len(batch["labels"])

    onnx_accuracy = onnx_correct / onnx_total

    metrics = {
        "val_accuracy": val_accuracy,
        "onnx_accuracy": float(onnx_accuracy),
        "model_size_mb": model_size_mb,
        "epochs_trained": epoch,
        "best_val_loss": best_val_loss,
    }
    logger.info("Metrics: %s", metrics)

    if onnx_accuracy < 0.85:
        logger.warning(
            "ONNX accuracy %.2f is below 85%% threshold -- "
            "consider regenerating training data", onnx_accuracy,
        )

    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    metrics = train()
    print(f"\nTraining complete:")
    print(f"  Val accuracy:  {metrics['val_accuracy']:.2%}")
    print(f"  ONNX accuracy: {metrics['onnx_accuracy']:.2%}")
    print(f"  Model size:    {metrics['model_size_mb']:.1f} MB")
    print(f"  Epochs:        {metrics['epochs_trained']}")
    if metrics["onnx_accuracy"] >= 0.85:
        print(f"\nModel ready at concierge/classifier/model.onnx")
    else:
        print(f"\nAccuracy below threshold -- review training data")
        sys.exit(1)
