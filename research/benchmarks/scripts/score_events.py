#!/usr/bin/env python3
"""Small dependency-free event scoring utility.

Input JSON:
{
  "truth": [{"timestamp": 10, "action": "open"}],
  "pred": [{"timestamp": 10.5, "action": "open"}]
}

This is intentionally simple. Domain-specific scoring belongs in a later
version after the event schema stabilizes.
"""

import argparse
import json

def normalize(s):
    return " ".join(str(s).lower().split())

def main():
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--tolerance", type=float, default=2.0)
    a = p.parse_args()

    with open(a.path, encoding="utf-8") as f:
        data = json.load(f)

    truth = data.get("truth", [])
    pred = data.get("pred", [])
    used = set()
    matches = 0

    for t in truth:
        best = None
        for i, q in enumerate(pred):
            if i in used:
                continue
            if normalize(t.get("action")) != normalize(q.get("action")):
                continue
            delta = abs(float(t["timestamp"]) - float(q["timestamp"]))
            if delta <= a.tolerance and (best is None or delta < best[0]):
                best = (delta, i)
        if best:
            matches += 1
            used.add(best[1])

    precision = matches / len(pred) if pred else 0.0
    recall = matches / len(truth) if truth else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0

    print(json.dumps({
        "matches": matches,
        "truth_count": len(truth),
        "prediction_count": len(pred),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tolerance_seconds": a.tolerance,
    }, indent=2))

if __name__ == "__main__":
    main()
