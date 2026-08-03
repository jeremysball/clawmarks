# Persona: Dr. Elena Vasquez — adversarial QD-research expert

- Task ID: `oc_mrr6o9pj_39eb7db0`
- Model: `opencode/deepseek-v4-flash-free`
- Viewport: 1440x900
- Character: leading QD-search researcher, deliberately adversarial toward methodological claims

## Report

Right. I spent about 15 minutes working through six of the seven major views. The app goes further than most personal QD tools toward transparency, but there are several places where the methodological presentation would not survive a first-year grad student's lab-meeting interrogation.

Let me start with what is solid, because there is genuinely good practice here.

## methodology that was actually well-presented by expert standards

1. **Near-duplicate clustering** (`redundancy.html`): This is the strongest page in the app. The method is fully specified: connected components over each image's top-16 DINOv2 nearest neighbors, threshold as a tunable parameter. The tooltip even gives distribution context ("your pairs span 0.16-0.72") and the default threshold is anchored to the 95th percentile of the pairwise similarity distribution ("tightest 5% of pairs this sweep"). It also distinguishes raw count (50 images) from effective diversity (30 clusters). I'd accept this methodology in a paper methods section.

2. **UMAP solution map** (`map.html`): Honest about what it shows — the full DINOv2 embedding space, not the 2D projection of the two scalars. The mode-collapse histogram (which real training image each generated image anchors to) is a genuinely useful diagnostic that many tools skip. Showing a time slider to watch generation-by-generation drift is good practice.

3. **Elite archive transparency**: The archive page explicitly says "The DINOv2 scorer only ranks faithfulness and novelty, not aesthetic quality, so it can't tell which image in a cell is the better picture" and admits the default is highest-novelty, not highest-quality. That disclaimer should be on every QD archive tool; most omit it.

4. **Quartile binning on the coverage map**: The coverage map uses quantile-based bins (quartiles of the population) rather than uniform grid spacing, and it explains this choice. For a small, non-uniformly distributed population of 50 points, this is the defensible choice.

## unsupported or ambiguous methodological claims

1. **Tooltip range contradicts actual data (novelty and faithfulness)**: The browse-page info popup for novelty says "A score of 1 means nothing seen so far looks like it; 0 means it is a near-duplicate." The faithfulness popup says "A score of 1 means the image is at the same position as the average real photo; 0 means it is in completely unrelated territory." Both state a [0, 1] range. But the coverage map grid directly contradicts both: novelty bins go up to `[0.599..., 2)` — the top bin's upper bound is 2, not 1. Faithfulness bins start at `[-1, ...)` — the bottom bin extends to -1. Cosine similarity (which faithfulness uses per its own definition) ranges [-1, 1], not [0, 1]. So the tooltip text is factually wrong about its own metric, on two of the two core scalars. A student would lose a methods-review round over this.

2. **Novelty distance metric is never specified**: The novelty tooltip says it's "how different an image is from everything the search has already explored" but doesn't name the distance. Is it 1 - max cosine similarity to any existing embedding? Is it distance to the nearest neighbor? Distance to the centroid of explored points? Without knowing the actual formula, "novelty" as used here is not a reproducible quantity. Faithfulness gets a full definition (DINOv2 cosine similarity to the real-image centroid); novelty gets a hand-wave. This asymmetry matters because the MAP-Elites grid claims to be a "faithfulness x novelty" plane — if one axis is unspecified, the grid's cells aren't well-defined.

3. **"Coverage" is never defined as a summary metric**: The page is called "Coverage / void map" and shows an 8x8 grid colored by cell count. But there is no summary coverage number or fraction. If I want to say "this population covers X% of the frontier," I can't — I'd have to count cells by hand from the table. The term "coverage" is used as though it's a quantity the user should understand from the grid, but it's never computed or stated.

4. **"Best images by area" label conflates novelty with quality**: The navigation menu entry "Best images by area" calls a MAP-Elites archive page. The archive text itself is honest (see above), but the navigation label promises "best" — and the default ranking is "highest novelty," not "highest faithfulness," not a composite quality score. On the sort menu on the browse page, the sort options are "How new or different" and "Similarity to real art" — neither is a quality or aesthetic ranking, despite the page title "Browse all images" suggesting a gallery of work. The label-system vectors the user toward reading novelty/faithfulness as proxies for quality, and the tooltip caveats are the only guard against that reading. In a lab-meeting demo, I'd say: "Your navigation says 'best,' but the actual criterion is 'most different from what you've already seen.' Those are not the same thing, and a user new to QD will not know the difference."

5. **"Usable" vs "total" comparisons opaque**: The preference-model readiness page says "Comparisons: 0 usable of 7 total (needs 50)." It never says what makes a comparison "usable" vs. "total." I clicked the "i" buttons on that page — none define this. Seven comparisons were made, zero are usable. Why? Did the user flip only one side of a pair? Did they time out? Are they self-consistent? This is exactly the kind of data-quality detail a practitioner needs before trusting a trained preference model, and it is entirely absent.

6. **"Frontier" heuristic's domain is unstated**: The frontier cell criterion (empty cells adjacent to cells at or above median density) is pragmatically useful, but as presented, a user could confuse "empty because unreachable (structural gap in LoRA capacity)" with "empty because not tried yet (reachable gap)." The frontier heuristic doesn't distinguish these, and nothing in the UI caveats this.

Status: DONE
