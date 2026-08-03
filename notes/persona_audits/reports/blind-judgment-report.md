# Blind Judgment Report: Do Faithfulness and Novelty Track Perceived Art Quality?

**Evaluator:** Grace Okonkwo (casual art enthusiast)
**Date:** 2026-07-19
**Source:** CLAWMARKS uncanny scan, 50 images, trent_v3_epoch4/freeform1

---

## Step 1: My Top 5 (Blind Picks, No Scores Yet)

I scrolled through all 50 images without paying attention to any sort order, filters, or numeric scores. Here are the five that stopped me:

### 1. The Red Wolf Face
**Description:** A bold, graphic close-up of a wolf's face rendered in vivid red against a dark, textured background. The linework is confident and almost woodcut-like, with heavy black outlines and crosshatching. The red is unapologetic, filling the snout and cheeks while the ears and forehead stay dark.
**Why I picked it:** The emotional intensity hit me immediately. It feels urgent and confrontational, like a warning sign or a folk-art talisman. The simplicity of the palette (red, black, white) makes every mark count. It has the confidence of a screen print or a propaganda poster, but for an animal. I kept coming back to it.

### 2. The Ethereal Fox with Blue Eyes
**Description:** A soft, dreamy close-up of a fox or cat face with large, luminous blue eyes. The style is loose and painterly, almost like a watercolor or charcoal study that was left deliberately unfinished. The background is warm brown, and the creature's fur dissolves into soft grey and white washes.
**Why I picked it:** The mood is completely different from the red wolf, but equally compelling. It feels like a memory or a dream of an animal rather than a portrait. The blue eyes anchor the composition while everything else floats. There's a gentleness to it that I found myself wanting to look at longer.

### 3. The Family of Cats and Owls on Aged Paper
**Description:** A collection of cat and owl faces arranged like a naturalist's field sketch, drawn in loose ink on what appears to be aged, yellowed paper. Each creature has a distinct personality: some alert, some drowsy, some suspicious. The style varies from face to face, some more detailed, some just quick gestures.
**Why I picked it:** This one charmed me completely. It feels like finding a page torn from a Victorian naturalist's sketchbook, except the creatures are slightly wrong in a way that's hard to pin down. The variety within a single frame rewards close looking. It tells a story without words.

### 4. The Ghostly White Wolf on Brown
**Description:** A pale, almost translucent wolf or cat face emerging from a warm brown background. The creature is rendered in soft white and grey washes, with minimal detail. It looks like a spirit photograph or a figure seen through fog. The ears are pointed, the snout suggested rather than defined.
**Why I picked it:** Haunting and atmospheric. This image has the quality of something half-remembered. The warm brown background makes the white figure feel like it's materializing or fading. It's quiet in a way most of the other images aren't, and that quietness drew me in.

### 5. The Neon Pink Cat on Brown
**Description:** A cat face rendered in hot pink and electric cyan on a warm brown cardboard-like background. The brushwork is bold and gestural, almost like street art or a neon sign. The eyes are large and intense, outlined in dark red. The color combination is jarring in the best way.
**Why I picked it:** This one grabbed me by color alone. The pink-cyan-brown palette is unexpected and contemporary. It feels like something you'd see wheat-pasted on a wall in Shoreditch. The energy is completely different from the other picks: loud, playful, and unafraid.

---

## Step 2: Scores and Sort Ranks

After finalizing my top 5, I looked up each image's faithfulness and novelty scores and noted where they rank in each sort.

| Pick | Description | Faithfulness | Novelty | Novelty Rank (of 50) | Faithfulness Rank (of 50) |
|------|-------------|-------------|---------|---------------------|--------------------------|
| 1 | Red wolf face | 0.2529 | 0.6185 | #3 (top 6%) | ~#48 (bottom 5%) |
| 2 | Ethereal fox, blue eyes | 0.2921 | 0.577 | #8 (top 16%) | ~#46 (bottom 10%) |
| 3 | Cats & owls, aged paper | 0.3942 | 0.5085 | #17 (top 34%) | ~#21 (middle) |
| 4 | Ghostly white wolf | 0.4569 | 0.535 | #15 (top 30%) | ~#33 (middle-bottom) |
| 5 | Neon pink cat | 0.532 | 0.3687 | #43 (bottom 14%) | ~#17 (middle-top) |

---

## Step 3: Comparison and What This Suggests

**Did my favorites cluster at the top of either sort?**

No. My picks are scattered across both metrics with no clear pattern.

On the **novelty** sort, three of my five picks land in the top third (#3, #8, #15), one sits in the middle (#17), and one falls near the bottom (#43). The two I find most compelling, the red wolf and the ethereal fox, are high-novelty images, which makes intuitive sense: they feel genuinely unlike anything I've seen before. But the neon pink cat, which I also love, scores low on novelty. It's bold and contemporary, but apparently not as "new or different" as the system measures it.

On the **faithfulness** sort, the pattern inverts almost perfectly. My two strongest picks, the red wolf and the ethereal fox, rank near the very bottom. They are the *least* similar to real art, according to the metric. Meanwhile, the neon pink cat, my weakest novelty pick, ranks highest on faithfulness of my five. The family of cats and owls sits comfortably in the middle on both.

**What does this suggest?**

For my personal taste, faithfulness and novelty are not just uncorrelated with quality, they may be *negatively* correlated with what I find compelling. The images that stopped me hardest, the red wolf and the ethereal fox, are the ones the system considers most unlike real art. They score low on faithfulness, meaning they diverge from the training distribution in ways the model flags as unusual, and high on novelty, meaning they occupy unusual positions in the embedding space.

But this isn't a simple "low faithfulness equals good" story either. The neon pink cat has high faithfulness and low novelty, and I still picked it. The family of cats and owls is moderate on both. There's no single metric trajectory that explains all five picks.

If anything, what my picks share is *emotional specificity*: each one has a clear mood (urgent, dreamy, charming, haunting, playful) and commits to it fully. The metrics measure distributional properties of the images, how different they are from training data and from each other, but they don't capture whether an image has a point of view. My picks all have a point of view. The ones I skipped, even the high-scoring ones on either metric, often felt technically accomplished but emotionally flat.

This is obviously one person's taste on 50 images. But it's a data point: the metrics may be useful for ensuring diversity in a search, but they don't reliably predict what a human viewer will find genuinely compelling. Art quality, at least for me, lives somewhere the metrics aren't looking.
