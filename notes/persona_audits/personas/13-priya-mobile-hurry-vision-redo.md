# Priya (mobile, in a hurry) — vision-enabled redo

Task ID: `oc_mrr8zrcx_13601b64`
Model: `opencode/mimo-v2.5-free` (vision-capable)
Original run: [01-priya-mobile-hurry.md](01-priya-mobile-hurry.md), on `cheapestinference/glm-5.2` (text-only, no image input)

## Why this redo

Priya's original report judged visual claims (overlapping text, tiny tap targets, whether the
image grid "looked fine") purely from the accessibility tree, since `cheapestinference/glm-5.2`
has no vision capability. This redo used a vision-capable free model and instructed explicit use
of `browser_take_screenshot` before making any visual claim, to confirm or correct the original
findings against actual rendered pixels.

## Report

Okay so my friend texted me this link saying "check out this AI art tool" and honestly... my
first reaction was confusion. The page loaded and I saw a title "CLAWMARKS uncanny scan" and a
bunch of dropdown menus and filters. Like, a LOT of dropdown menus. Sort, Type, Category, Prompt,
Similarity to real art... I have no idea what any of that means. I just wanted to see the
pictures.

Scrolling down I finally found the actual artwork and okay, these are cool. Two columns of animal
portraits — cats, foxes, wolves, owls — some are really striking, some are abstract and weird.
The grid looks fine on my phone, no overlapping or anything, the images are big enough to
actually see what's going on. I tapped on one (a fox face with blue eyes) and it opened this
lightbox thing with the image big and some buttons below it.

The "i" buttons are actually really helpful! I tapped one next to "favoriting" and it told me
"Favoriting just bookmarks this image for your own reference... Unlike picking, it has no effect
on the search." That made sense. Another one explained "Similarity to real art" as "DINOv2 cosine
similarity" — okay that lost me, I don't know what DINOv2 is, but the rest of the explanation
about "score of 1 means same position as average real photo" was clear enough.

I tried the "jump to" dropdown to explore other pages. "Best images by area" showed me an archive
grid with fancy metadata like "faithfulness=0.2738 novelty=0.7243" — again, no clue what those
numbers mean but the pictures looked good. "Choose between two images" was the simplest thing —
just two pictures and you pick which one you like. That I understood immediately. "Explore image
neighborhoods" showed a dot map visualization that looked cool but I don't know what I'm looking
at. And "Run or monitor a search" had a big yellow "Back up and launch" button with a "SPENDS
MONEY" label next to it — good thing that's obvious because I would NOT want to accidentally
click that.

### What actually confused me

- The main page dumps you into a wall of filters before you see any art. I had to scroll past
  Sort, Type, Category, Prompt, Similarity, Search, and checkboxes just to find the pictures.
- Jargon everywhere: "MAP-Elites cell", "DINOv2 embedding", "faithfulness", "novelty", "LoRA
  search", "counterfactual generation" — I'm a vet tech, not an engineer.
- The prompt names are truncated underscores like "conflict_pure_abstract_brushed-pa" — not
  helpful.
- The "Guide" button didn't seem to do anything when I tapped it.
- The solution map page has a long list of seed numbers that I can't make sense of.

### What worked well

- The image grid looks great on mobile — two clean columns, images are big enough to appreciate.
- The lightbox view is smooth and the arrow navigation works.
- The "i" info popups are genuinely useful explanations.
- The compare page (pick A or B) is the most intuitive thing in the whole app.
- The "SPENDS MONEY" warning on the launch button is very clear.
- Tap targets are all big enough for my thumb.

### What I could finally see, that the last run couldn't

- The images actually render properly — they're not just placeholder boxes, I can see the
  artwork details, colors, brushstrokes.
- The dot map visualization on the solution map page shows actual colored dots (white, gray,
  gold) that correspond to real training photos, generated images, and picked winners.
- The comparison images are full-size and I can actually judge which one I prefer.
- The detail view lightbox shows the image at good resolution with similar image thumbnails
  below.

Status: DONE

## Verdict vs. original report

The vision-enabled redo **confirms** the original's mobile-layout findings (grid looks fine, tap
targets big enough, no overlapping text) rather than overturning them — the accessibility-tree
read turned out accurate for this page. The new value is qualitative: with real image input,
Priya can now actually evaluate whether the artwork looks good and whether visualizations (dot
map, comparison images) are legible, which a text-only run could describe structurally but never
actually judge.
