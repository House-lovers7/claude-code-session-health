# session-health

**95% of my Claude Code tokens were cache re-reads — not output.** This plugin
detects when a session enters that token-wasting phase and, unlike
monitoring-only tools, closes the loop: it tells *the model itself* to propose
`/compact` and delegate to subagents, and surfaces "time to cut this session"
in your statusline and notifications.

日本語版は [README.ja.md](README.ja.md) へ。

## The problem

Prompt caching in Claude Code is automatic and cheap per token — but every
request re-reads the entire cached context. Run one session for a few hours
and the numbers look like this (measured on a real day of work, 12 projects):

```
input      736k
output     1.4M
cacheRead  284.7M   <- 95% of all tokens
```

The worst sessions had a **cacheRead/output ratio of 200–300x**. A statusline
warning alone didn't change behavior (mine was ignored past 2x the threshold).
What worked was making the *model* aware: once the session crosses a
threshold, every prompt carries an injected instruction to wrap up, compact,
and delegate.

## What it does

One detection engine (`scripts/session_health.py`), three surfaces:

| Surface | Mechanism | What you see |
|---|---|---|
| **Model self-correction** | `UserPromptSubmit` hook (installed automatically) | When hot, the model starts proposing `/compact` / a fresh session at task boundaries and delegates exploration to subagents |
| **Statusline** | optional, see below | `📜req56·120x` → `🟡` → `🔥req231·246x ⚠️/compact` |
| **Stop notification** | optional, see below | your "response done" notification gains ` \| cut point: req231 / re-read 246x -> /compact` |

Plus `/session-health:usage-report`: a token breakdown of the last day across
**project × session × subagent × model**, with request-level deduplication
(streaming writes each request as multiple JSONL records — naive summing
double-counts 2–3x) and subagent transcripts included (they live in separate
files under `<session>/subagents/`; miss them and delegation looks like zero).

Everything runs on local transcript files. **Nothing leaves your machine.**

## Security / What this installs

Claude Code plugins are powerful — they can add commands, hooks, agents, and
MCP servers, so being wary of a plugin from a personal repository is the
correct instinct. Here is exactly what this one adds.

This plugin installs:

- one slash command: `/session-health:usage-report`
- one `UserPromptSubmit` hook that runs `scripts/session_health.py hook`

It does not install:

- MCP servers
- external integrations
- background daemons
- network calls
- dependencies outside the Python standard library

All analysis is performed on local Claude Code transcript files under
`~/.claude/projects/`. Nothing leaves your machine.

If you'd rather verify than trust: read [`hooks/hooks.json`](hooks/hooks.json)
first — it declares exactly when Claude Code runs what — then the two scripts
under [`scripts/`](scripts/) and [`commands/usage-report.md`](commands/usage-report.md).

## Install

```
/plugin marketplace add House-lovers7/claude-code-session-health
/plugin install session-health@house-lovers7
```

The hook and `/session-health:usage-report` work immediately. Two optional surfaces:

**Statusline** — see [`scripts/statusline-example.sh`](scripts/statusline-example.sh),
or add one line to your existing statusline script:

```bash
health=$(printf '%s' "$input" | python3 "<plugin>/scripts/session_health.py" statusline 2>/dev/null)
```

**Stop notification** — append the `status` mode output to whatever
notification you already send from a Stop hook:

```bash
extra=$(printf '%s' "$input" | python3 "<plugin>/scripts/session_health.py" status 2>/dev/null)
notify "response done$extra"
```

## Thresholds

Defaults: **hot** at 80 requests or a 150x cacheRead/output ratio; **warn**
(statusline marker only) at 50 requests or 100x. Override via environment
variables — see the header of
[`scripts/session_health.py`](scripts/session_health.py) for the full list
(`SESSION_HEALTH_HOT_REQS`, `SESSION_HEALTH_HOT_RATIO`, ...).

The hook re-fires at most once every 20 requests, and each injection is ~60
tokens, so the correction itself stays cheap.

## How this differs from existing tools

Great monitoring tools already exist — [ccusage](https://github.com/ryoppippi/ccusage)
for cost reports, [Claude HUD](https://github.com/jarrodwatts/claude-hud) for
context visibility. They are read-only: they inform *you*. This plugin's bet
is that the cheapest intervention point is **the model's own behavior** — an
injected instruction at the right moment beats a dashboard you stop looking
at. To my knowledge no existing tool does threshold-triggered self-correction
(survey as of 2026-07; happy to be corrected via issues).

## Requirements

- Claude Code with plugin support
- Python 3.8+ (stdlib only)

## License

MIT
