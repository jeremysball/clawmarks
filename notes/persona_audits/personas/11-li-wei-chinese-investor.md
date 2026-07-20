# Persona: Mr. Li Wei — Chinese angel investor, ESL-sensitive

- Task ID: `oc_mrr6oaet_6aa13111`
- Model: `opencode/mimo-v2.5-free`
- Character: 55, angel investor evaluating whether to fund more search rounds, unit-economics and scaling-evidence focused

## Report

**Usability Walkthrough Report: CLAWMARKS Curation Tool**
**Evaluator:** Mr. Li Wei
**Date:** July 19, 2026

---

**First Impressions of Polish and Trustworthiness**

I opened the homepage and saw a gallery of AI-generated animal portraits. The images are visually interesting and varied. The navigation bar at the top is clean: the brand name "CLAWMARKS," current expedition label, a "Guide" button, "Session Status" link, and a page selector dropdown. The layout is functional and organized.

However, the design feels like an internal research tool, not a product I could show to my own investors. The color scheme is plain gray. There is no welcome screen, no "What is this?" introduction, no progress indicator showing how far along the curation process is. The page title says "uncanny scan" which confused me initially: I did not know what "uncanny" meant in this context. The word does not appear anywhere else on the page.

The "Guide" button does not seem to open anything visible when clicked. I expected a tutorial or overview, but nothing appeared.

---

**Finding Dollar Figures and Computing Cost-per-Usable-Image**

I searched the entire app for cost information and found exactly one place: the "Search Runs" page.

- **Total spend so far:** $9.91
- **Total images generated:** 50
- **Generations completed:** 1

From this I can compute: $9.91 / 50 images = **approximately $0.20 per image**.

This was easy to find on one page, but hard to find at all because I had to navigate to the right section. There is no cost summary on the homepage, no running total in the header, no "cost per image" metric displayed anywhere else. The word "spend" appears only on the runs page, and the label says "started $9.91" which made me wonder if the number was still counting up or if it was final.

I could not find:
- Cost per round breakdown (hardware vs. compute vs. storage)
- Projected cost for a second generation round
- Total budget spent to date across all expeditions
- Any comparison of cost efficiency across different prompt categories

The "Generate" button on the "Candidate Seeds" page is clearly labeled "SPENDS MONEY" in a purple badge, which I appreciate. But there is no estimate of how much each generation costs before clicking.

---

**Evidence the Process Scales or Improves**

I looked for trendlines, historical comparisons, or any chart showing improvement over time. Here is what I found:

- **Novelty Decay Watchlist:** This page exists and would show per-prompt novelty trends across generations. However, the page explicitly states: "No prompt family in this dataset has appeared in 2+ generations yet, so there's no decay curve to plot (placeholder page)." The infrastructure for tracking improvement is built, but there is only one generation of data, so the chart is empty.

- **Lineage Tree:** This page exists and would show whether mutating near a parent image actually improves on it. However, the page says: "No image in this dataset carries a parent_tag yet, so there's nothing to draw a tree from (placeholder page)."

- **Coverage Map:** Shows a heatmap of faithfulness versus novelty with occupied cells and "frontier" cells marked. This is useful for understanding where the search has explored and where gaps remain, but it does not show improvement over time.

- **Solution Map:** A UMAP scatter plot of the embedding space. It has a generation slider and play button, but since there is only one generation, the animation is static.

**Bottom line:** The tool has excellent infrastructure for tracking improvement, but because there is only one generation of data, there is no evidence of improvement I could show a co-investor. I would need to see at least two generations to demonstrate that the process learns and improves.

---

**Technical Jargon Blocking Understanding**

I encountered the following terms that confused me, and I note whether the "i" info buttons helped:

| Term | Where I saw it | Did the "i" button help? |
|------|----------------|-------------------------|
| **MAP-Elites** | Category dropdown, archive page | Partially. It explained this is a grid of faithfulness x novelty cells, but the explanation assumed I already understood evolutionary algorithms. |
| **DINOv2** | Similarity to real art, solution map, redundancy clusters | No. The "i" button said "DINOv2 cosine similarity" which is more jargon. I still do not know what DINOv2 is or why I should care. |
| **Faithfulness** | Throughout the app | Partially. The "i" button explained it as "cosine similarity between the image's embedding and the centroid of the real training images." I understood the general idea (how close to real art) but "centroid" and "embedding" are still unclear. |
| **Novelty** | Sort dropdown, solution map, archive | Yes. This was the best explanation: "how different an image is from everything the search has already explored." Clear and actionable. |
| **Centroid** | Similarity to real art explanation | No. The "i" button defined it as "average position," which helped, but "position in embedding space" is still abstract. |
| **Coverage** | Coverage map page | The heatmap is visually intuitive, but the term "coverage" is not defined on the page itself. |
| **Epoch** | Expedition label "trent_v3_epoch4" | No explanation anywhere. I do not know what an epoch is or why it is called epoch4. |
| **Leg** | "freeform1" label | No explanation. I do not know what a leg is in this context. |
| **LoRA** | Page subtitle "Browse and curate AI-generated artwork from this LoRA search" | No explanation. This is the core technology and it is not defined anywhere in the UI. |

The "i" buttons are a good idea, but they are inconsistent: some provide clear, plain-language explanations (novelty, picked), while others just add more technical vocabulary (DINOv2, faithfulness). I would suggest a "Glossary" page or a "New? Start Here" introduction that defines the five most important terms in plain language.

---

**Investment Recommendation**

Based on what I saw, I would **not** feel comfortable recommending an investment at this time. The reasons are specific and fixable:

1. **No evidence of improvement over time.** The tool has built the infrastructure to track this (novelty decay, lineage trees) but there is only one generation of data. I cannot show a co-investor a chart proving the process gets better. This is the single most important missing piece.

2. **No clear cost-per-usable-image metric.** I had to manually compute $9.91 / 50 = $0.20 per image. But I do not know how many of those 50 images are actually "usable" for merchandise. The "picked" and "favorited" counts are both zero. Without knowing the yield rate (how many of 50 images are good enough to sell), I cannot evaluate the economics.

3. **The tool looks like a research prototype, not a product.** The plain gray design, the technical jargon in the UI, the placeholder pages, and the lack of a welcome experience all signal "internal tool" rather than "investable product." For e-commerce merchandise, I need to see that the images are commercially viable, not just that they can be generated.

4. **The business model is unclear.** Is this a tool for one artist? A SaaS product for pet portrait businesses? A licensing opportunity? The app does not explain what problem it solves or for whom.

---

**What would increase my investment confidence**

- A chart showing novelty or quality improvement from generation 1 to generation 2 (or later)
- A "yield rate" metric: out of 50 generated images, how many were picked as winners?
- A cost breakdown: what does $9.91 buy, and what would a second round cost?
- A "gallery of winners" page showing only the best images, formatted for merchandise preview
- A plain-language introduction explaining what this tool does and who it is for
- A polished [report cut off here — worker session's final output was truncated at this point; likely continued with visual/branding polish as the sixth confidence-building item]

Status: DONE (final sentence of the report was cut off in the settled result; all substantive findings above are complete)
