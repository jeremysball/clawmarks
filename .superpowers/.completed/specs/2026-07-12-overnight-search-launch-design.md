# Launching an overnight search run from the web UI

Design only, per the continuation prompt's item 6: plan a way to start a search run
(`search/driver.py`, currently invoked by hand as `python3 -m clawmarks.search.driver --round N`)
from `curation_server.py`'s browser UI, gated on RunPod idle-billing safety and the project's
data-integrity rails. Not implemented.

## What the driver already does, and doesn't

`search/driver.py` submits generation jobs to the same serverless ComfyUI endpoint
`curation_server.py`'s counterfactual feature already uses (`comfyui.py`, pay-per-job, not an
always-on pod), so the RunPod idle-billing risk this feature actually carries is narrower than
"a pod might sit running." It's a long unattended process (`ROUND_CONFIGS[1]` caps at 7.5 wall-
clock hours and a $10 budget with a $1.50 safety margin; round 2 is 1 hour and $1), self-stops on
whichever of wall-clock cap, budget cap, or plateau-triggered exhaustion hits first, resumes from
a per-round state file (`allnight{round}_state.json`) if interrupted, and writes continuously
into `SWEEP_DIR` or `SWEEP2_DIR`, exactly the directories the project's data-integrity rule
protects. It does not currently do a balance-floor check before starting (unlike the
counterfactual endpoint's `BALANCE_FLOOR_USD` guard); it only tracks spend against its own budget
cap once running.

Three properties make this different from every other web-launched action in
`curation_server.py` so far: it runs far longer than any HTTP request should block on, it writes
continuously rather than once, and stopping it needs to work from a browser tab that might not
still be open when something goes wrong.

## Safety rails, in the order they'd fire

1. **Backup and verify before launch, every time, not just on request.** Same rule this project
   already applies by hand (see the `notes/uncanny_seedrun1.backup_candidate_seeds_*` mirrors on
   disk from this session's own seed-generation work): before a launch request is allowed to
   start `driver.py`, the server takes a complete mirror of the target round's `out_dir` (even if
   it's a resume, not a fresh start, since a resume that goes wrong is exactly as destructive as
   a fresh run that goes wrong) and verifies it by file count before proceeding. A launch request
   that can't complete a verified backup fails closed with a clear error, never proceeds "best
   effort."
2. **Balance floor, checked once up front.** Reuse `curation_server.py`'s existing
   `runpod_balance()` / `BALANCE_FLOOR_USD` pattern before spawning the process, the same guard
   the counterfactual endpoint already has, so a launch doesn't start a run an empty account can't
   sustain past the first job.
3. **One run at a time, enforced by a lock file, not just UI discipline.** A launch request
   checks for a `SWEEP_DIR/.searchrun.lock` (or equivalent) containing the running PID before
   doing anything else. If a live process still owns that PID, refuse the new launch outright
   rather than risk two `driver.py` processes appending to the same state file and manifest
   concurrently, which corrupts both.
4. **Detached background process, not a blocking HTTP request.** `curation_server.py` launches
   `driver.py` via `subprocess.Popen` with its own process group (`start_new_session=True`),
   writes `{pid, round, started_at, out_dir}` into the lock file, and returns immediately. The
   HTTP request that launched it is done in well under a second; the run itself continues after
   the response, and after the browser tab closes.
5. **Status is pollable, not just log-tailable.** `driver.py` already writes a state file with
   generation count, plateau count, and spend; a new `GET /api/searchrun/status` endpoint reads
   that file plus the lock file's PID (checking the process is actually still alive, not just
   that the lock file exists, since a crash should surface as "not running" rather than a stale
   false-positive) and returns a status payload the UI polls every few seconds while a run is
   live.
6. **Stop is a first-class button, not "go SSH in and kill it."** `POST /api/searchrun/stop`
   sends the lock file's PID a `SIGTERM` (the driver's own budget/wall-clock check loop already
   has a natural checkpoint between generations to catch a clean shutdown; a hard `SIGKILL`
   fallback after a short grace period covers a hang) and removes the lock file once the process
   is confirmed gone. This is the rail that most directly answers the idle-billing concern raised
   for this feature: a run started from a browser must be stoppable from that same browser, so a
   forgotten tab doesn't turn into a forgotten spend the way an idle pod has before on this
   project.

## Resolved: where the process runs

Confirmed with Jeremy: `driver.py` runs directly on this sandbox, not on a RunPod pod over SSH;
`TODO.txt`'s "SSHing in" phrasing referred to the historical single-script workflow, not an
actual remote host. All compute is RunPod serverless end to end, matching what the driver's code
already showed. This means step 4's `subprocess.Popen` launches in the same environment
`curation_server.py` itself runs in, no second hop needed, and there is no separate pod for this
feature to worry about idling; the balance-floor check in step 2 is the only spend guard this
design needs, since serverless billing stops the moment no job is in flight.

## UI sketch

A new `runs.html` (or a panel on `seeds.html`, since seed pool review and launching a run are
adjacent tasks): a round selector defaulting to `ROUND_CONFIGS`' existing values (editable budget
cap and wall-clock cap, since round 2's exact numbers were themselves tuned by hand after round
1's results), a single "Back up and launch" button whose label changes to reflect which safety
rail is currently running ("Backing up...", "Verifying backup...", "Checking balance...",
"Launching..."), then a live status panel (current generation, novelty trend line reusing
`novelty_decay.py`'s existing rendering, spend so far against the cap, plateau count) once
running, and a "Stop" button that's only enabled while a run is live.
