# Persona: Theo — ADHD skimmer, scans instead of reads

- Task ID: `oc_mrr6eshj_c225fa2e`
- Model: `opencode/mimo-v2.5-free`
- Character: skims UI, gravitates to images/bold text/short labels, bounces off dense paragraphs

## Report

**Note:** this task's session ended mid-walkthrough rather than producing a synthesized closing report. What follows is Theo's live running commentary (narration transcript), which still captures the useful signal: what caught his eye vs. what he skipped as he skimmed each page.

**First 2 seconds on landing page:**

Whoa, okay. Big grid of art. Colorful. Cat faces, wolf things, owls. "CLAWMARKS" up top in bold. My eyes go straight to the images, not the words. The top bar has some kind of dropdown that says "Browse all images" and a button that says "GUIDE" and one that says "SESSION STATUS." I don't know what any of that means yet but the pictures are cool.

Below that there's a row of filters: Sort, Type, Category, Prompt, some number boxes, a search field, and "picked only" / "favorited only" checkboxes. That's a LOT of controls for a first glance. I'd skip all of that on first pass and just start clicking images.

**What I'd actually absorb:** The art grid. "CLAWMARKS" as the name. The word "GUIDE" because it's a button. The "picked only" and "favorited only" checkboxes because they're short labels.

**What I'd skip entirely:** The subtitle "Browse and curate AI-generated artwork from this LoRA search" — too long, I'd skim right past it. The filter row with Sort/Type/Category/Prompt/Similarity inputs — wall of controls, not interesting yet.

Clicked an image. Detail view popped up. Big image in the center, nice. Below it there's a line of text that looks like data: "gen1_explore_32_seed947694 | gen 1 | r2_explore | type=conflict | prompt=conflict_pure_abstract_brushed-pa | strength=0.514 cfg=9.59 | faithfulness=0.2738 novelty=0.7243" — I'd skim past that entirely, it looks like log output. Two buttons below: "favorite" with a heart, and "generate counterfactual." I'd know what "favorite" means. "Generate counterfactual" — I don't know what that does but it sounds like it might do something, so I'd probably avoid it on first pass.

There's a row of "SIMILAR IMAGES (BY DINOV2 EMBEDDING)" at the bottom — small thumbnails. That's actually cool, I'd want to click those. And left/right arrows to navigate between images. The X to close is in the top right, small, I'd miss it at first.

**What I absorbed:** The big image, the "favorite" button, the similar images thumbnails, the nav arrows.
**What I skipped:** That entire metadata line — too dense, looks like debug info.
**Would skipping it matter?** Maybe? It tells me what "type" and "strength" and "novelty" are, but I have no idea what those mean anyway, so no.

The arrows are pretty subtle — thin `‹` and `›` characters on the sides. If I were clicking fast I might miss them and try keyboard arrows instead. Tried that — keyboard arrows work, nice. Escape closes the lightbox, good.

I noticed a "GUIDE" button up top. That's exactly what a confused new user would click. Clicked it — didn't seem to open anything visible. The snapshot showed `[active]` but nothing visible changed. As a skimmer I'd shrug and move on.

Tried the big dropdown at top right — "Browse all images" with a bunch of options. This dropdown is actually well-organized. Bold section headers jump out: "Look at images," "Make new images," "Understand the search," "Preference model." Under each, shorter labels. The bold headers help me scan fast.

"Choose between two images" sounded like a fun, low-commitment thing to try. Clicked it — this is cool! "COMPARE" in big bold letters — immediately clear what this page is. Two images side by side with "OR" between them. Magnifier icons in the corners. The instruction line is a wall of text I'd skip, but the layout is intuitive enough I'd figure it out — click the one I like.

"Model unlocks in 50 votes" with a progress bar — nice motivator. "0 / 50 usable comparisons (6 submitted)" tells me where I am. Clicked Image A to vote — worked instantly, new pair loaded, counter incremented. No confirmation dialog. Very ADHD-friendly, no friction to bounce me out.

Tried "Best images by area" — sounds visual. Got "ELITE ARCHIVE" in bold — clear heading. Then a giant 6-7 line paragraph. I'm not reading that, I'd bounce right past it. What grabs me: the image cards. Each has an image, a prompt name, a "highest novelty" badge (nice tag, short and punchy), some stats, and a "VIEW ALL X IN THIS CELL" button. Cards are well-structured — image first, label second, action third. The stats below ("faithfulness=0.2738 novelty=0.7243 count=8 in cell | s=0.514 cfg=9.59" plus bin ranges) are dense; I'd skip all of that.

Checked "session status." "CLAWMARKS CURATION SERVER" bold heading, then a file path I'd skip entirely. "50/50 manifest images present on disk" and "7 comparisons" — quick status bits, I'd register those. Then a row of blue links: scan gallery, solution map, redundancy clustering, coverage map, novelty decay, lineage view, archive, preference ranking, preference status, explore, seed browser, compare, cockpit, runs. That's a LOT of links. I'd scan for words I understand: "gallery," "map," "compare," "explore." The rest — "redundancy clustering," "novelty decay," "lineage view" — sound technical, I'd skip them. "cockpit" and "runs" sound like they might do things — I'd avoid those on first pass, might cost money.

Tried "coverage map" — "COVERAGE / VOID MAP" bold heading, then another wall of text I'd skip. The grid below is visually interesting though — colored cells with numbers, some with yellow "F" badges. The colors immediately tell me something about density even without reading. I'd want to click a cell. On the right side a form: "REAL-ART ANCHOR," "FOCUS LABEL," "QUESTION," "Create Focus" button — no idea what that does, I'd skip it, too many unknowns.

Session ended while attempting to click a numbered cell on the coverage grid.

## what a skimmer would notice vs. skip
- **Notices:** image grids, bold `<h1>` page headings, short punchy badges ("highest novelty"), colored cells/visual coding, the well-organized dropdown with bold section headers, progress bars, short button labels.
- **Skips entirely:** long subtitle/description paragraphs (every page has one), dense inline metadata strings (`faithfulness=0.2738 novelty=0.7243...`), file paths, technical nav labels ("redundancy clustering," "novelty decay," "lineage view").
- **Would hesitate on:** "generate counterfactual," "cockpit," "runs" — unfamiliar verbs that could plausibly do something (i.e., cost money), so a skimmer self-selects away from them without needing an explicit warning.
- **Broken/dead-feeling:** the "GUIDE" button toggles an internal `[active]` state with no visible change — exactly the button a confused/skimming user would reach for first, and it does nothing observable.
- **Subtle navigation risk:** lightbox prev/next arrows are thin, low-contrast `‹`/`›` glyphs, easy to miss at a skim; keyboard arrows and Escape both work as fallbacks, which saved the flow.
- **Best-designed page for skimming:** the Compare page — bold "COMPARE" heading, clear A/B/OR layout, instant click-to-vote with no confirmation friction, and a progress bar that gives a skimmer a reason to keep going.

Status: DONE (narration transcript only, no synthesized closing report from the worker session)
