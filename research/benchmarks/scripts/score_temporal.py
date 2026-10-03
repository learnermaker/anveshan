#!/usr/bin/env python3
"""Deterministic temporal scoring for predicted timestamps.

Usage:
  python score_temporal.py --truth 22.0 --pred 21.4 --tolerance 2.0
"""

import argparse

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--truth", type=float, required=True)
    p.add_argument("--pred", type=float, required=True)
    p.add_argument("--tolerance", type=float, default=2.0)
    a = p.parse_args()
    error = abs(a.truth - a.pred)
    print({
        "absolute_error_seconds": error,
        "pass": error <= a.tolerance,
        "tolerance_seconds": a.tolerance,
    })

if __name__ == "__main__":
    main()
