# Persona: Minh — ESL newcomer

- Task ID: `oc_mrr5hx9y_c974f243`
- Model: `opencode/mimo-v2.5-free`
- Viewport: 1440x900
- Character: English-as-second-language new intern, first time using the app

## Report

**Minh's walkthrough report**

OK so I opened the app and the first thing I see is a big grid of animal portraits. Very cool art actually. But the top bar has a lot of words I do not understand. Let me go through what happened.

**Page 1: Homepage ("Browse all images")**

The title says "CLAWMARKS uncanny scan." I do not know what "uncanny" means here in this context. Is it a good thing or bad thing? The subtitle says "Browse and curate AI-generated artwork from this LoRA search." I know what "browse" means but "curate" feels like a word my team lead would use, not me. And "LoRA search" - I have no idea what LoRA is.

The filter area has a Sort dropdown. One option says "How new or different (high to low)" and there is a little "i" button next to it. I clicked it and the explanation was actually pretty clear - it said "novelty" measures how different an image is from everything already explored. Good. But the sort option itself does not say "novelty" anywhere - it says "How new or different." So if I wanted to sort by novelty later, I would not know that is the same thing.

The Category dropdown has things like "negtrigger," "truncated," "allnight exploit," "allnight explore," "round2 exploit," "round2 explore." These are not English words to me. I would have to ask someone what these mean. The "i" button next to Category explains MAP-Elites and explore/exploit, which is actually a good explanation, but the category names themselves are still opaque.

I clicked on an image and a big lightbox opened. The metadata line says things like "gen1_explore_32_seed947694 | gen 1 | r2_explore | type=conflict | strength=0.514 cfg=9.59 | faithfulness=0.2738 novelty=0.7243." I understand none of this except "type=conflict." There are two buttons: "favorite" and "generate counterfactual." I hovered over the "i" next to "generate counterfactual" and the explanation says it costs real generation time/money. OK so I will not click that. But there is no "SPENDS MONEY" badge on this button like there is on the "Back up and launch" button on another page. I would be nervous about clicking it.

There is also a section called "similar images (by DINOv2 embedding)." I do not know what DINOv2 is.

The checkboxes "picked only" and "favorited only" - I do not know the difference between picked and favorited. They sound like the same thing to me.

**Page 2: "Choose between two images"**

This page was actually clear! The nav label says "Choose between two images" and that is exactly what you get. Two images side by side, you click the one you prefer. The page heading says "Compare" which is also a clear word. There is a progress bar that says "Model unlocks in 50 votes" and "0 / 50 usable comparisons (6 submitted)." I do not know what "usable comparisons" means vs just "comparisons" but the basic idea is clear. This page I could use without help.

**Page 3: "Best images by area"**

This was confusing. The nav says "Best images by area" so I expected something organized by maybe animal type, or art style, or geographic area? But the page heading says "Elite archive" and the content is a grid organized by "faithfulness x novelty" with labels like "bin faithfulness 1/4 (0.243-0.394) - novelty 4/4 (0.545-0.724)." The description paragraph is very long and uses words like "MAP-Elites archive," "population quartiles," "DINOv2 scorer," and "mode-collapse check." I would not know where to start on this page without help. The word "area" in the nav is misleading - this is not about geographic areas or categories, it is about statistical bins.

**Page 4: "Explore image neighborhoods"**

The nav says "Explore image neighborhoods" but the page heading says "Solution map." Already a mismatch. The content is a scatter plot with dots. The description says "UMAP projection of the full DINOv2 embedding space." I do not know what UMAP or embedding space means. The right sidebar has a list of seed IDs like "gen1_explore_1_seed214599 gen 1" which look like internal file names, not something a user should see. There is a section called "Nearest real training image (mode-collapse check)" which I would have to ask about. The form fields say "REAL-ART ANCHOR," "FOCUS LABEL," "QUESTION," and a button "Create Focus." I do not know what a "Focus" is in this context.

**Page 5: "Run or monitor a search"**

The nav says "Run or monitor a search." The page heading says "Search runs." There is a button "Back up and launch" with a red/purple badge that says "SPENDS MONEY." This is the only place I saw a clear warning that something costs money. Good. But the word "monitor" in the nav makes it sound like I can just watch, when actually the main action here is to launch something. Also there is a "Stop" button that is greyed out. The Per-run report shows "Spend started $9.91" which tells me money has already been spent.

**Page 6: "session status"**

This is a simple status page. It shows "50/50 manifest images present on disk" and "6 comparisons." The word "manifest" is not something I would look up but it is not everyday English. Below there is a list of links to other pages: "scan gallery," "solution map," "redundancy clustering," "coverage map," "novelty decay," "lineage view," "archive," "preference ranking," "preference status," "explore," "seed browser," "compare," "cockpit," "runs." Some of these are clear (compare, archive, explore) but "cockpit" and "redundancy clustering" and "novelty decay" are not.

---

**words/phrases I'd have to look up**

- **uncanny** - I know the word means "strange/weird" but I do not know why it is in the app title. Is the art supposed to be uncanny?
- **LoRA** - appears in "this LoRA search" on the homepage. No idea what this is.
- **curate** - I know the word but it feels like jargon here. What does curating mean in this tool vs just looking?
- **MAP-Elites** - appears in the Category filter info and on the Elite archive page. The info popover explains the concept but the name itself is opaque.
- **negtrigger** - Category option. Not an English word.
- **truncated** - Category option. I know the word generally but not what it means for an image category.
- **allnight exploit / allnight explore** - Category options. "Exploit" has a negative connotation in everyday English. "Allnight" is not a standard word.
- **round2 exploit / round2 explore** - Category options. What is round 1?
- **exploit vs explore** - used as opposites in the MAP-Elites explanation but "exploit" sounds bad in normal English.
- **cfg** - appears in image metadata (cfg=9.59). Abbreviation for what?
- **strength** - appears in image metadata (strength=0.514). Strength of what?
- **faithfulness** - used everywhere as a metric. Faithful to what? The info popover for the similar images section does not explain this.
- **novelty** - the sort "i" button explains this well, but the word itself is not obvious.
- **DINOv2 embedding** - appears in the similar images section and the solution map. No explanation on the page for what DINOv2 is.
- **UMAP projection** - on the solution map page. No plain-English explanation.
- **embedding space** - on the solution map page. Mathematical concept, not plain English.
- **mode-collapse check** - on the solution map page. I would have to ask what this means.
- **counterfactual** - the "i" button explains it well, but the word itself is academic.
- **picked vs favorited** - two separate checkboxes with separate "i" buttons but I do not know how they differ.
- **manifest** - on the status page ("50/50 manifest images present on disk"). Technical word.
- **seed** - appears in all the image IDs (seed947694). What is a seed?
- **generation** - used as both a sort option ("Generation (newest first)") and a metadata field (gen 1). Does it mean the round of creation?
- **plateau count** - on the search runs page. What is plateauing?
- **taste-model** - in the nav ("Check taste-model readiness"). A model of taste?
- **ancestry / lineage** - in nav options. Images have parents?
- **cockpit** - in the status page links. A control panel? Why cockpit?
- **expedition / leg** - in the search runs page dropdowns. These are exploration metaphors but I do not know what they map to technically.

**labels that matched vs misled once I clicked through**

- **"Browse all images"** - matched. You get a grid of images. Clear.
- **"Choose between two images"** - matched. Side-by-side comparison. Very clear.
- **"session status"** - matched. Shows status info. But the word "session" is slightly misleading - this is not a login session, it is a search/expedition session.
- **"Best images by area"** - misled. I expected geographic or categorical areas. Got a statistical grid organized by faithfulness/novelty bins called "Elite archive." The word "area" is doing heavy lifting here and does not mean what I think it means.
- **"Explore image neighborhoods"** - misled. The nav says this but the page heading says "Solution map." The content is a UMAP scatter plot, not something I would call "exploring neighborhoods." The word "neighborhoods" suggests local areas of something, but this is a mathematical projection.
- **"Run or monitor a search"** - partially misled. "Run" is accurate (you can launch), but "monitor" implies passive watching. The main action is a money-spending launch button. Also the page heading is "Search runs" (plural noun), not "Run or monitor" (verb phrase).
- **"Check taste-model readiness"** - I did not visit this but the label is confusing. Readiness for what?
- **"See predicted favorites"** - I did not visit this but "predicted" raises the question: predicted by what?
- **"See which prompts are running out"** - I did not visit this but "running out" of what? Prompts are not a finite resource in normal English.
- **"Trace image ancestry"** - I did not visit this but "ancestry" implies family trees. Do images have parents?
- **"Find near-duplicate groups"** - I did not visit this but it is at least clear English, even if "near-duplicate" is a technical concept.
- **"Find gaps in the image space"** - I did not visit this but "image space" is jargon. Gaps in what?

**Money-spending anxiety notes**

- The "Back up and launch" button on the search runs page has a clear "SPENDS MONEY" badge. This is good.
- The "generate counterfactual" button in the image detail view has no visual spending warning. The "i" popover mentions "real generation time/money" but you have to find and read that yourself. As a new intern, I would be afraid to click this button.
- The "favorite" button appears safe (no spending warning) but I am not 100% sure.
- All the info "i" buttons appear safe. I clicked several.
- The navigation dropdown and all filter controls appear safe.
- The "Guide" button appears safe but I could not tell what it did - it seemed to toggle something but nothing visible changed.

Status: DONE
