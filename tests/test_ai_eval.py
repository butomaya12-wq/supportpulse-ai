"""Labeled synthetic regression evaluation for the NON-LLM rules baseline only."""
import json
from datetime import datetime
from pathlib import Path
from app.ai_extract import propose


def test_synthetic_rules_baseline_confusion_matrix():
    dataset = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "ai_eval.json").read_text(encoding="utf-8"))
    event_time = datetime.fromisoformat(dataset["event_time"])
    tp = fp = tn = fn = 0
    for row in dataset["examples"]:
        predicted = propose(row["message"], event_time, "rules")["status"] == "PROPOSED"
        expected = row["promise"]
        tp += int(predicted and expected)
        fp += int(predicted and not expected)
        tn += int(not predicted and not expected)
        fn += int(not predicted and expected)
    assert (tp, fp, tn, fn) == (4, 0, 9, 0)
    # This is a *synthetic 13-case smoke eval*. It says nothing about real LLM precision or recall.
