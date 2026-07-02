---
description: Token usage breakdown by project / session / agent / model (local transcripts, deduplicated)
allowed-tools: Bash(python3:*)
---

## Result

!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/usage_report.py" $ARGUMENTS`

Useful arguments:
- `--project NAME`: scan only matching project directories.
- `--current PATH`: scan one current-session transcript.
- `--transcript PATH`: scan one transcript file.

Present the output above as-is, then add a 1-2 line observation: is the
cache re-read share and main-thread share healthy for a
"main model as orchestrator, delegate implementation to subagents" workflow?
If it has degraded, suggest exactly one countermeasure — either cutting
sessions shorter or delegating more — whichever will help most.
No further analysis or investigation.
