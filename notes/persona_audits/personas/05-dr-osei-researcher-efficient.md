# Persona: Dr. Sam Osei — efficiency-focused ML researcher

- Task ID: `oc_mrr5k5tc_08c8d8ff`
- Model: `opencode/deepseek-v4-flash-free`
- Viewport: 1440x900
- Character: runs QD/hyperparameter searches for a living, wants zero hand-holding

## Report

Landed on the homepage (it's not really a homepage — it just redirects straight to the browse view sorted by novelty descending, which is a good instinct for QD work). First impression: not bad. The default sort is novelty descending, the grid density is reasonable, the filter panel is right there.

**Finding the archive/MAP-Elites view**: The jump-to menu labels everything in plain language. I need "archive view" — is that "Best images by area"? I hover, I don't know. I pick it. Page title says "Elite archive." So yes, it was the archive. One guess. Cost me about 8 seconds of decode time that a label saying "Elite archive" would have saved.

**Coverage/void map**: Guessed "Find gaps in the image space." Was right. The page title says "Coverage / void map." The 8x8 grid with frontier markers is genuinely well done — clickable cells, occupancy numbers, F markers for expandable frontiers, a density histogram. This is the right thing.

**Redundancy clustering**: "Find near-duplicate groups." Page title: "Redundancy clusters." Adjustable threshold slider, connected-component groups with thumbnails. Good.

**UMAP embedding view**: "Explore image neighborhoods" → "Solution map." Generation slider, play button, color-by options, nearest-real-image histogram with clickable bar filters. This is the standout view — I'd keep it exactly as-is for any user level.

**Preference model status**: "Check taste-model readiness" → "Preference classifier status." Shows 0/6 usable comparisons (needs 50), links to compare view. No model trained. Useful status page.

**URL state**: Only `sortKey` survives in the URL. Not type, not category, not faithfulness range, not search text. If I build a specific filtered view, I can't bookmark it or share it. This is a hard blocker for my workflow.

**Detail overlay**: Click a thumbnail, get a lightbox with full metadata (faithfulness, novelty, seed, cfg, gen, category, type, prompt) plus 16 DINOv2 nearest-neighbor thumbnails, favorite button, and a counterfactual generate button (costs money — noted, did not click). Good density.

**Plain-language friction**: The jump-to menu has 14 task-oriented labels. "Browse all images," "Best images by area," "Find gaps in the image space," "Explore image neighborhoods," "Check taste-model readiness" — each one makes me decode: "Do I want the coverage map or the elite archive? Which one of these is the archive?" The `status.html` page lists every view by its real name (scan gallery, solution map, redundancy clustering, coverage map, archive, preference ranking, etc.) in one click — that page is effectively the expert's navigation hub, but it's tucked behind a "session status" link rather than being the primary nav.

**What I'd add**: An "expert mode" toggle that renames the nav to actual research terms and exposes a sidebar nav instead of the combo box. A keyboard shortcut map (`?` to show). Deep-linkable filter state in the URL. And a dedicated archive coverage/heatmap view (the 8x8 grid exists on coverage.html, but I'd also want a per-cell novelty-vs-faithfulness scatter overlay).

**Friction that slowed me down as an expert:**
- Plain-language nav labels force decode time on every page choice; I can't just think "I need the archive" and pick "archive"
- Filter state (type, category, faithfulness range, prompt, search) is not in the URL — no deep linking, no shareable research views
- `status.html` uses the real names but is only linked as "session status" rather than being the primary navigation
- The jump-to combo box is a 14-item single-select — for an expert who already knows the map, a fixed nav bar with 6-8 real-name links would be faster
- Faithfulness labeled everywhere as "Similarity to real art" — the `i` button reveals the actual term, but I shouldn't need to click an info button to confirm I'm looking at the right metric

**Things that were actually fine or good even for an expert:**
- Default sort is novelty descending (perfect default for QD research)
- Page titles (`<h1>`) use the actual research terms: "Elite archive," "Solution map," "Coverage / void map," "Redundancy clusters"
- Coverage/void map with frontier markers is genuinely well executed — the `F` cells adjacent to dense cells are exactly what I'd want
- UMAP solution map with generation slider, play animation, and nearest-real-image bar chart is production-quality
- Detail overlay with 16 DINOv2 nearest neighbors, full metadata, and pick/favorite is fast and useful
- Status page gives a one-click index of every view by its real name (switched from plain language)
- Redundancy clustering with adjustable threshold slider and connected-component display is well designed
- Information density on all views is appropriate for someone who knows the terms — no padding, no beginner hand-holding in the data display itself

Status: DONE
