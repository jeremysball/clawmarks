# CLAWMARKS UX persona tests

Simulated-persona usability walkthroughs of the CLAWMARKS curation app (`curation_server.py`, tailnet URL `http://100.73.69.126:8420/`), run via `taskferry` dispatch across multiple opencode/taskferry models. Each persona was a read-only observational walkthrough; none clicked a real billable action (generate/launch/retrain).

| # | Persona | Focus | Model |
|---|---------|-------|-------|
| 01 | [Priya](01-priya-mobile-hurry.md) | Mobile, in a hurry | cheapestinference/glm-5.2 |
| 02 | [Walt](02-walt-money-anxious.md) | Older, non-technical, money-anxious | cheapestinference/glm-5.2 |
| 03 | [Dana](03-dana-keyboard-only.md) | Keyboard-only, low-vision, 200% zoom | opencode/mimo-v2.5-free |
| 04 | [Minh](04-minh-esl-newcomer.md) | ESL newcomer, first-time user | opencode/mimo-v2.5-free |
| 05 | [Dr. Sam Osei](05-dr-osei-researcher-efficient.md) | Efficiency-focused ML researcher | opencode/deepseek-v4-flash-free |
| 06 | [Rae](06-rae-poweruser-goal.md) | Goal-directed power user | opencode/hy3-free |
| 07 | [Jordan](07-jordan-screenreader.md) | Blind, screen-reader-only | cheapestinference/kimi-k2.7 |
| 08 | [Carla](08-carla-stakeholder-roi.md) | Non-technical stakeholder, ROI/trust | opencode/deepseek-v4-flash-free |
| 09 | [Dr. Elena Vasquez](09-dr-vasquez-adversarial-researcher.md) | Adversarial QD-research expert | opencode/deepseek-v4-flash-free |
| 10 | [Theo](10-theo-adhd-skimmer.md) | ADHD skimmer | opencode/mimo-v2.5-free |
| 11 | [Mr. Li Wei](11-li-wei-chinese-investor.md) | Chinese angel investor, ESL-sensitive | opencode/mimo-v2.5-free |
| 12 | [Viktor](12-viktor-adversarial-art-connoisseur.md) | Adversarial technical art connoisseur | cheapestinference/glm-5.2 --variant max |
| 13 | [Priya (vision redo)](13-priya-mobile-hurry-vision-redo.md) | Mobile, in a hurry — with real image input | opencode/mimo-v2.5-free |
| 14 | [Sam](14-sam-security-redteam.md) | Passive security / information-exposure audit | opencode/deepseek-v4-flash-free |
| 15 | [Viktor (vision redo)](15-viktor-adversarial-art-connoisseur-vision-redo.md) | Adversarial art connoisseur — with real image input | opencode/mimo-v2.5-free |
| 16 | [Walt (vision redo)](16-walt-money-anxious-vision-redo.md) | Older, money-anxious — with real image input | opencode/mimo-v2.5-free |
| 17 | [Ines](17-ines-colorblind-contrast.md) | Deuteranopia (red-green color blindness) audit | opencode/mimo-v2.5-free |
| 18 | [Marcus Webb](18-marcus-plain-language-editor.md) | Plain-language / technical-writing copy audit | opencode/deepseek-v4-flash-free |
| 19 | [Priyanka Rao](19-priyanka-product-designer-heuristic.md) | Senior product designer, Nielsen heuristic evaluation | opencode/mimo-v2.5-free |

## Cross-cutting findings (surfaced by 3+ personas independently)

- **Jargon wall**: LoRA, MAP-Elites, DINOv2, faithfulness/novelty, UMAP, expedition/leg, cockpit — undefined or under-defined on first encounter. Flagged by Priya, Minh, Carla, Li Wei, Dana.
- **"Elite"/"Best" mislabeling**: the Elite archive's "best" images are actually "highest novelty" per MAP-Elites cell, not aesthetic quality — the page's own text admits this, but the nav label and per-card badges don't. Flagged hardest by Viktor and Dr. Vasquez, also noted by Rae and Priya.
- **Inconsistent/missing cost warnings on billable controls**: "Back up and launch" (search runs) and "Generate" (candidate seeds) carry a clear "SPENDS MONEY" badge; "generate counterfactual" (lightbox) and "Send draft to queue" / "Retrain now" (cockpit, preference status) do not. Flagged by Walt, Priya, Dana, Jordan (Jordan additionally notes the "Spends money" text isn't programmatically associated with the button for screen readers). Walt's vision redo confirms the badge itself is well-designed where present (real contrast/size/position) but the gap on "Send draft to queue" is total: no badge, no cost-related word anywhere on that page.
- **Preference/taste model is perpetually offline** (0 usable comparisons of the ones submitted, needs 50) so "predicted favorites" and quality-based ranking are dead ends app-wide. Flagged by Rae, Viktor, Dr. Vasquez, Li Wei.
- **Accessibility**: image grid thumbnails are keyboard-unreachable and have no alt text/image role (Dana, Jordan independently confirmed via different methods — keyboard-only navigation and accessibility-tree inspection).
- **"Usable" vs "total" comparisons never defined** anywhere in the UI, including the info popovers. Flagged by Dr. Vasquez and Rae.
- **No evidence-of-improvement view**: novelty-decay and lineage-tree pages are built but empty (placeholder, since only one generation exists). Flagged by Carla and Li Wei as the top blocker to trusting the tool with money.
- **No auth layer at all**: every API endpoint and every billable control is reachable by anyone with the URL, no login/token/ACL gate anywhere. The status page also leaks the real absolute filesystem path and username. Flagged originally by Priya (path leak) and confirmed/extended by Sam's dedicated security audit, which additionally found an unauthenticated RunPod dollar-balance leak in `/api/searchrun/report`.
- **Color as the sole encoding for type/category**: the gallery grid's conflict/style card-shadow color and the solution map's "prompt type" dot color both use an orange/green pair, the single most common red-green colorblindness collision, with no redundant icon or text on the affected element. Flagged by Ines's dedicated audit; no other persona had the perceptual grounding to catch this.
- **Possible broken "i" info popovers**: Marcus's close read of the underlying `data-tip` markup found that clicking any "i" button shows "loading expeditions..." and never resolves across all 14 popovers he tried, contradicting several role-played personas (Priya x2, others) who described popover *content* as if it displayed successfully. This needs an engineering follow-up to confirm — either the popovers are genuinely broken and the role-played personas didn't notice a loading-state failure, or Marcus's read-only inspection of the markup mistook something else for a stuck loading state.
- **Nav dropdown label never matches the page's own heading**: every page's jump-to dropdown entry, top-bar label, and on-page `<h1>` use a different name for the same page (e.g. dropdown "Explore image neighborhoods" vs. heading "Solution map"; dropdown "Find gaps in the image space" vs. heading "Coverage / void map"), and the status page's link list uses yet a third set of names for the same pages. Flagged in depth by Priyanka's heuristic evaluation; consistent with the broader jargon-wall finding above but this is the concrete, fixable instance of it — pick one name per page.
- **Duplicate dropdown entry**: the jump-to navigation dropdown lists "Choose between two images" twice (once mid-list, once at the end). A straightforward bug, not a design tradeoff. Flagged by Priyanka.
- **Placeholder pages leak raw system internals instead of guiding the user**: the Predicted Preference page shows a full filesystem path and tells the user to run a Python module directly (`python -m clawmarks.search.preference_pairwise_model`) rather than a plain-language "not ready yet" message. Flagged by Priyanka; corroborates Sam's security audit finding on the same page.
- **"Guide" button appears non-functional**: clicking it produces no visible modal, overlay, or page change. The one element a first-time visitor would naturally reach for fails silently. Flagged by Priyanka; not previously reported by any other persona (most didn't try it).

## Vision-enabled redo round (13+)

Personas 01, 02, and 07 originally ran on text-only models (`cheapestinference/glm-5.2`,
`cheapestinference/kimi-k2.7`), which cannot see screenshots — every visual judgment in those
reports (layout, contrast, whether a warning badge is actually eye-catching) came from the
accessibility tree alone, not real pixels. This round redoes those personas on vision-capable
free models (`opencode/mimo-v2.5-free`) with explicit instructions to screenshot and reason from
actual images, to confirm or correct the earlier text-only findings. It also adds new persona
angles: a passive security/info-exposure audit (Sam), a color-blindness accessibility audit
(Ines), a constructive heuristic evaluation (Priyanka), and a plain-language copy audit (Marcus).

- 13: Priya vision redo — confirms the original mobile-layout findings; new value is judging
  artwork/visualization legibility, which text-only couldn't do at all.
- 15: Viktor vision redo — the headline result of this round. With real pixels, Viktor's own
  top pick for "most visually striking image" sits mid-rank on both `novelty` and `faithfulness`,
  empirically confirming neither metric reliably tracks perceived art quality.

## Notes on this collection

- Theo's and Li Wei's reports are the raw narration/message text as returned by their worker sessions rather than a fully synthesized closing report — both cut off before a clean ending (Theo mid-exploration, Li Wei mid-final-sentence). The content up to the cutoff is complete and usable.
- All dispatches ran read-only against the live app; no generation, launch, or retrain action was triggered by any persona.
