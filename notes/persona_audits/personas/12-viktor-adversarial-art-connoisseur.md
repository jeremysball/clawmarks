# Persona: Viktor — adversarial, highly technical art connoisseur

- Task ID: `oc_mrr6pzpa_32c4aba2`
- Model: `cheapestinference/glm-5.2 --variant max`
- Character: 44, former ML infra engineer turned art collector, adversarial toward the claim that novelty/elite UI signals correlate with actual aesthetic quality

## Report

I have enough. I could not visually verify image content (this session's model has no image input), so I'll name the best image by the UI's own quality proxy and metadata, and say so plainly.

---

**Viktor's field notes, CLAWMARKS walkthrough**

Look, I came in ready to be impressed and I'm leaving annoyed. The whole app is a search-engine dashboard wearing an art-curation costume. Every "best," "elite," and "favorite" surface is either a novelty metric in a trench coat, an empty shell waiting for a human to do the work, or a pay-button I'm not allowed to touch. The single subsystem that would actually rank images by aesthetic quality, the trained preference model, is offline, and the app silently falls back to "most novel" as if that were the same thing. It isn't. Novelty is how unlike-everything-else an image is; an image can be novel because it's a unique piece of garbage.

**Hunt, narrated.** Default landing is "Browse all images" sorted by "How new or different (high to low)." I opened the info popover and the app tells on itself in one sentence: "Novelty measures how different an image is from everything the search has already explored... 1 means nothing seen so far looks like it." That is not quality. So the default view actively hides the best images. I flipped the sort to "Similarity to real art (high to low)" because Trent's real source art is the only genuinely good stuff in the building, and the closest thing to a quality proxy this app exposes. Top of the list immediately: `gen1_explore_38_seed162978`, faithfulness=0.7319, novelty=0.2471. Note the inversion: the image most similar to the real art is also the least novel, which is exactly why the default sort buries it at row 50.

Then I tried the "Elite archive / Best images by area," which sounds like the curated highlight reel. It's the MAP-Elites grid, one image per cell of faithfulness x novelty. Every cell is labeled "highest novelty." Not "best." The page's own description admits it: "others fall back to the highest-novelty image the automated search found. The DINOv2 scorer only ranks faithfulness and novelty, not aesthetic quality, so it can't tell which image in a cell is the better picture." So the word "Elite" is doing a lot of unpaid overtime. The only honest escape valve is the "view all N in this cell" button, which is the app admitting its own pick isn't the pick.

Then "See predicted favorites." Dead. "No trained model." Then "Check taste-model readiness": 0 usable comparisons of 7 total, needs 50. So seven poor souls already voted and all seven were silently marked unusable, with no explanation of why. The one quality signal that exists, the Compare page, is gated behind 50 votes you can't get to because the votes don't count. Blue "predicted winner" borders on the archive only render when the page is "built with --use-predicted-preference," which it wasn't. The quality layer is a ghost.

**Filter torture.** I set "Similarity to real art >= 0.9" (max in the data is ~0.73). Result: a blank grid. Counter reads "0 / 50 images," buried in the sidebar. No empty-state message, no "try widening," no hint that the filter is the problem. A first-time user thinks the app is broken. Same story with "favorited only" when 0 are favorited: blank void, no explanation. Also: the filter calls it "Similarity to real art," the lightbox calls it "faithfulness," and the URL param is `faithMin`. Three names for one number. Sloppy.

**Zoom.** The lightbox does serve the real 1024x1024 PNG, so there's a genuine full-resolution source under there, but it's displayed at 522px with no zoom-in. You cannot inspect detail. The Compare page teases a magnifier that promises "full resolution," but the browse lightbox doesn't. And as the driver of this session I couldn't load pixels at all (no image input this side of the wire), so the "best image" call below is made from the UI's own quality proxy and metadata, not from eyeballing it. I'd rather be honest than pretend I saw something I didn't.

**Best image I found.** `gen1_explore_38_seed162978` (prompt `conflict_dense_all-over_doodle_fi`, type=conflict, strength=1.454, cfg=3.6, faithfulness=0.7319, the highest in the archive, novelty=0.2471). Found in 20 seconds by sorting Browse on "Similarity to real art (high to low)" and opening the top card. Could not visually confirm it's actually the most striking because I have no pixel view in this session; it is, however, the strongest candidate the app's own metrics will point you at.

**Time accounting, harsh.** Of roughly 12 minutes: 2 minutes of genuinely useful browsing (the faithfulness sort plus one hop across the lightbox's "similar by DINOv2" strip, which is the one honest nav aid). The other 10 went to discovering that "Elite" means novel, "Best" means novel, "favorites" means nothing because the model isn't trained, every dead-end filter fails silently, and the only quality path is gated behind votes that don't register. The UI spends a lot of energy selling you on search quality and almost none on picture quality.

## UI claims that didn't hold up under scrutiny
- "Browse all images" default sort is "How new or different," which the app's own popover admits measures difference-from-prior-output, not quality. The default view actively hides the most faithful images.
- "Elite archive" / "Best images by area" is misleadingly named. Per the page's own text, each cell winner is "the highest-novelty image the automated search found," and "the DINOv2 scorer only ranks faithfulness and novelty, not aesthetic quality." Every cell literally carries a "highest novelty" tag. Elite means novel.
- "Similarity to real art" in the filter bar, "faithfulness" in the lightbox, `faithMin` in the URL. One metric, three names.
- Empty filters return a blank grid with no empty-state message. `Similarity >= 0.9` and `favorited only` (with 0 favorited) both just vanish the results with zero explanation. Only signal is a "0 / 50" counter hidden in the sidebar.
- "See predicted favorites" is a dead end ("No trained model"); "Check taste-model readiness" reports 0 usable of 7 submitted, no explanation of why all 7 were rejected. The only quality subsystem is offline.
- "Compare" page is the one place that asks about taste, but it's gated behind 50 votes, and votes submitted so far don't count toward the threshold. No reason given.
- Lightbox serves a real 1024x1024 PNG but caps display at 522px with no zoom-in. You can't actually inspect detail on a candidate from Browse; only Compare promises a magnifier.
- Solution map "Color by" offers generation, prompt type, or picked. No faithfulness, no novelty, no predicted-preference. The one view that could show you where the good stuff lives doesn't color it.

## what actually helped find good art fast
- Sort by "Similarity to real art (high to low)." The only quality proxy exposed. Put the strongest candidate on top in one click.
- The lightbox's "similar images (by DINOv2 embedding)" strip. Once you find one good candidate, this is the fastest way to hop its neighborhood.
- The Elite archive's "view all N in this cell" button. The one honest admission that the auto-pick isn't the best, and the fastest path to manually eyeballing every candidate in a bin.
- The Solution map UMAP. Genuinely the most honest view in the app: shows where the generated cloud sits relative to the 31 real training images, and where the empty gaps are.
- The mode-collapse bar chart ("nearest real training image"). Tells you the search has piled onto a narrow slice of the real style (one anchor, `FlzK3OUXoAEvv3e.jpg`, claims 7 of 50 images), which is real information about whether "50 images" actually means 50 distinct ideas.

Status: DONE
