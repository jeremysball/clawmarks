# Walt (older, money-anxious) — vision-enabled redo

Task ID: `oc_mrr9m8oh_6d2b9b2a` (final report; resumed from `oc_mrr8zrnn_58e4199c` after an empty
completion)
Model: `opencode/mimo-v2.5-free` (vision-capable)
Original run: [02-walt-money-anxious.md](02-walt-money-anxious.md), on `cheapestinference/glm-5.2`
(text-only, no image input)

## Why this redo

Walt's whole persona is judging whether a "Spends money" warning is genuinely eye-catching at a
glance, a question a text-only model can only answer from the accessibility tree (is the badge
present in the DOM), not from actual visual prominence (contrast, size, color, position). This
redo used a vision-capable model with explicit `browser_take_screenshot` instructions on every
page with a billable-looking control.

## Report

Alright, here's my report. I looked at every page this thing has.

**Walt's Usability Walkthrough Report**

OK so my grandson said "just look around, you can't break anything." But I don't trust that. I've
been burned before. So I went through every single page in this app and I'm going to tell you
exactly what I found.

**Page 1: The main gallery ("Browse all images")**

First thing I see is a big grid of artwork. Cats, wolves, owls, some weird abstract stuff. Looks
like a photo gallery. Fine so far. But then my eyes go to the top bar. There's a button that says
"TRENT_V3_EPOCH4/FREEFORM1" — I have no idea what that means. Is that a link? A setting? If I
click it, does it change something? Does it cost something? It's styled like a button but it
doesn't say what it does. That makes me nervous. There's also a "GUIDE" button and a "SESSION
STATUS" link. The dropdown says "Browse all images" and I can see it has other options like "Run
or monitor a search" and "Build one image trial." Those sound like they might DO something.
"Build a trial"? "Run a search"? That sounds like it could cost money. I didn't touch that
dropdown until I knew what those options did.

The filter controls (Sort, Type, Category, Prompt, Similarity, Search, picked only, favorited
only) all look like they just filter the gallery. Safe. The little "i" buttons popped up helpful
tooltips — I tried the one for Sort and it explained what "novelty" means in plain English.
Nothing about money there. Good.

**Page 2: "Best images by area" (Elite Archive)**

A grid of image cards with stats. Each card has a "VIEW ALL X IN THIS CELL" button. These look
like they just show more pictures. No cost warnings. Safe.

**Page 3: "Choose between two images" (Compare)**

Two big images side by side with "OR" between them. I click one to vote. There's a progress bar
saying "Model unlocks in 50 votes." Just voting, not spending money. Safe.

**Page 4: "Build one image trial" (Generation Cockpit) — THIS IS THE PROBLEM PAGE**

Whoa. This page has a LOT of controls. Mission buttons, a prompt text box, batch size, LoRA
strength, seed strategy... and at the bottom there's a button that says "Send draft to queue."
That sounds like it might actually DO something — like generate images on a GPU. Which costs
money. And I looked everywhere on that page — I searched for "spend," "cost," "money," "bill,"
"price," "GPU," "charge" — ZERO. Nothing. Not a single word about money anywhere on the entire
page. The "Send draft to queue" button has no warning, no badge, no label telling me this will
cost real money. That button sends work to be generated on a paid GPU and there is absolutely no
visible warning. If I were a real user, I might click that just to see what happens. That's
terrifying.

There's also an "Autopilot" tab at the bottom. No tooltip, no warning, nothing. I don't know what
that does but it sounds like it runs things automatically. On a paid GPU. With no warning.

**Page 5: "Run or monitor a search" — THIS ONE GETS IT RIGHT**

OK, THIS page has a "Back up and launch" button and right next to it is a purple/magenta badge
that says "SPENDS MONEY" in all caps, white text on purple. That badge is visible. The purple
stands out against the beige background. It's small — maybe the same height as the button text —
but it's clearly there and it's right next to the button. If I were about to click "Back up and
launch," I'd see that badge. I'd stop. Also, the page shows "Spend: started $9.91" in the report
section, so there's real dollar amounts visible. That's useful context.

**Page 6: "Edit candidate ideas" (Candidate Seeds) — ALSO GETS IT RIGHT**

A "Generate" button with the same purple "SPENDS MONEY" badge right next to it. Same design, same
position. Consistent. Good.

**Page 7: "Check taste-model readiness" — ANOTHER UNLABELED ONE**

There's a "Retrain now" button. Retraining a model sounds like it would cost money — it uses
compute. And there's no "Spends money" badge on it. No warning at all. That's another unlabeled
billable control.

**Pages 8-13: The rest**

"Explore image neighborhoods" (scatter plot), "Find gaps in the image space" (coverage grid),
"Find near-duplicate groups" (placeholder), "See which prompts are running out" (placeholder),
"Trace image ancestry" (placeholder), "See predicted favorites" (placeholder) — all safe, no
billable controls.

**Image detail view**

Clicking an image opens a dark overlay with a big version of the picture, navigation arrows, and
two buttons: "favorite" and "generate counterfactual." The "generate counterfactual" button — hold
on, does that cost money? I didn't see a "Spends money" badge on it. But it has an "i" info button
next to it. I didn't get to check what that one does. That's suspicious.

### Controls I was unsure about and why

- **"TRENT_V3_EPOCH4/FREEFORM1" button in the header** — It's styled as a button but has no
  label explaining what it does. Could be navigation, could be a setting, could trigger
  something. No tooltip. I avoided it.
- **"Send draft to queue" button on Generation Cockpit** — This is the most dangerous one. It
  clearly sends work to be generated on paid GPU hardware. There is zero cost warning anywhere on
  the page. No badge, no text, nothing.
- **"Autopilot" tab on Generation Cockpit** — Sounds like it runs things automatically. On a paid
  GPU. No warning, no tooltip, no explanation.
- **"Retrain now" button on Preference Classifier Status** — Retraining a model uses compute. No
  cost badge. The button is active and clickable.
- **"generate counterfactual" button in image detail view** — The name sounds like it generates
  something. Has an "i" info button but I couldn't tell if it costs money. No "Spends money"
  badge visible.
- **"Back up and launch" button on Search Runs** — I was unsure at first, but then I saw the
  "SPENDS MONEY" badge. That one is labeled correctly.

### What made me feel safe

- The "SPENDS MONEY" badges on "Back up and launch" and "Generate" (candidate seeds) —
  purple/magenta background, white text, all caps, positioned directly to the right of the
  button. Clear and unambiguous.
- The "i" info popovers — dark background, white text, readable, and they explain things in
  plain language without any cost implications.
- The filter controls on the gallery page — obviously just filtering, nothing executable.
- The Compare page — just voting, progress bar shows how many comparisons I've done.
- The "Session Status" link — just shows status, read-only.
- The "picked only" and "favorited only" checkboxes — obviously just filters.
- The navigation dropdown options that are clearly read-only ("Browse all images," "Best images
  by area," "Explore image neighborhoods," etc.).

### What I could finally see, that the last run couldn't

The "SPENDS MONEY" badge on the "Back up and launch" button is a purple/magenta rectangle with
white text in all caps. From the actual screenshot: it sits immediately to the right of the
button, same vertical alignment, roughly the same height as the button text but narrower. The
purple color (#7B2D8B or similar) contrasts well against the beige/tan page background (#D2C9B5
or similar). The white text on purple has good legibility. At 1440x900 desktop resolution, the
badge is small but readable — maybe 80px wide and 20px tall. It's not huge, but if you're looking
at the button, you'll see it. The same badge appears on the "Generate" button on the Candidate
Seeds page, in the same position and style. Consistent design.

However: the Generation Cockpit's "Send draft to queue" button has NO such badge, even though it
does the exact same kind of thing (sends work to be generated). That inconsistency is the biggest
problem. An anxious user who learned to look for the purple badge on one page would not find it on
the most dangerous page in the app.

Status: DONE

## Verdict vs. original report

The vision-enabled redo confirms the "SPENDS MONEY" badge is genuinely well-designed where it
exists (real contrast, real size, consistent position), which the original report could only infer
from markup. It also sharpens the original's cost-warning-inconsistency finding into a concrete,
prioritized list: "Send draft to queue" (Generation Cockpit) has zero warning of any kind despite
triggering paid GPU work, "Retrain now" and "generate counterfactual" are similarly unlabeled. This
strengthens the existing cross-cutting finding on inconsistent billable-control warnings with a
first-hand visual confirmation that the pattern users would learn from the correctly-labeled pages
("look for the purple badge") fails silently on the most dangerous page in the app.

## Process note

This task needed one resume: the first dispatch (`oc_mrr8zrnn`) did real work (66 tool calls
across all major pages) but completed with a trivial one-line message instead of a report. Resumed
with an explicit "stop browsing, write the report now" instruction, same pattern as Ines and
Viktor this round.
