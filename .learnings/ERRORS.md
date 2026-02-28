# Errors Log — Devin
---

## Entry Template
- ID: ERR-YYYYMMDD-XXX
- Logged: YYYY-MM-DD HH:MM UTC
- Agent: Devin
- Priority: Low | Medium | High | Critical
- Status: Open | Investigating | Resolved | Won't Fix
- Area: <component/tool/workflow>
- Summary: <short description>
- Details: <what failed, command/output, context>
- Suggested Fix: <proposed remediation>
- Metadata: <tags, related IDs, links, environment>

## ERR-20260227-001
- ID: ERR-20260227-001
- Logged: 2026-02-27 09:41 UTC
- Agent: Devin
- Priority: Medium
- Status: Resolved
- Area: Version Control / Workspace
- Summary: `git status --short` failed because workspace is not a git repository.
- Details: Command output: "fatal: not a git repository (or any of the parent directories): .git" (exit code 128).
- Suggested Fix: Initialize a repository with `git init` or run git commands in the correct repo root.
- Metadata: command="git status --short"; cwd="/home/jy/.openclaw/workspace-devin"; exit_code=128

## ERR-20260228-002
- ID: ERR-20260228-002
- Logged: 2026-02-28 14:52 UTC
- Agent: Devin
- Priority: Medium
- Status: Open
- Area: Environment / Dependencies
- Summary: Scanner runtime failed due missing Python dependency (`pandas`).
- Details: `python3 openbb_earnings_iv_scanner.py` exited with `ModuleNotFoundError: No module named 'pandas'`.
- Suggested Fix: Install dependencies: `python3 -m pip install openbb pandas numpy` then rerun.
- Metadata: command="python3 openbb_earnings_iv_scanner.py"; cwd="/home/jy/.openclaw/workspace-devin"; exit_code=1

## ERR-20260228-003
- ID: ERR-20260228-003
- Logged: 2026-02-28 15:18 UTC
- Agent: Devin
- Priority: High
- Status: Resolved
- Area: OpenBB API Compatibility
- Summary: Earnings calendar endpoint call failed due path/signature mismatch across OpenBB versions/providers.
- Details: Runtime error showed all attempted paths failed for bulk symbol call; last observed error referenced missing path token (`stocks`).
- Suggested Fix: Remove deprecated path, add multi-signature attempts (`symbol`/`symbols`, with and without date range), and add per-symbol fallback normalization.
- Metadata: file=openbb_earnings_iv_scanner.py; related=LRN-20260227-001
