# Cockpit and Autopilot Design Review

## What I observed

The cockpit has a sound three-stage safety model, but its labels obscure that strength. Autopilot generates suggestions, `Use this` copies one into the editable recipe, and `Send draft to queue` records a draft without starting generation. Only `Run queued trial` spends RunPod money. The implementation preserves these boundaries: Autopilot returns filtered suggestions without queueing them (`curation_server.py:1870-1928`); `Use this` fills the mission, prompt, and hypothesis (`build/cockpit.py:641-660`); and queue creation stores `status: "draft"` (`curation_server.py:525-555`, `1549-1560`). This is safer than the word “Autopilot” implies.

The editor also distinguishes evidence from prediction well. “Existing evidence only” and “not a forecast” appear beside prompt neighbors and coverage context (`build/cockpit.py:403-411`). The live page showed `uncanny_frontier` as the selected expedition, an empty queue, and no available frontier data. The target-cell API reported a missing cockpit manifest, while the UI converts that condition to the more general “No search data yet” state (`build/cockpit.py:468-481`).

The paid-action boundary is much weaker. Each queue row shows only a generic mission title, image count, seed strategy, strength, sampler, steps, CFG, and status (`build/cockpit.py:591-600`). It hides the prompt, hypothesis, target cell, negative prompt, creation time, and expedition. The collapsed bottom drawer also hides the queue by default (`build/cockpit.py:252-265`, `416-428`). Jeremy can see that something will run, but cannot verify what it will generate from the launch control.

`Run queued trial` immediately posts to the run endpoint without a confirmation or review state (`build/cockpit.py:617-626`). The server then submits every image as a separate job (`curation_server.py:657-703`). It checks the RunPod balance floor, but neither the UI nor response presents balance, estimated spend, job count in paid-action language, or a final payload summary (`curation_server.py:1646-1700`). There is no cockpit cancel endpoint. The only cancellation handling recognizes a remote `CANCELLED` result; it does not let Jeremy request one (`curation_server.py:698-699`).

## Concrete problems

1. **A paid, irreversible launch looks like an ordinary row action.** “Run queued trial” has the same visual weight as low-risk utility controls and fires on one click. Other draft buttons remain active, so several batches can start concurrently. The backend blocks only rerunning the same running trial, not concurrent trials (`curation_server.py:1657-1669`).

2. **The launch surface omits the experiment’s identity.** Generic titles such as “Candidate trial” make similar drafts indistinguishable. A long overnight queue cannot answer “what runs next?” without relying on memory.

3. **No intervention path exists after launch.** Running rows show only `running`; they expose no submitted/completed count, elapsed time, remote job IDs, stop action, or recovery guidance. On server restart, the system marks a running trial failed even though remote generation may still be active (`curation_server.py:1950-1966`).

4. **Partial failure can hide paid output.** PNGs are written as jobs complete, but scoring and `result_tags` happen only after the whole batch succeeds (`curation_server.py:678-717`). If a later job fails, the row says `failed` with no result links, although earlier images may exist. This does not delete output, but it makes generated assets undiscoverable and invites a duplicate paid rerun.

5. **Global active-leg state weakens context confidence.** Opening the cockpit silently switches the global leg, and another tab can switch it away (`curation_server.py:1340-1350`). Queue APIs resolve against that mutable global state. The expedition picker alone does not warn that another tab changed the destination.

## Recommendations ranked by impact

1. **Add a launch review and explicit confirmation.** Expand a draft into a compact payload summary: expedition, prompt, target, image count, all generation settings, and a clear “This submits 4 paid RunPod jobs” line. Require `Confirm and run 4 jobs`; keep queueing visually neutral. This preserves the existing two-step workflow while making the costly step unmistakable.

2. **Add stop and concurrency controls.** Permit one cockpit trial at a time by default. For a running trial, show `submitted / completed`, elapsed time, and `Stop remaining jobs`. Cancellation should preserve completed PNGs and mark the record `cancelled with results`, never delete files.

3. **Make every draft inspectable and removable.** Show the prompt’s first line and target in each row, with `Review`, `Edit`, and `Remove draft`. Keep failed trials visible with `Inspect output` and an explicit `Retry as new draft`, rather than silently reusing the old record.

4. **Persist partial results immediately.** Record each completed job and expose its thumbnail before the batch finishes. A failed row should say, for example, “failed after 2 of 4; 2 outputs preserved.” This directly supports the project’s data-integrity rule.

5. **Rename Autopilot to Suggestions, or label its scope.** “Autopilot: suggestions only” would align the name with behavior. Add “Nothing is queued or run automatically” above the cards and retain provenance such as `source: autopilot` when a suggestion becomes a draft.

6. **Bind requests to an explicit expedition and cockpit leg.** Include that destination in queue and run payloads, then reject stale-page actions if it differs from the page context. This small protocol change prevents cross-tab ambiguity without changing the server architecture.
