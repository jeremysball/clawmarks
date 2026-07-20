# Marcus Webb (plain-language editor, copy audit)

Task ID: `oc_mrr97qhh_029a56bc`
Model: `opencode/deepseek-v4-flash-free`
New persona for this batch — a constructive, close-reading copy audit, not a role-played end
user: rewrites unclear text inline, catalogs terminology inconsistencies, and proposes a starter
glossary.

## Report

Marcus Webb here. I've done a close read of every page in the app. Overall impression: the copy
is unusually thoughtful for a research tool — someone has clearly put work into it, and it shows
in the empty states, the tooltip content, and the Guide/explore overview page. The main weakness
is that the core vocabulary (faithfulness, novelty, embedding, DINOv2, MAP-Elites) defines terms
using other undefined terms, and several info popovers use a loading state that never resolves
(stuck on "loading expeditions...") so a user who clicks the "i" button gets nothing useful.
Here's the detailed breakdown.

### 1. Sentences a first-time reader would have to read twice

| Current text | Page/Location | Suggested rewrite | Why |
|---|---|---|---|
| "Browse and curate AI-generated artwork from this LoRA search." | Browse (scan.html), subtitle | "Browse and curate AI-generated animal portraits from this experimental art search." | "LoRA search" assumes the reader knows what LoRA is. Also "artwork from this LoRA search" is vague, and conflicts with the title "uncanny scan." |
| "The DINOv2 scorer only ranks faithfulness and novelty, not aesthetic quality, so it can't tell which image in a cell is the better picture." | Elite archive, info popover | "The scoring model only measures faithfulness and novelty — it has no opinion on whether one image 'looks better' than another." | "aesthetic quality" is a value judgment that means different things to different readers. Clearer to say what the model *doesn't* measure. |
| "Connected components over each image's top-16 DINOv2 nearest neighbors, using only edges at or above the similarity threshold below." | Redundancy clusters, body paragraph | "Groups images into clusters where each image is connected to its most similar neighbors (up to 16), but only counts connections stronger than the threshold you set below." | "Connected components" and "edges" are graph theory terms; a newcomer stops there and never reaches the explanation. |
| "Gold-bordered cells are favorited winners; blue-bordered cells (only when this page is built with --use-predicted-preference) are the trained model's top pick for that cell" | Elite archive, info popover | "Gold borders mark cells where you've favorited an image. Blue borders mark the model's predicted best image — but only appear when the page was built with the 'use predicted preference' flag." | The inline `--use-predicted-preference` flag is CLI syntax leaking into UI copy. |
| "MAP-Elites is a search strategy that keeps a grid of bins (here, faithfulness x novelty) and remembers only the single best image found so far for each bin" | Elite archive, info popover | "MAP-Elites is a search strategy that divides the space into a grid (faithfulness on one axis, novelty on the other) and keeps only the best image it has found for each cell." | The axes are buried mid-sentence in a parenthetical; front-load them. |
| "Higher threshold = stricter 'near-duplicate,' lower threshold = looser 'similar family.'" | Redundancy clusters, body paragraph | "A higher threshold means images must be very similar to be grouped together. A lower threshold groups broader families of similar images." | Two different terms for the two ends of the same slider. |
| "DINOv2-based faithfulness (x) x novelty (y) plane as gallery.html, but at a finer 8x8 grid" | Coverage / void map, body paragraph | "The same faithfulness (x) and novelty (y) grid as the gallery, but split into 64 smaller cells instead of 16." | Referencing `gallery.html` by filename is a system-term leak; use the page label. |
| "Plateau count: 0" | Search runs, per-run report | "Times the search stalled: 0" (or define "plateau" at first use) | Domain term meaning "how many times the search ran out of new territory" — undefined for a newcomer. |
| "Novelty trajectory" | Search runs, per-run report | "Novelty over time" | "Trajectory" is a statistical term; "over time" is more direct. |

### 2. Info popover rewrite audit

I found **14 info popovers** across the app, all stored in `data-tip` attributes. **None of them
rendered properly** — clicking the "i" button shows "loading expeditions..." and never resolves.
A user relying on the click interaction gets nothing.

That said, the *intended* content in the `data-tip` attributes is mostly well written. The
exceptions:

| Current tooltip text | Page | Fails because | Suggested rewrite |
|---|---|---|---|
| "Faithfulness is how close the model thinks an image is to real reference photos. Novelty is how different it is from images already made." | Generation cockpit | Attached to "Choose a target coverage cell," not to either term individually — a reader who sees both terms in the label gets both definitions but not which is which. | Split per-term if the popover is per-term: "Faithfulness: how closely the image matches the reference art style. Novelty: how different it is from everything already generated." |
| "DINOv2 is an open vision model that turns an image into about 768 numbers (an embedding) capturing style without human labels; similar style gives similar embeddings, so we measure style match without a human." | Solution map, Coverage map, Redundancy clusters, Novelty decay watchlist (verbatim on 5 pages) | Defines "embedding" as "about 768 numbers" — a definition for someone who already knows what an embedding is. "Open vision model" is ambiguous (open-source? open-access?). | "DINOv2 is an AI model that converts any image into a unique 'fingerprint' (a set of roughly 768 numbers) that captures the image's style. Images with similar styles get similar fingerprints, so the computer can compare styles automatically." |
| "...The grid uses quantile bins, so each axis is split into ranges with roughly equal numbers of images. The median frontier gate only highlights empty cells beside occupied cells at or above the median count." | Coverage / void map | "Quantile bins" undefined; the frontier-gate sentence is a triple-nested condition even a technical reader parses twice. | "...Each axis is split into ranges that each contain roughly the same number of images (quantile bins). The 'frontier' markers only highlight empty cells that sit next to a cell with at least the median number of images — gaps worth exploring, not just any empty space." |
| "When on, archive.html's fallback champion per MAP-Elites cell and the next `clawmarks run allnight`'s exploit pool both use this trained model's predicted preference instead of raw novelty / favorited images." | Preference status | References a filename and a CLI command in UI copy; "exploit pool" is jargon carried over from another tooltip. | "When activated, the elite archive and the next automated search round will use this model's predicted preference instead of raw scores or favorites to decide which images to build from." |
| "This is a Bradley-Terry-style classifier: logistic regression on the *difference* between two images' DINOv2 embeddings, trained on your head-to-head picks." | Compare page | "Bradley-Terry-style classifier" and "logistic regression" are graduate-level statistics terms; the audience includes non-technical collaborators and investors. | "This model learns your taste by comparing pairs of images you've rated. It doesn't judge images individually — it learns a direction in 'image space' that points toward what you prefer, then scores every image by how far in that direction it sits. The percentage shown is how often the model picks the same winner you did, on comparisons it wasn't trained on." |

Consistently good popovers (no rewrite needed, but still broken by the "loading expeditions..."
bug): "Novelty measures how different..." (Browse, Sort), "Picked images are ones a human has
flagged..." (Browse, picked), "Favorited images are bookmarked for reference..." (Browse,
favorited), "A cluster here is a connected component..." (Redundancy clusters — excellent
analogy), "A candidate seed is a short subject/texture description..." (Candidate seeds), "This
is a small crop of the full faithfulness x novelty map..." (Cockpit, target coverage).

### 3. Inconsistent terminology

| Term 1 | Term 2 | Where they appear | Problem |
|---|---|---|---|
| "Similarity to real art" | "faithfulness" | Browse page sort/filter labels vs every other page | Reads as two different metrics moving between pages. |
| "Best images by area" | "Elite archive" | Navigation combobox vs page heading | One is task language, the other is system language. Pick one. |
| "uncanny scan" | "LoRA search" | Page title vs page subtitle | Unclear whether these name the same thing. |
| "LoRA search" | "MAP-Elites search" | Browse page subtitle vs info popover, same page | Unclear whether LoRA is the technique and MAP-Elites the strategy, or two different things. |
| "Spends money" | "Spend: started $9.91" | Search runs, launch button vs per-run report | One's a warning, one's a record — fine, but "Spend" as a label reads oddly; "Cost" or "GPU cost" clearer. |
| "image-to-image match threshold" | "similarity threshold" | Redundancy clusters, slider label vs body paragraph | Two names for the same value. |
| "Browse all images" | "scan gallery" | Navigation combobox vs link in explore page | Same destination, different names. |
| "generation" | "round" | Search runs page ("Generation: 1") vs Guide page ("search rounds") | Unclear whether a generation is a round. |

**Duplicate menu item:** "Choose between two images" appears twice in the "jump to another page"
combobox — position 4 and position 14 (the last option). Both lead to the compare page.

### 4. Empty states, error states, zero-results states

| Page | State | Verdict |
|---|---|---|
| Novelty decay watchlist | Zero data (only one generation) | **Excellent** — explains why it's empty, what needs to happen, what will appear when it does. |
| Lineage tree | Zero data (no parent_tag yet) | **Excellent** — same pattern. |
| Candidate seeds | Zero seeds | **Excellent** — actionable, explains the alternative path. |
| Predicted preference | No trained model | **Good**, but shows a filesystem path in UI copy — should link to the compare page instead. |
| Preference status | Training not ready | Mixes user-facing and developer-facing language ("via compare.html" should be a link/page name). |
| Explore/research desk | No Focus selected | **Good** — explains state and links to where to create one. |
| Cockpit evidence pane | No prompt typed yet | **Excellent** — clear instructions. |

**Overall:** empty states are a strength of this app. Every one explains why you're seeing
nothing and what to do about it. The only weakness is the occasional filesystem path or CLI
command that slips into user-facing copy.

### 5. Button and link copy audit

| Button/link text | Page | Verdict |
|---|---|---|
| "Back up and launch" | Search runs | Good, with the "Spends money" warning label. |
| "Generate" (new seeds) | Candidate seeds | The "Spends money" label is small enough to miss; consider folding cost into the button text. |
| "Send draft to queue" | Generation cockpit | "Queue" is a system concept; not obvious what happens next. |
| "Create Focus" | Solution map / Coverage map | Disabled with no tooltip explaining why (user must select a region first, but nothing says so). |
| "view all 8 in this cell" | Elite archive | **Good.** |
| "Choose image A" / "Choose image B" | Compare | **Good.** |
| "review the model's ranking" / "review the ranking" / "See predicted favorites" | Compare / Preference status / Navigation | Three different phrasings for the same destination. |
| "Retrain now" | Preference status | Unclear what it retrains or whether it's billable — no "Spends money" label. |
| "More information" (no "about [topic]" suffix) | Browse page, picked/favorited checkboxes | Breaks the pattern every other info button follows. |

### 6. Proposed glossary

A "New here? Start with these 5 words" box, suitable for the explore/research desk page or a
persistent side element:

**Faithfulness** — How closely a generated image matches the style of the real training photos.
A score near 1 means it could pass for one of the originals; near 0 means it doesn't look like
that style at all.

**Novelty** — How different a generated image is from everything the search has already
explored, including both the real photos and earlier generations. A high score means it ventures
into new visual territory.

**Generation** — One round of the automated search, producing a batch of new images. Earlier
generations (gen 0, gen 1) are the first attempts; later generations refine or expand from there.

**MAP-Elites** — The search strategy: it divides the full range of possible images into a grid
(faithfulness x novelty) and keeps the best example it has found for each cell, ensuring it
covers the whole space rather than chasing one "best" image.

**DINOv2** — An AI model that converts any image into a numerical "fingerprint" capturing its
visual style, letting the computer compare images by style similarity without needing a human to
label them.

**Embedding** — The numerical fingerprint DINOv2 assigns to an image — about 768 numbers that
represent its style. Images with similar embeddings look similar.

**Frontier** — An empty cell in the faithfulness x novelty grid that sits next to a
well-populated cell, meaning it's reachable territory the search hasn't explored yet.

Status: DONE

## Notes

New, high-value finding not previously surfaced by any persona: **all 14 info popovers are
functionally broken** — clicking the "i" button shows a "loading expeditions..." state that never
resolves, so no user relying on the popover interaction can actually read any definition. This
directly undercuts the earlier cross-cutting finding's assumption that "i" buttons are a working
jargon-mitigation ("The 'i' info popups are genuinely useful explanations," Priya's original and
redo reports) — Marcus's close read of the underlying `data-tip` attribute text confirms the
*content* is good, but the *delivery mechanism* is broken, which the role-played personas didn't
catch because they described what the popover eventually showed rather than the loading failure
itself. Worth an engineering follow-up to confirm and fix.
