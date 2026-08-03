# Data-Integrity Safety Affordances Review

## What I observed

The interface distinguishes some expensive actions from ordinary browsing. `/runs.html` calls its launch control **Back up and launch** and states that each launch mirrors and file-count-verifies the selected leg first (`build/runs_page.py:59-71`). The server enforces that promise before it starts `search.driver`: it copies the full `out_dir` and verifies file counts (`search/run_manager.py:90-106`, `129-133`). The cockpit also separates drafting from paid generation. **Send draft to queue** writes a `draft` record, while only **Run queued trial** submits RunPod jobs (`build/cockpit.py:398-400`, `591-625`; `curation_server.py:1549-1560`, `1646-1700`).

Those boundaries matter because button actions write directly below the active state leg. Favorites overwrite `user_favorites.json`; unfavorite removes a record and writes its replacement file (`curation_server.py:1527-1546`). Each comparison appends to and rewrites `user_comparisons.json` (`1468-1485`). The preference toggle persists `preference_settings.json`; retraining replaces the trained model and metadata (`1488-1525`). Cockpit generation writes full PNGs, thumbnails, and appends to `scored_manifest.json` (`657-717`). Counterfactual generation writes PNGs and `user_counterfactuals.json` (`1782-1801`). Search launch backs up the leg before a driver process can write it, but its Stop control signals that process with SIGTERM and then SIGKILL (`run_manager.py:243-263`).

The shared lightbox makes favorite removal look like a normal repeat click: the same button changes from `favorite` to `favorited (click to remove)` and immediately posts `/api/unfavorite` (`shared_ui.py:450-453`, `581-592`). The counterfactual panel explains that generation costs money, but its **Generate** button neither repeats the selected count nor asks for confirmation (`320-334`, `508-536`). `/preference_status.html` places **Retrain now** beside the model-influencing checkbox with the same secondary button treatment and no statement of what files it replaces (`preference_status.py:149-193`).

## Concrete problems

1. **Stop is visually dangerous but behaviorally unexplained.** `/runs.html` styles **Stop** red, yet one click immediately sends the stop request (`runs_page.py:190-194`). The page never states that it terminates a detached driver, may escalate to SIGKILL, or what happens to a partly completed generation batch. A researcher trying to pause, inspect, or recover from a slow run can mistake irreversible interruption for a safe UI toggle.

2. **Curation-record deletion has no undo.** Unfavoriting removes the only favorite record for a tag. The UI gives neither confirmation nor a short undo, even though favorites affect the next search's exploit pool when predicted preference is disabled. Comparison choices also append permanently with no visible correction path. These files are small, but they encode irreplaceable human judgment accumulated across long sessions.

3. **Write and overwrite actions lack a destination and consequence cue.** Counterfactuals, queued trials, seed generation, preference settings, and manual retraining all mutate the active leg. The controls do not name that leg or their target files. This matters because the global active leg can change from another tab, and merely opening `/cockpit.html` rewrites it to `cockpit` (`curation_server.py:1340-1350`).

4. **The UI does not expose the backend's strongest safety evidence.** The launch flow correctly creates and verifies a complete backup, but reports neither backup location nor verification result after launch. The user cannot tell which state snapshot protects the run just initiated.

## Recommendations, Ranked by impact

1. **Add an interrupt confirmation to Stop.** A compact confirmation should name the running expedition and leg, say that it stops the detached search and preserves already-written files, and require **Stop search run**. Keep the red styling. Return a visible completion state that distinguishes graceful stop from forced termination.

2. **Make every state-changing control show its destination.** Add a persistent `Writing to: expedition/leg` label on cockpit, seeds, preference status, and runs. For paid generation, name the artifact class and count: “Generate 4 counterfactual PNGs in this leg” and “Run 4 jobs, append results to this leg's manifest.” Bind submissions to the displayed expedition and leg, then reject a stale tab rather than relying on mutable global selection.

3. **Provide lightweight recovery for judgment edits.** After unfavorite, show a 10-second **Undo** that restores the captured record. After each comparison, offer **Undo last choice** until the next choice loads, backed by a server endpoint that removes only the matching latest record. This protects researcher effort without introducing a version-control system.

4. **Make retrain and preference steering explicit model-replacement actions.** Label the button **Retrain and replace saved preference model**. Before enabling predicted preference, display the existing warning plus an acknowledgement that the next search will use predictions instead of favorites or novelty. The current tooltip explains this, but a checkbox alone remains too easy to flip during review.

5. **Surface backup proof after launch.** Have the launch response include the verified backup path and file count, then retain a success line in `/runs.html`: “Backup verified: 3,392 files at ….” This turns an invisible backend safeguard into an auditable user-facing checkpoint.
