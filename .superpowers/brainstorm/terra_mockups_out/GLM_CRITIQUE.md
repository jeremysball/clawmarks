# Critique: generation cockpit mockup v3

File reviewed: `mockup-a-v3-target-picker-tooltips-theme.html`
Viewed live at 1440×900 (desktop, light theme resolved) and 390×844 (mobile, light theme).
All measurements below came from Playwright snapshots and `getComputedStyle`, not from eyeballing the
source. Page renders; no console errors. The DOM tree and the data-binding script behave as
designed. The problems are design, not bugs, except where noted.

---

## 1. The owner's complaint, taken head-on: mobile has no hierarchy

At 390×844 the document is **2228px tall for an 844px viewport** (measured). The recipe panel alone
is **1075px**, the evidence panel **594px**. So the user's "nothing has more weight than anything
else, there is no logical flow" is literally true: a phone user scrolls through ~2.7 screens of
nearly identical gray surfaces before reaching the cost button. Concretely, here is the mobile
top-to-bottom order and what is wrong at each step.

**1a. The mission bar scrolls away.** The mission strip is the first real decision (which of four
intents you are running), and at 390px it is rendered as a 2×2 grid of ~178×86 torn-paper scraps,
then it leaves the viewport forever. There is no sticky version. While you edit the recipe one
screen down, your *current mission* is invisible. For a tool whose whole posture is "choose an
intent, then act deliberately," the intent should stay on screen. **Fix:** make `.mission-bar`
`position: sticky; top: <nav height>` on mobile, or collapse it to a one-line "Mission: Fill a
coverage gap ▾" once a choice is made, so the current intent rides along the top.

**1b. Three of the four missions look identical to the active one.** Active mission gets
`--ultramarine` fill and `rotate(0)`. On a phone, four ~178×86 scraps in a 2-up grid do not read as
"one chosen, three available"; they read as four equal buttons with one slightly bluer. The
inactive scraps also carry the same caption stack ("Mission" eyebrow / bold name / one-line
description) at the same type size, so scanning "which did I pick" requires reading. **Fix:**
collapse the non-active three to a single-line chip ("Develop a candidate  ▸") once one is chosen,
and give the active mission a brighter state (acid underline, a checkmark glyph, "STEP 1 —
chosen"). The goal is to make *the selection* the visual event, not the four-way menu.

**1c. The target-cell picker and the form fields use the same surface.** `.target-card` uses
`background: var(--field)` (`#e6dac4` in light) — the **exact same background as `<input>` and
`<textarea>`**. The cards are tappable choices; the inputs below are typeable. On mobile, stacked
full-width (each card measured 342×58), they look like four more rows of the same form. The thumb
cannot tell "choice" from "field". **This is the single biggest contributor to the flat-stack
feeling.** Fix: choices get the `--card`/`--paper` surface with a left-accent rail and a visible
selection glyph; inputs keep `--field` with the bottom-underlined look. Two surfaces, two
affordances.

**1d. Selected state on target cards is too quiet.** Selected card differs from unselected by a
3px acid bottom border (vs. the unselected 1px seam) and an 18%-mix ultramarine tint
(`color-mix(in srgb, var(--field) 82%, var(--ultramarine))`). On a 342×58 stacked card the acid bar
is **3px tall**, i.e. 5% of the card. Easy to miss while scrolling. **Fix:** give the selected
card a full-height left rail (4–6px acid), a checkmark glyph in the thumb slot, and a stronger bg
tint, e.g. `color-mix(var(--field) 70%, var(--ultramarine))`. Selection should be glanceable from
across the screen, not detectable by a thin underline.

**1e. The `?` tooltips are unreachable on touch devices.** The tooltip is `opacity:0;
visibility:hidden` and only opens on `:hover`/`:focus`. On a phone there is no hover, and tapping
the `<button>` fires click without toggling open (there is no `tap-to-toggle` handler, no
`aria-describedby`, no `title`). I confirmed with `getComputedStyle` that all seven `info-btn`
tooltips report `visibility: hidden` at 390px. So on the very device the owner is complaining
about, **every "Explain faith and novelty / coverage grid / prompt similarity" affordance is a dead
button**. Fix: make the `info-btn` a `<details>`-style tap-toggle (tap opens, tap outside closes),
or move the explanation inline as a one-line disclosure under the heading. Right now the mobile
user gets the "?" but none of the words behind it.

**1f. `.controls` collapses to a 1-column stack at ≤640, making three unrelated controls look like
three more rows of the same form.** Seed strategy, batch size, and LoRA strength turn into three
full-width 35px-tall rows, each with its mono label above and the same `--field` surface and 1px
bottom seam styling as the brief inputs above them. This is the breakpoint *creating* the flatness
the owner is reporting, not solving it. Three controls at 35px + labels = ~150px of vertical stack
that could be **one row** (~110px wide × 3 = 330px + gaps fits in 390 easily). **Fix:** keep
`.controls` at 3 columns down to ~520px instead of dropping to 1fr at 640. They share a "sampler"
row; that row is one visual unit, not three.

**1g. `.brief` and `.advanced-body` do the same thing.** `.brief` (hypothesis + target) drops
two short fields to a vertical 1fr stack at 640; `.advanced-body` (sampler/steps/CFG/etc.) drops a
3-col grid to 1fr at the same breakpoint. Each one lengthens the recipe column with full-width rows
that look like every other full-width row. The advanced body is the worst case: a collapsed
"Advanced…show" toggle that, when expanded, becomes a *long tail* of equal-weight full-width inputs
exactly when the user is already overwhelmed. **Fix:** let `.brief` stay 2-col down to ~440, and
let `.advanced-body` stay 2-col on mobile (3-col is genuinely too tight at 390, but 2-col at
~165px each is fine). Shorten the advanced tail by removing fields the solo user rarely changes, or
move advanced into a slide-over rather than inline expansion.

**1h. The cost-incurring CTA is buried mid-page and shares its label with the drawer's button.**
Recipe panel ends with `.action-row` = estimate text + "Queue trial" (the `.generate` button, 342×36
full width). Then **~594px more evidence** scrolls past. Then the fixed bottom drawer. The drawer's
own action button is also labeled **"queue trial"** (`#queueRun`) — two different buttons with the
same visible label on the same page. On desktop both are visible simultaneously; on mobile the
recipe one scrolls past and the drawer one is bottom-fixed. A user reasonably asks "which Queue
trial actually queues, and what is the other one for?" **Fix:** rename one. The recipe button is
"Send draft to queue"; the drawer button is "Run queued trial". Different verbs for different
verbs.

**1i. No step scaffolding.** The page has exactly two `.section-tag` chips ("Recipe", "Evidence")
and one `.eyebrow`. That is the entire hierarchy signal. On mobile the chips are 12px stamped
rectangles; they do not establish "this is step 2 of 3." The mission-card → target-picker → brief →
refs → prompt → controls → advanced → action flow is a real sequence with a real order, but nothing
in the layout tells the eye "you are here." **Fix:** introduce a numbered step rail or a step
header per group ("1 — Choose target", "2 — Draft recipe", "3 — Confirm and queue") at mobile
widths. The flow already exists in the data; it just is not surfaced.

**1j. Head weight before the first interactive element.** Before the user reaches the first mission
button at 390px they pass `.eyebrow` ("Interactive trial workbench") + `h1` (25px "Generation
cockpit") + `.sub` (two-line muted paragraph). That is ~120px of decorative header. On a
scroll-heavy mobile flow it delays the first decision. **Fix:** collapse the eyebrow+sub into a
single smaller subtitle, or move them into the mission-bar's own header. The page can keep its
identity without spending a ninth of the first screen on a title block.

---

## 2. Broader critique (desktop + mobile)

### 2.1 Typography and type identity

- The `--stamp` stack is `"Arial Narrow","Helvetica Neue Condensed",sans-serif`. On Linux (the
  RunPod dev box, this sandbox) and on Android, **neither face exists**, and everything stamped
  falls back to generic `sans-serif`. I confirmed the computed `font` on `.generate` resolves to
  `800 12px "Arial Narrow","Helvetica Neue Condensed",sans-serif`, but Android/Linux will render
  the fallback. The whole condensed/stamped identity is OS-dependent and silently disappears on
  the user's non-Apple devices. **Fix:** ship a webfont (Oswald, Barlow Condensed, Bebas Neue) or
  widen the fallback so the look survives.
- Body is 13px/1.45, labels 11px mono, meta 10.5px mono, badges 10px, eyebrows 10px, honest 10px
  stamp. **A lot of 10–11px text.** On a phone, 10px is below the comfortable reading floor.
  Bump mobile body to 14px and the small/label tier to 12px minimum at ≤640.
- Heading scale jumps unevenly: `h1` 25px → `h2` 16px → `h3` 11px stamp. `h2` at 16px is barely
  larger than the 13px body and smaller than the 14px mission `b` chips above it. The `h2` carries
  the trial title ("Reach the sparse owl-on-paper frontier"), the most important single sentence on
  the page, and it reads as a body-weight line. **Fix:** raise `h2` to ~19–20px or give it the
  stamp treatment with a tighter scale to `h1`.

### 2.2 The collage / paper-craft vocabulary

- **Torn mission strips** — best piece in the file. Irregular `clip-path` polygon edges, per-card
  rotation (`-1.2 / 1.1 / -.7 / .9` deg), per-card bg tint. Conceptually right. Two issues:
  (a) The `clip-path` clips `box-shadow`, so `.mission.active{box-shadow:0 7px 18px
  var(--shadow)}` is **invisible** — confirmed because `clip-path` is set on the same element, and
  shadow cannot escape the polygon. The active state's lift is doing nothing. Either drop the
  box-shadow (rely on color + rotation reset) or wrap the clip-path in an outer element that holds
  the shadow. (b) On the 2×2 mobile grid with equal sizes, the rotation reads as
  "buttons-askew," not "tossed scraps." Real collage scraps have different sizes and overlaps. On
  desktop the four equal widths (27/23/28/22%) already looks more like a progress bar than scraps.
- **Tape-corner thumbnails** — the `:before` tape strip (16×7, rotated 38°) at the corner is a
  nice realistic touch. The `:after` "animal face mask" (`border-radius:48% 52% 40% 42%`, rotated
  -9°, an inner ring on the gradient swatch) does not read as an animal silhouette at 35–40px; it
  reads as a soft blur inside the thumbnail. The thumb swatches are 4-stop diagonal gradients
  standing in for art — fine for a mockup, but the `:after` adds noise, not signal. **Fix:** drop
  the `:after`, or replace it with a more deliberate mark (a single claw-stroke glyph, an ink dot,
  a real compositional anchor). Don't leave it as a half-readable squiggle.
- **"Redaction-bar" section labels** — the `.section-tag` is a solid-filled `--ultramarine`/
  `--crimson` rectangle with white stamped text. That is a *label pill*, not a redaction bar. A
  redaction bar implies text under it that has been censored and partially revealed. The current
  element does not deliver the "redacted archive" idea in the design rationale; it just looks like a
  colored tag. Either lean into redaction (text visible through a torn/shifted bar giving a
  kraft-and-black-out vibe) or drop "redaction" from the vocabulary and call it a tag.
- **The workbench panels themselves are not paper.** `.panel` is a flat `--paper` rectangle with a
  1px `--seam` border and no shadow, texture, or deckled edge. The collage lives in the mission
  scraps and thumbs only; the two main work surfaces read as plain admin-dashboard cards. For a
  page titled "collage workbench," the *workbench* should be the most paper-like surface of all.
  Consider a faint paper grain, a 4–6px warm drop-shadow, or a deckle/torn top edge on `.panel` so
  the whole sheet reads as pinned paper, not as a card.

### 2.3 The target-cell picker

- Behavior works: tapping a card flips `aria-pressed`, updates the readonly `#target` input,
  re-renders the `#miniGrid`, and rewrites `#coverageText`. Good wiring.
- Card content is dense and unframed: `"faith 0.49-0.57, novelty 0.67-0.74" / "adjacent to 17
  images"` shares one line range and a smaller muted subline. The two axes are comma-joined; the
  eye cannot compare "is this cell higher-faith or higher-novelty than the next?" across the three
  cards at a glance. **Fix:** two-row card: `Faith 0.49–0.57` / `Novelty 0.67–0.74`, with the
  adjacency number promoted to a small bold summary ("17 adjacent") rather than a muted footer.
- The picker offers three equal cells, but the mission is "fill a coverage **gap**," which implies
  one of the three is the *best* reachable gap. Picker gives no ranking or recommendation. Sort the
  three by reachability and visually anoint the top one (e.g. an "recommended" acid flag on
  cell 1), so the solo user who does not want to study 16-cell mini-grids gets a default answer.
- The picker `h3` is a plain 11px mono label, no step number, no help beyond the inaccessible `?`
  tooltip. The decision "which cell to target" is the substance of the gap mission; its container
  is the same gray panel as every other section. **Fix:** treat the picker as its own framed
  block, not a row inside the recipe panel; see step-rail proposal in 1i.
- When the user switches missions away from `gap`, the picker is `hidden` and the readonly target
  input shows static text ("Candidate seed: …", "Parent: …", "No target selected"). A readonly
  `<input>` carrying display-only data looks typeable/tappable on mobile but is not. **Fix:**
  replace the `<input readonly>` with a static labeled value for non-gap missions (label +
  value row), reserving the input style for genuinely editable fields.

### 2.4 Tooltips

- Width 210px, anchored above the `?`, centered on the button (`left:50%; transform:translateX(-50%)`).
  On the current 390 layout the visible `?` buttons sit far enough left that the tooltip fits (max
  right edge measured 360px on tip i=5, 30px from the viewport edge). There is **no clamping**, so
  on a 320px-class phone (iPhone SE-ish) or for any future `?` placed near a right edge, the tooltip
  will clip off-screen. **Fix:** clamp via `min/left:8px` and `max-width` with
  `transform-origin: top left/right` when near a viewport edge.
- Tooltip content is reasonable, but **two of the three "faith/novelty" tooltips are verbatim
  duplicates** (one in the target-picker `h3`, one in the "Nearest past prompts" `h3` — both say
  the same faith/novelty definition). Repeating identical text under two headings is noise. One
  shared inline definition near the first use is enough.
- See 1e above: hover/focus-only means **mobile gets nothing**. This is the most serious tooltip
  problem and a real content loss on the owner's device, not just a polish issue.

### 2.5 Light theme

- The cream/kraft palette is on-brand and warm: `--bg:#e8dfcc`, `--paper:#f4eddd`,
  `--field:#e6dac4`, `--ink:#29251f`. Good base for a paper-craft tool. The *concept* is right.
- **Surface separation collapses in light theme.** `--paper` (#f4eddd) on `--bg` (#e8dfcc) with
  a `--seam` of `rgba(57,48,37,.24)` (a 24%-alpha brown) is nearly invisible. On desktop the
  recipe/evidence two-pane split — the page's main structural division — is barely detectable. The
  whole page reads as one sheet of paper with faint ruled lines. If that is the intent ("single
  workbench sheet"), the two panels should still differ subtly (a tape line, a deckle edge, a
  2-step bg delta). Right now they read as "the same card twice."
- **Tape on thumbnails disappears in light theme.** `--tape` becomes `rgba(246,236,211,.8)`,
  which is nearly the same as `--paper` and almost the cream bg. The tape strip on thumbnails
  reads as a faint sheen, not tape. **Fix:** bump light-theme tape contrast (slightly more yellow,
  or add a faint edge) so the collage motif survives.
- **Per-card mission tint differentiates less in light theme.** Cards 2 and 3 become `#d4c7b0`
  vs the default `--card:#d8ccb6` — a ~5/255 unit delta. The "different colored scraps" feel that
  sells the collage almost vanishes in the cream theme. Same for the inactive card tints
  (`:hover:#cbbda4`).
- `--acid` becomes `#657a16` in light (a muted olive). On dark theme `--acid:#c4d94a` is vivid;
  in light it loses energy, so "kept" / "Existing evidence only" / the eyebrow accent all read
  muddier. **Fix:** pick a greener olive like `#5e7a0e` or push toward the acid-yellow end at
  `#7d8a14` to recover the pop.
- The light theme is gated entirely on `prefers-color-scheme`. There is no manual toggle, so a
  light-mode OS user is locked to cream. Given that **cream/paper is the on-theme look for this
  product**, light should arguably be the *primary* theme, not a derivative. Right now dark feels
  like the more "designed" of the two (the acid pops, the seams read, the badge borders show). Either
  invest in the light theme until it carries as much identity as dark, or add a manual toggle.

### 2.6 A few real bugs spotted

- `.mission.active` has `box-shadow:0 7px 18px var(--shadow)` that is clipped away by the same
  element's `clip-path` (see 2.2). The active lift is a no-op.
- `.estimate` markup is `<b>4 images</b> · estimated 3m 08s<br>New images will enter the trial
  record as a draft.` Two distinct sentences (an estimate and a disclaimer) are joined only by a
  `<br>`. There is no spacing and no semantic break; the disclaimer reads as a continuation of the
  estimate. Use `<p class="small">` for the disclaimer, or add margin below the `<br>` line. (The
  rendered visible text only works because the `<br>` happens to start a new line visually;
  text-extraction and copy-paste concatenate them, which is how the snapshot reported
  "3m 08sNew images.")
- Two buttons on the same page both display "queue trial" — the recipe `.generate` and the drawer
  `#queueRun` (see 1h). Different actions, same label.
- The drawer's `#queueMeta` is hardcoded `4 images · random seeds · 1.00 strength · DDIM / 28 /
  7.5` and does not update when the recipe changes (batch size stepped up, seed strategy toggled
  to fixed, advanced sampler adjusted). The queue preview is stale relative to the draft. Not
  design per se, but it undermines the honesty posture the page is going for — the trial card
  claims a configuration the recipe no longer holds.

---

## 3. What is working (so it does not get cut)

- The "Honest evidence, not a forecast" framing is the soul of the page and it is reinforced
  everywhere: `.honest` eyebrow, the disclaimer `.small` under the evidence `h2`, the
  "evidence is close, not predictive" badge, the tooltip "It does not say whether the resulting
  image will be good." That consistency is excellent; do not soften it.
- The two-type-family system (condensed stamp for headers/CTAs, mono for data/labels) is the right
  call for a research-tool-meets-collage product. It just needs the webfont fix (2.1) and a wider
  size delta between `h2` and body.
- The mission-driven content swap (`setMission`) is soundly wired: title, hypothesis, prompt,
  queue title, target label, and picker visibility all update together. The mechanic is right;
  only its visual hierarchy on mobile is the problem.
- The mini coverage grid (4×4, 16px cells, target cell outlined in acid, live cells in
  ultramarine) is a good honest summary of "what is around this cell." On desktop it sits next to
  its explanation in a clean 76px+1fr grid. Keep this. On mobile it currently drops below the
  recipe and loses its adjacency to the target picker (see 1); restore that adjacency and the
  grid earns its keep.

---

## 4. Short list of the highest-leverage changes

In priority order, for whoever picks this up next:

1. Make the mission bar sticky on mobile, or collapse it to a one-line "Mission: X ▾" once chosen
   (1a, 1b).
2. Differentiate choice surfaces from input surfaces: target cards on `--card`/`--paper` with a
   left acid rail and a check glyph; inputs keep `--field` (1c, 1d).
3. Make the `?` tooltips tap-to-toggle on touch, or move explanations inline (1e).
4. Keep `.controls` and `.brief` multi-column down to ~440–520px instead of dropping to 1fr at
   640; the 1fr collapse is *producing* the flat stack the owner is reacting to (1f, 1g).
5. Rename one of the two "queue trial" buttons; add a step rail / numbered step headers at mobile
   widths so the page reads as a sequence, not a pile (1h, 1i).
6. Ship a condensed webfont so the stamped identity survives Linux/Android (2.1).
7. Fix the clipped active-mission shadow (clip-path eats box-shadow), the `<br>`-joined estimate
   text, and the stale `#queueMeta` (2.6).
8. Strengthen light-theme surface separation and tape contrast so the cream theme reads as
   primary, not as a derivative of dark (2.5).

=== CRITIQUE DONE ===