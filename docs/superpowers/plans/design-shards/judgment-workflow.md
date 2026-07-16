# Judgment Workflow Design Review

## Observed workflow

`/compare.html` is a focused two-image task. It presents two large square images side by side on desktop, limits each to 70vh, uses a dark neutral surround, and makes each pane the target. Large targets and the left/right-arrow shortcut suit a long session (`build/compare_page.py:44-50, 89-91, 266-272`). Captions expose prompt name, faithfulness, and novelty (`:134-137, 226-227`), but risk pulling a visual preference judgment toward the existing metrics.

The page gives useful early progress: a 50-comparison threshold, count, animated bar, and an explanation that the model starts choosing informative pairs after the floor (`:145-170`). The sampler supports that claim: before 50 it spreads exposure across the faithfulness/novelty grid; afterwards it selects close predicted scores, where the model is least certain (`search/comparison_sampler.py:5-11, 126-138`). `/api/compare` saves each choice and retrains every tenth post-floor comparison (`curation_server.py:1468-1485`), while `/preference_rank.html` offers visual validation before the model controls a search (`build/preference_rank.py:61-65`).

The live `/compare.html` HTML fetched successfully. The current active leg has a stale manifest, so `/api/compare/next` returns 500 and prevents inspection of a live pair; `/preference_rank.html` fails for the same stated reason. The implementation was therefore reviewed from the live HTML plus source.

## Problems

1. **A single intended vote can become several stored votes.** `choose()` leaves `current` intact while its POST is pending and neither disables input nor tracks submission (`compare_page.py:235-264`). A held key, double click, or alternating arrows can send multiple POSTs for one displayed pair before the first response calls `loadNext()`. The server appends each request immediately (`curation_server.py:1477-1485`). Training later consolidates repeats, but the progress count can advance without adding evidence.

2. **The page gives no decision cadence or recovery mode for a long session.** Its only session feedback is a small cumulative text string (`compare_page.py:246-249`). It does not acknowledge a choice, show that the next pair is loading, or offer a stop point. At every tenth post-floor vote, retraining happens synchronously before the response returns (`curation_server.py:1481-1485`), yet old panes remain active and no saving/training state appears. A pause reads as failure or invites another input.

3. **Keyboard support is shortcut-only, not keyboard-operable UI.** Arrow keys trigger selection globally, but the selectable panes and magnifier are `div`s with click listeners, no button semantics, no tab stop, no focus style, and no accessible name (`compare_page.py:105-114, 266-272, 302-303`). A keyboard user cannot tab to a pane or inspect an image deliberately. The global handler also does not call `preventDefault()`, so arrow voting may scroll the page at the same time. The zoom overlay has no Escape close path or focus management (`:274-345`).

4. **Progress reports submissions, not the evidence that unlocks training.** The compare page assigns `totalCount` from raw `n_comparisons` (`:194-205, 245-258`) and declares the model unlocked at 50. Training requires 50 distinct, embedded, consolidated pairs (`preference_pairwise_model.py:15-21, 201-215`). The status route already computes both raw and usable counts (`preference_status.py:25-39`). Thus the most prominent progress indicator can promise an unlock that the retrain gate denies, especially after accidental repeats.

5. **Rank validation is visually exhaustive but cognitively unstructured.** `preference_rank.html` renders up to 500 thumbnail cells with predicted score, faithfulness, and novelty (`preference_rank.py:23-33, 79-111`). It has no rank ordinal, sampling protocol, “looks wrong” capture, or keyboard-accessible cell. The stated sanity check before search steering is an unbounded grid with no decision record.

## Recommendations, Ranked By Impact

1. **Make each vote an explicit transaction.** At the first click or arrow, set a `submitting` flag, disable both panes and arrows, and show a brief selected outline plus “Saving choice...” status. Clear it only after the next two images have loaded, or restore the current pair with a specific retry action on failure. Reject or ignore input while submitting. This is the highest-value change because it protects the training evidence and removes ambiguity during latency.

2. **Replace raw progress with usable evidence and add session pacing.** Fetch and display `n_usable / 50` as the unlock bar, with raw submissions secondary. After each 10 choices, show a compact checkpoint: “10 comparisons this session. Model refresh due after this vote” or “Model refreshed.” Add a non-blocking “Take a break” reminder at 25 or 50 choices.

3. **Make the task fully keyboard and screen-reader operable.** Use semantic buttons for choices and magnifiers, or give the panes `role="button"`, `tabindex="0"`, labels, Enter/Space behavior, and a persistent `:focus-visible` outline. Prevent arrow-key scrolling when a vote succeeds. Add Escape to close zoom and return focus to the magnifier.

4. **Preserve the uncluttered image comparison by hiding metrics until after choice.** The prompt name and faithfulness/novelty numbers invite anchoring. Show only neutral image labels while deciding, then reveal the metadata briefly after selection or behind a “show sampling details” disclosure. Keep the existing full-resolution magnifier, which is valuable for marker texture and line quality.

5. **Turn ranked-grid validation into a bounded review.** Add rank numbers and a simple review mode that presents, for example, the top 20, middle 10, and bottom 10 with a “matches my taste / questionable” mark. Record only the reviewer’s validation notes or flags, not another model-training label. This gives the Stage 5b gate an auditable human check while retaining the existing grid as an overview.
