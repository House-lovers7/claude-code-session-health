#!/usr/bin/env python3
"""Session health engine for Claude Code.

Detects sessions that have entered the "token-wasting phase": long-running
conversations where every request re-reads a huge cached context, so cache-read
tokens dwarf actual output (200x+ is common). Measured on real workloads,
~95% of all consumed tokens can be context re-reads.

Reads the hook input JSON from stdin (Claude Code passes transcript_path and
session_id to every hook). Local file reads only — nothing leaves the machine.

Modes (first CLI argument):
  hook        (default) For the UserPromptSubmit hook. When the session crosses
              the "hot" threshold, injects corrective instructions into the
              model's context: propose /compact or a fresh session at the next
              natural boundary, and delegate exploration to subagents. Fires at
              most once every SESSION_HEALTH_REWARN_EVERY requests.
  status      For Stop-hook notifications. Prints a short suffix such as
              " | cut point: req231 / re-read 246x -> /compact" when hot,
              nothing otherwise. Append it to your notification message.
  statusline  For statusline scripts. Always prints a compact segment like
              "req56 120x" with a marker when warn or hot. Results are cached
              until the transcript grows by SESSION_HEALTH_CACHE_DELTA bytes,
              so it adds no perceptible latency.

Thresholds (override via environment variables):
  SESSION_HEALTH_HOT_REQS=80      hot when requests reach this count
  SESSION_HEALTH_HOT_RATIO=150    ... or cacheRead/output ratio reaches this
  SESSION_HEALTH_WARN_REQS=50     warn level (statusline marker only)
  SESSION_HEALTH_WARN_RATIO=100
  SESSION_HEALTH_REWARN_EVERY=20  hook re-fires every N requests while hot
  SESSION_HEALTH_CACHE_DELTA=100000  statusline re-scan threshold in bytes

All failure paths are silent (exit 0) so a broken transcript can never block
a prompt from being submitted.
"""
import json
import os
import sys


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


HOT_REQS = _env_int("SESSION_HEALTH_HOT_REQS", 80)
HOT_RATIO = _env_int("SESSION_HEALTH_HOT_RATIO", 150)
HOT_RATIO_MIN_REQS = 20
WARN_REQS = _env_int("SESSION_HEALTH_WARN_REQS", 50)
WARN_RATIO = _env_int("SESSION_HEALTH_WARN_RATIO", 100)
WARN_RATIO_MIN_REQS = 10
REWARN_EVERY = _env_int("SESSION_HEALTH_REWARN_EVERY", 20)
CACHE_DELTA_BYTES = _env_int("SESSION_HEALTH_CACHE_DELTA", 100_000)
# Reset the counters at each compaction so the figures describe the CURRENT
# live segment (since the last /compact), which is what /compact actually
# shrinks. SESSION_HEALTH_CUMULATIVE=1 restores the legacy whole-transcript sum.
CUMULATIVE = os.environ.get("SESSION_HEALTH_CUMULATIVE", "") == "1"
FIELDS = ["input_tokens", "output_tokens", "cache_read_input_tokens",
          "cache_creation_input_tokens"]
STATE_DIR = os.path.expanduser("~/.claude/.state/session-health")


def scan(transcript_path):
    """Return (request_count, output_tokens, cache_read_tokens).

    Deduplicates by requestId: streaming writes the same request as multiple
    JSONL records, so summing raw lines would double-count massively.

    Compaction-aware: the counters reset at every ``compact_boundary`` record,
    so the returned figures describe the CURRENT live segment (since the last
    /compact) rather than the whole transcript. Without this, req count and the
    cacheRead/output ratio never fall after a /compact even though the model's
    live context shrank, so the statusline/hook kept nagging to compact again.
    Set SESSION_HEALTH_CUMULATIVE=1 to restore the legacy whole-transcript sum.
    """
    reqs = out_tok = cache_rd = 0
    seen = set()
    with open(transcript_path, errors="replace") as fh:
        for line in fh:
            if not CUMULATIVE and "compact_boundary" in line:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    rec = None
                if rec and rec.get("type") == "system" \
                        and rec.get("subtype") == "compact_boundary":
                    reqs = out_tok = cache_rd = 0
                    seen = set()
                    continue
            if '"assistant"' not in line or '"usage"' not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "assistant":
                continue
            msg = rec.get("message") or {}
            usage = msg.get("usage") or {}
            if msg.get("model") == "<synthetic>" or not any(
                    usage.get(f) for f in FIELDS):
                continue
            req = rec.get("requestId") or msg.get("id")
            if req:
                if req in seen:
                    continue
                seen.add(req)
            reqs += 1
            out_tok += usage.get("output_tokens") or 0
            cache_rd += usage.get("cache_read_input_tokens") or 0
    return reqs, out_tok, cache_rd


def level(reqs, ratio):
    if reqs >= HOT_REQS or (reqs >= HOT_RATIO_MIN_REQS and ratio >= HOT_RATIO):
        return "hot"
    if reqs >= WARN_REQS or (reqs >= WARN_RATIO_MIN_REQS and ratio >= WARN_RATIO):
        return "warn"
    return "ok"


def read_state(name):
    try:
        with open(os.path.join(STATE_DIR, name)) as fh:
            return fh.read().strip()
    except OSError:
        return ""


def write_state(name, value):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(os.path.join(STATE_DIR, name), "w") as fh:
            fh.write(value)
    except OSError:
        pass


def mode_hook(transcript_path, session_id):
    reqs, out_tok, cache_rd = scan(transcript_path)
    ratio = cache_rd / out_tok if out_tok else 0
    if level(reqs, ratio) != "hot":
        return
    try:
        last = int(read_state(session_id) or -REWARN_EVERY)
    except ValueError:
        last = -REWARN_EVERY
    if reqs - last < REWARN_EVERY:
        return
    write_state(session_id, str(reqs))
    ctx = (f"Session health warning: this session has reached {reqs} requests "
           f"with a cacheRead/output ratio of {ratio:.0f}x — token consumption "
           "is now dominated by context re-reads. "
           "(1) At the next natural task boundary, suggest /compact or "
           "continuing in a fresh session to the user. "
           "(2) From here on, delegate exploration and routine edits to "
           "subagents, and avoid pulling raw logs or whole files into the "
           "main context.")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": ctx,
        }
    }, ensure_ascii=False))


def mode_status(transcript_path, session_id):
    reqs, out_tok, cache_rd = scan(transcript_path)
    ratio = cache_rd / out_tok if out_tok else 0
    if level(reqs, ratio) == "hot":
        print(f" | cut point: req{reqs} / re-read {ratio:.0f}x -> /compact",
              end="")


def mode_statusline(transcript_path, session_id):
    size = os.path.getsize(transcript_path)
    cached = read_state(f"statusline-{session_id}")
    if cached:
        parts = cached.split("\t", 1)
        try:
            cached_size = int(parts[0])
            fresh = 0 <= size - cached_size < CACHE_DELTA_BYTES
            if fresh and size > cached_size and not CUMULATIVE:
                # A compaction appends a compact_boundary record far smaller
                # than CACHE_DELTA_BYTES, so a size-only check would keep
                # showing the stale hot segment. Scan just the appended tail.
                with open(transcript_path, errors="replace") as fh:
                    fh.seek(cached_size)
                    if "compact_boundary" in fh.read():
                        fresh = False
            if fresh:
                print(parts[1] if len(parts) > 1 else "", end="")
                return
        except (ValueError, OSError):
            pass
    reqs, out_tok, cache_rd = scan(transcript_path)
    ratio = cache_rd / out_tok if out_tok else 0
    lv = level(reqs, ratio)
    if reqs == 0:
        seg = ""
    elif lv == "hot":
        seg = f"🔥req{reqs}·{ratio:.0f}x ⚠️/compact"
    elif lv == "warn":
        seg = f"🟡req{reqs}·{ratio:.0f}x"
    else:
        seg = f"req{reqs}·{ratio:.0f}x"
    write_state(f"statusline-{session_id}", f"{size}\t{seg}")
    print(seg, end="")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "hook"
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    transcript_path = data.get("transcript_path") or ""
    session_id = data.get("session_id") or "unknown"
    if not transcript_path or not os.path.exists(transcript_path):
        return
    try:
        {"hook": mode_hook, "status": mode_status,
         "statusline": mode_statusline}.get(mode, mode_hook)(
             transcript_path, session_id)
    except OSError:
        return


if __name__ == "__main__":
    main()
