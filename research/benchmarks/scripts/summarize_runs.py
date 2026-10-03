#!/usr/bin/env python3
"""Aggregate JSON score files without third-party dependencies."""

import argparse
import json
from pathlib import Path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("directory")
    a = p.parse_args()

    rows = []
    for path in sorted(Path(a.directory).glob("*.json")):
        with path.open(encoding="utf-8") as f:
            rows.append({"file": path.name, "result": json.load(f)})

    print(json.dumps({"count": len(rows), "runs": rows}, indent=2))

if __name__ == "__main__":
    main()
