#!/usr/bin/env python3
"""Token usage breakdown for Claude Code: project x session x agent x model.

usage: python3 usage_report.py [since_iso]
  since_iso  ISO-8601 start time, e.g. 2026-07-02T04:00:00+09:00.
             Defaults to today 04:00 local time.

Scans ~/.claude/projects/**/*.jsonl transcripts, including subagent
transcripts, which live in separate files under
<project>/<sessionId>/subagents/agent-*.jsonl (an easy blind spot: scanning
only the top-level session files makes delegation look like zero).

Records are deduplicated by requestId — streaming writes one request as
multiple JSONL records, so naive summing double-counts by 2-3x.

Local file reads only. Nothing leaves the machine.
"""
import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

FIELDS = ["input_tokens", "output_tokens", "cache_read_input_tokens",
          "cache_creation_input_tokens"]


def default_since() -> datetime:
    now = datetime.now().astimezone()
    since = now.replace(hour=4, minute=0, second=0, microsecond=0)
    if now < since:
        since -= timedelta(days=1)
    return since.astimezone(timezone.utc)


def fmt(n: float) -> str:
    for unit, div in (("B", 1e9), ("M", 1e6), ("k", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return str(int(n))


def short_project(dirname: str) -> str:
    """Claude Code encodes the project cwd into the directory name by
    replacing path separators with '-'. Strip the home-directory prefix so
    the report shows readable project names on any machine."""
    home = os.path.expanduser("~").replace("/", "-")
    if dirname.startswith(home):
        return dirname[len(home):].lstrip("-") or "~"
    return dirname


def main() -> None:
    since = (datetime.fromisoformat(sys.argv[1]).astimezone(timezone.utc)
             if len(sys.argv) > 1 else default_since())
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%S")

    agg = defaultdict(lambda: defaultdict(int))
    slug_by_session = {}
    retries = defaultdict(int)
    api_errors = defaultdict(int)
    seen_req = set()
    dup_tokens = 0

    root = os.path.expanduser("~/.claude/projects")
    paths = glob.glob(os.path.join(root, "*", "*.jsonl"))
    paths += glob.glob(os.path.join(root, "*", "*", "subagents", "*.jsonl"))
    for path in paths:
        if os.path.getmtime(path) < since.timestamp():
            continue
        rel = os.path.relpath(path, root)
        project = short_project(rel.split(os.sep)[0])
        agent_type = None
        if os.sep + "subagents" + os.sep in path:
            agent_type = "(subagent)"
            meta_path = path[:-len(".jsonl")] + ".meta.json"
            try:
                with open(meta_path) as mf:
                    agent_type = json.load(mf).get("agentType") or agent_type
            except (OSError, json.JSONDecodeError):
                pass
        with open(path, errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = rec.get("timestamp") or ""
                if ts[:19] < since_iso:
                    continue
                sess = rec.get("sessionId") or os.path.basename(path)[:8]
                if rec.get("slug"):
                    slug_by_session.setdefault(sess, rec["slug"])
                if rec.get("retryAttempt"):
                    retries[(project, sess)] += 1
                if rec.get("isApiErrorMessage"):
                    api_errors[(project, sess)] += 1
                if rec.get("type") != "assistant":
                    continue
                msg = rec.get("message") or {}
                usage = msg.get("usage") or {}
                model = msg.get("model") or "?"
                if model == "<synthetic>" or not any(usage.get(f) for f in FIELDS):
                    continue
                req = rec.get("requestId") or msg.get("id")
                if req:
                    if req in seen_req:
                        dup_tokens += sum(usage.get(f) or 0 for f in FIELDS)
                        continue
                    seen_req.add(req)
                agent = agent_type or rec.get("agentName") or (
                    "(sidechain)" if rec.get("isSidechain") else "main")
                key = (project, sess, agent, model)
                for f in FIELDS:
                    agg[key][f] += usage.get(f) or 0
                agg[key]["requests"] += 1

    if not agg:
        print(f"since {since_iso}Z: no matching records")
        return

    def rollup(keyfn):
        out = defaultdict(lambda: defaultdict(int))
        for key, u in agg.items():
            k = keyfn(key)
            for f, v in u.items():
                out[k][f] += v
        return out

    def total(u):
        return sum(u[f] for f in FIELDS)

    def header(title):
        print(f"\n== {title} ==")
        print(f"{'':<44} {'in':>7} {'out':>8} {'cacheRd':>9} {'cacheCr':>9} {'req':>5}")

    def row(label, u):
        print(f"{label[:44]:<44} {fmt(u['input_tokens']):>7} {fmt(u['output_tokens']):>8}"
              f" {fmt(u['cache_read_input_tokens']):>9}"
              f" {fmt(u['cache_creation_input_tokens']):>9} {u['requests']:>5}")

    print(f"since {since_iso}Z (local {since.astimezone():%m/%d %H:%M})  "
          f"deduplicated away: {fmt(dup_tokens)} tok")

    header("By project")
    proj = rollup(lambda k: k[0])
    for p, u in sorted(proj.items(), key=lambda x: -total(x[1])):
        row(p, u)

    header("Top 15 sessions")
    sess = rollup(lambda k: (k[0], k[1]))
    models_by_sess = defaultdict(set)
    for (p, s, a, m), u in agg.items():
        models_by_sess[(p, s)].add(m.replace("claude-", ""))
    for (p, s), u in sorted(sess.items(), key=lambda x: -total(x[1]))[:15]:
        slug = slug_by_session.get(s, s[:8])
        out = u["output_tokens"] or 1
        note = f" cacheRd/out={u['cache_read_input_tokens'] / out:.0f}x"
        extra = ""
        if retries[(p, s)]:
            extra += f" retry={retries[(p, s)]}"
        if api_errors[(p, s)]:
            extra += f" apiErr={api_errors[(p, s)]}"
        row(f"{p[:20]}/{slug}", u)
        print(f"{'':<6}models={','.join(sorted(models_by_sess[(p, s)]))}{note}{extra}")

    header("By agent")
    ag = rollup(lambda k: k[2])
    for a, u in sorted(ag.items(), key=lambda x: -total(x[1])):
        row(a, u)

    header("Top 15 agent x model")
    am = rollup(lambda k: (k[2], k[3].replace("claude-", "")))
    for (a, m), u in sorted(am.items(), key=lambda x: -total(x[1]))[:15]:
        row(f"{a} / {m}", u)

    header("By model (cross-check)")
    mo = rollup(lambda k: k[3])
    g = defaultdict(int)
    for m, u in sorted(mo.items(), key=lambda x: -total(x[1])):
        row(m.replace("claude-", ""), u)
        for f, v in u.items():
            g[f] += v
    row("TOTAL", g)

    all_tok = total(g)
    if all_tok:
        main_tok = sum(total(u) for a, u in ag.items() if a == "main")
        print(f"\nHealth: cache re-reads "
              f"{100 * g['cache_read_input_tokens'] / all_tok:.0f}% of all "
              f"tokens (lower is better — the payoff metric for shorter "
              f"sessions) / main-thread share "
              f"{100 * main_tok / all_tok:.0f}% (delegation keeps this "
              f"moderate)")


if __name__ == "__main__":
    main()
