# Viktor (adversarial art connoisseur) — vision-enabled redo

Task ID: `oc_mrr9itj6_808db38d` (final report; resumed twice from `oc_mrr8ys2x_2044dd1d` after a
stale-element crash, then again from `oc_mrr966uw_5895b691` after an empty completion)
Model: `opencode/mimo-v2.5-free` (vision-capable)
Original run: [12-viktor-adversarial-art-connoisseur.md](12-viktor-adversarial-art-connoisseur.md),
on `cheapestinference/glm-5.2 --variant max` (text-only, no image input)

## Why this redo

Viktor's whole persona is judging whether images are genuinely good art, a question a text-only
model cannot answer at all — its original run could only reason from metric values and DOM
metadata. This redo used a vision-capable model with explicit `browser_take_screenshot`
instructions so Viktor could actually look at the pixels and compare his own visual judgment
against the app's novelty/faithfulness scores.

## Report

**Viktor's Field Notes: CLAWMARKS Usability Walkthrough**

I came here to find one genuinely amazing image fast. Here's what happened.

The app opens on a novelty-sorted grid of 50 images. Right away, I'm skeptical. "How new or
different" is the default sort, and what it surfaces is... a lot of broken-looking stuff. Glitchy
animal faces, fragmented compositions, images that look like the model hallucinated
mid-attention. The novelty metric measures deviation from training data, not aesthetic quality.
That's a meaningful distinction the UI doesn't make explicit. I'm scrolling past rows of images
I'd never hang on a wall, wondering if the algorithm thinks "weird" equals "good."

The grid thumbnails are a decent size, enough to get a sense of composition and color at a
glance. But you can't judge detail, texture, or whether an image actually holds up until you
click into the lightbox. The lightbox is where the real evaluation happens. The similar-images
strip at the bottom, powered by DINOv2 embeddings, is genuinely useful. It pulls up visually
related pieces and lets you surf laterally through the archive. That's the single best discovery
tool in the app.

I navigated through a handful of images in the lightbox. The standout from the novelty sort was a
chaotic composition with dozens of eyes scattered across a teal and red-orange background, a
central eye containing a tiny face, and a massive orange hand reaching upward. The color contrast
is electric. The image has a paranoia-inducing intensity that stops you mid-scroll. That's my
current pick for most visually striking piece in the archive.

The dark wolf-cat creature with glowing white eyes and visible fangs against a muted teal
background was also strong. The creature design is genuinely menacing, the color palette works,
and the linework has a rough, sketchy quality that adds character. The red wolf-head portrait with
aggressive ink-wash hatching is striking in a different way, more graphic and woodcut-like.

But here's the problem: the novelty metric doesn't track with any of this. The images I found
most compelling had novelty scores in the 0.59-0.61 range, which is mid-pack. The most novel
images in the grid were the least visually interesting. The metric is measuring something real
(distance from training distribution) but it's not measuring what I care about (does this image
actually look good).

So I switched to "Similarity to real art (high to low)" sort. The grid transformed. Suddenly I'm
looking at colorful, dense, compositionally coherent images. The top result was a bright yellow
and magenta chaotic composition that looks like Neo-Expressionist painting. Faithfulness=0.7319.
The faithfulness metric clearly correlates with "looks like something a human artist might have
made" better than novelty correlates with "looks good." But "looks like real art" and "is
genuinely striking" are still different things. Some of the high-faithfulness images are
competent but boring.

The UI has a lot of knobs. Type filter (style vs. conflict), category filter (MAP-Elites cells
with names like "negtrigger" and "allnight exploit" that mean nothing to a first-time user),
prompt filter, similarity range inputs, picked/favorited checkboxes. Most of these feel like
they're for the person who built the system, not for someone browsing for art. The category names
are jargon. The "i" info buttons exist but are small and easy to miss.

The "jump to another page" dropdown has a dozen options: Best images by area, Choose between two
images, Build one image trial, Run or monitor a search, Edit candidate ideas, Explore image
neighborhoods, Find gaps, Find near-duplicate groups. This is a power-user navigation system
crammed into a dropdown. A new user would never know these views exist.

What I never got: a clear signal for which images are actually the best. There's no "top picks"
view, no curated highlight reel, no taste-model powered recommendation that works. The "See
predicted favorites" option in the dropdown might be that, but I didn't get there before being
told to stop. The app assumes you already know how to navigate its internal logic.

I spent maybe 12 minutes on this. I'd estimate 4 minutes were genuinely productive browsing, 3
minutes were fighting stale refs and the page going blank on me, and 5 minutes were trying to
figure out what the UI's signals actually mean. The lightbox and similar-images strip were the
productive part. Everything else was overhead.

### UI claims that didn't hold up under scrutiny

- "How new or different" as default sort implies novelty correlates with quality. It doesn't.
  The most novel images are the most broken.
- The category names ("negtrigger", "allnight exploit", "round2 explore") are meaningless
  without context. They're developer-facing labels, not user-facing navigation.
- The grid view alone can't tell you if an image is good. You need the lightbox. The app should
  make that clearer.
- The "i" info buttons are too small and too hidden. A user who doesn't know to click them will
  never understand what the metrics mean.

### What actually helped me find good art fast

- The lightbox view with the similar-images strip. That's the killer feature. Surf laterally
  through embeddings and you find related pieces you'd never reach by sorting.
- The faithfulness sort. It's not perfect, but it surfaces visually coherent images faster than
  novelty sort.
- The prompt filter. If I know I want cats or owls, I can narrow to those. That's useful.
- The grid thumbnails are large enough to scan composition and color quickly. You can eliminate
  most images at a glance and only click into the promising ones.

### What I could finally see, that the last run couldn't

The previous run used a text-only model. It could navigate the UI and read metadata, but it
couldn't see pixels. Its "best image" pick was really just "highest metric value." Now I can
actually look.

The direct comparison is damning for the metrics. The image I'd pick as most visually striking
(the multi-eyed chaos with the reaching hand) has a novelty score of 0.6002 and faithfulness of
0.4206. It's not at the top of either sort. It sits mid-rank in both directions. The novelty sort
buries it behind more "different" images that are visually weaker. The faithfulness sort buries
it behind images that look more like traditional art but aren't as arresting.

Conversely, the top faithfulness image (the yellow/magenta Neo-Expressionist composition,
faithfulness=0.7319) is interesting but not the one I'd pick. It's competent and colorful but
lacks the visceral punch of the eye/hand piece.

The metric-only pick from the last run would have been whatever image had the highest combined
score. Without seeing the actual pixels, that's just number-crunching. With them, I can tell you
the numbers are measuring something real but different from what matters to a human viewer
looking for genuinely amazing art.

Status: DONE

## Verdict vs. original report

The vision-enabled redo delivers the whole point of the exercise: a genuine, pixel-grounded
verdict that neither `novelty` nor `faithfulness` reliably tracks visual quality, with a concrete
counterexample (Viktor's top pick sits mid-rank on both metrics). The original text-only run could
only note the "Elite"/"Best" mislabeling structurally (the app's own copy admits novelty ≠
quality); this redo independently confirms it empirically, from an actual side-by-side comparison
of images against their scores.

## Process note

This task took three dispatches to get a real final report (`oc_mrr8ys2x` crashed on a stale
Playwright element reference plus a provider 400 error; `oc_mrr966uw` completed with an empty
message, `step-finish reason: "unknown"`, after real browsing/screenshotting happened). Both were
resumed via `--session-id` per the crash-recovery protocol rather than re-dispatched fresh. The
final resume needed an explicit "stop browsing, write the report now" instruction to force output
after a step finished with `reason: "unknown"` — this is the third time this session `mimo-v2.5-free`
has produced a step-finish with no output, alongside Ines and Walt.
