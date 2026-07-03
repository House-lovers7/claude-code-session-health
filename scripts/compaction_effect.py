#!/usr/bin/env python3
"""Measure the effect of /compact on Claude Code sessions (read-only).

session-health (usage_report.py / the statusline) does not measure compaction.
This script scans Claude Code transcripts and, for each compaction event,
compares the live context size (input + cache_read + cache_creation per
assistant request) in the requests just BEFORE vs just AFTER the boundary.
Unlike day-over-day aggregates, this is not confounded by workload volume — it
is a direct measure of how much /compact actually shrinks the live context.

Detected event: a record with type=="system" and subtype=="compact_boundary".
Its compactMetadata (trigger / preTokens / durationMs) is paired with the mean
context size of the K assistant requests before and after it.

Usage:
    python3 compaction_effect.py [--k N] [--csv]

Local file reads only. Nothing leaves the machine.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import statistics
import sys

PROJECTS = os.path.expanduser("~/.claude/projects")
FIELDS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
# preTokens bands: the payoff of compaction depends on distance from the
# post-compaction floor (~50-64k), so bucket events by pre-compaction size.
BANDS = [(0, 100_000, "<100k"), (100_000, 200_000, "100-200k"),
         (200_000, 400_000, "200-400k"), (400_000, 10**12, ">=400k")]


def ctx_size(usage: dict) -> int:
    """Prompt-side tokens for one request (a proxy for live context size)."""
    return sum(usage.get(f) or 0 for f in FIELDS)


def scan_file(path: str):
    """Return an ordered sequence of ("B", pre, trig, dur) and ("A", ctx)."""
    seq = []
    for line in open(path, errors="ignore"):
        if '"assistant"' not in line and "compact_boundary" not in line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = o.get("type")
        if t == "system" and o.get("subtype") == "compact_boundary":
            m = o.get("compactMetadata") or {}
            seq.append(("B", m.get("preTokens"), m.get("trigger"), m.get("durationMs")))
        elif t == "assistant":
            u = (o.get("message") or {}).get("usage") or {}
            cs = ctx_size(u)
            if cs > 0:
                seq.append(("A", cs))
    return seq


def project_label(path: str) -> str:
    """Human-friendly project name from the encoded ~/.claude/projects dir."""
    raw = os.path.basename(os.path.dirname(path))
    return re.sub(r"^-?Users-[^-]+-(projects-)?", "", raw)[:34] or raw[:34]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=4,
                    help="assistant requests to average on each side of a boundary (default 4)")
    ap.add_argument("--csv", action="store_true", help="one row per event as CSV")
    args = ap.parse_args()
    K = args.k

    events = []  # (trigger, preTokens, durationMs, ctx_before, ctx_after, project)
    files = glob.glob(os.path.join(PROJECTS, "*", "*.jsonl"))
    files += glob.glob(os.path.join(PROJECTS, "*", "*", "subagents", "*.jsonl"))
    for f in files:
        seq = scan_file(f)
        if not any(x[0] == "B" for x in seq):
            continue
        proj = project_label(f)
        for i, x in enumerate(seq):
            if x[0] != "B":
                continue
            before = [s[1] for s in seq[max(0, i - 2 * K):i] if s[0] == "A"][-K:]
            after = [s[1] for s in seq[i + 1:i + 1 + 3 * K] if s[0] == "A"][:K]
            if not before or not after:
                continue
            mb = sum(before) / len(before)
            ma = sum(after) / len(after)
            events.append((x[2], x[1], x[3], mb, ma, proj))

    if not events:
        print("No compaction events found.", file=sys.stderr)
        return 1

    def drop(mb, ma):
        return 100 * (mb - ma) / mb if mb else 0.0

    if args.csv:
        print("trigger,preTokens,durationMs,ctx_before,ctx_after,drop_pct,project")
        for trig, pre, dur, mb, ma, proj in events:
            print(f"{trig},{pre},{dur},{mb:.0f},{ma:.0f},{drop(mb, ma):.0f},{proj}")
        return 0

    print(f"{'project':34s} {'trig':7s} {'preTok':>8s} {'ctx_before':>11s} {'ctx_after':>10s} {'drop%':>6s}")
    for trig, pre, dur, mb, ma, proj in sorted(events, key=lambda e: -(e[1] or 0)):
        print(f"{proj:34s} {str(trig):7s} {str(pre):>8s} {mb:>11.0f} {ma:>10.0f} {drop(mb, ma):>5.0f}%")

    drops = [drop(mb, ma) for _, _, _, mb, ma, _ in events]
    floors = [ma for _, _, _, _, ma, _ in events]
    print()
    print(f"events: {len(events)}  |  median context drop {statistics.median(drops):.0f}%  "
          f"|  median post-compaction floor {statistics.median(floors):,.0f} tok")

    print("\n-- by trigger --")
    for trig in sorted({e[0] for e in events}, key=str):
        d = [drop(mb, ma) for t, _, _, mb, ma, _ in events if t == trig]
        print(f"  {str(trig):8s} n={len(d):2d}  median drop {statistics.median(d):.0f}%")

    print("\n-- by preTokens band (earlier compaction = smaller payoff) --")
    for lo, hi, name in BANDS:
        d = [drop(mb, ma) for _, pre, _, mb, ma, _ in events if lo <= (pre or 0) < hi]
        if d:
            print(f"  {name:9s} n={len(d):2d}  median drop {statistics.median(d):.0f}%")
    print("\nNote: the post-compaction floor is ~50-64k tokens. A manual /compact "
          "below ~2x\n      that floor barely helps; let it run higher (or let auto "
          "fire) for a better cut.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
