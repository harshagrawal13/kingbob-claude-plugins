---
name: session-limit-guard
description: Run a long task while guarding the Claude 5-hour session usage limit — pause automatically when usage reaches a threshold (default 90%), sleep until the window resets, then resume the task where it left off. Use when the user asks to pace a long task around usage limits, says "pause before I hit my session limit", "don't burn through my limit", "resume after my limit resets", or "/session-limit-guard <task>".
argument-hint: "[threshold%] <task to run>"
user-invocable: true
allowed-tools: Bash(bash:*), Read, Write
---

# Session limit guard

Wraps a long-running task so the session never slams into the 5-hour usage limit mid-work: at ≥ THRESHOLD% utilization (default 90), park the task safely, sleep until the window resets, then resume automatically. The wrapped task itself uses whatever tools it normally would (normal permission flow); `allowed-tools` above covers only the guard machinery.

## How usage is read

Claude Code sends a `rate_limits` block (5-hour and 7-day `used_percentage` + `resets_at`) to the configured statusline command after every API response. A small hook in the user's statusline script caches that block to `~/.claude/state/rate-limits.json`; the scripts here read the cache. No network calls, no credentials, no undocumented APIs.

Scripts live in `scripts/` next to this SKILL.md (resolve the absolute path from where this skill was loaded, or via `$CLAUDE_PLUGIN_ROOT/skills/session-limit-guard/scripts/` if that variable is set):

- `check_usage.sh [threshold]` — prints `five_hour_pct=… resets_at=… resets_in_s=…` and a `status=` line. Exit 0 = OK, exit 2 = PAUSE (at/over threshold), exit 3 = no data.
- `wait_for_reset.sh <resets_at_epoch> [buffer_s]` — sleeps until 2 minutes past the reset time, then exits. **Must be launched with `run_in_background: true`** so its completion re-invokes Claude.
- `setup_statusline_cache.sh` — one-time, idempotent install of the statusline cache hook (see First-run setup).

## Arguments

`/kingbob:session-limit-guard [threshold%] <task…>` — if the first token is a bare number (e.g. `85`), use it as the threshold; otherwise threshold is 90. Everything else is the task to perform.

## First-run setup

If `check_usage.sh` exits 3 with `reason=cache_missing`, run `setup_statusline_cache.sh` once:

- It edits the user's statusline script in place (idempotent, marker-guarded, leaves a `.bak`), or installs a minimal statusline if none is configured.
- If it exits 2 (`MANUAL_SETUP_REQUIRED`), it printed the exact block to add — show it to the user, ask them to wire it in, and continue the task unguarded in the meantime.
- After install, data appears once the next API response refreshes the statusline (Pro/Max subscriptions only — API-key billing has no session limit, so the guard is a no-op there).

## Procedure

1. **At start**: run `check_usage.sh <threshold>`. Report the current percentage and reset time to the user in one line. If it already says `status=PAUSE`, go straight to the pause procedure (step 4) before doing any work.
2. **Work on the task normally**, but run `check_usage.sh <threshold>` at checkpoints: after finishing each natural subtask, and at least every ~10–15 minutes of sustained tool activity. Don't run it more often than every couple of minutes — it's account-wide data; it doesn't change fast.
3. **Exit 3 (NO_DATA)**: run first-run setup (above) if the cache file is missing; otherwise mention it once, keep working, and retry at the next checkpoint. If data never appears, tell the user the guard is inactive and finish the task unguarded.
4. **Exit 2 (PAUSE)** — pause procedure:
   a. Finish the current step to a safe point first — never leave a half-applied edit or a dangling state. If mid-edit, complete the file write; if mid-investigation, jot conclusions.
   b. Write a progress file `slg-progress.md` in the working directory (or the job tmp dir for background jobs) containing: the original task verbatim, the threshold, what is done, exactly what to do next, and any key file paths / decisions / gotchas needed to resume cold. This file is the resume anchor if context gets summarized during the sleep.
   c. Launch the wait: Bash tool, `run_in_background: true`, command
      `bash <scripts dir>/wait_for_reset.sh <resets_at from check_usage>`.
   d. End the turn with a short message: current usage %, the local time you'll resume, and where the progress file is. This is a pause, not a completion — don't report the task as done.
5. **On wake** (the background command exits and re-invokes you):
   a. Run `check_usage.sh <threshold>` — expect `status=OK` (possibly `note=window_reset_since_cache`, which is fine: the cache is stale-high until the next API response refreshes it).
   b. If it still says PAUSE with a *future* resets_at (edge case: the new window is already loaded), launch `wait_for_reset.sh` again with the new resets_at.
   c. Re-read `slg-progress.md`, tell the user you're resuming, and continue the task. Keep checkpointing as in step 2 — a very long task may pause more than once.
6. **Weekly limit**: if `check_usage.sh` prints `weekly_warning=1`, do NOT auto-sleep — the 7-day window can be days from reset. Park the task safely (progress file as in 4b), tell the user the weekly limit is nearly exhausted, and stop to let them decide.

## Failure modes

- Background wait killed early (machine slept past it, session terminated): on any unexpected re-invocation, run `check_usage.sh` first; if still over threshold and resets_at is in the future, just relaunch `wait_for_reset.sh`.
- `~/.claude/state/rate-limits.json` very stale (`age_s` > ~1 hour) while other sessions are supposedly active: trust `resets_at` arithmetic over the percentage, and say the reading may be stale.
- Never fabricate usage numbers: if the scripts report garbage or nothing, say so verbatim and continue unguarded rather than guessing.
