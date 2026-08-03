# Ines (color-blind UX auditor, deuteranopia)

Task ID: `oc_mrr93vrk_3159cc07` (final report; resumed from `oc_mrr90l16_8c8aa0b0` after an empty
completion)
Model: `opencode/mimo-v2.5-free` (vision-capable)
New persona for this batch — audits color-only meaning encoding (charts, badges, status
indicators) for someone with deuteranopia (red-green color blindness, the most common form).

## Report

Hi. I'm Ines, 38, UX auditor with deuteranopia. I spent about 15 minutes clicking through
CLAWMARKS at desktop resolution. Here's what I found.

**Gallery grid (scan.html)**

The first thing I notice is the thumbnail cards have colored inset shadows that flash their type.
I pulled the actual CSS: `conflict` cards use `rgb(224, 162, 94)` (warm orange/amber) and `style`
cards use `rgb(94, 201, 138)` (green/teal) as a 2px inset box-shadow. Orange and green is the
single most common collision pair for deuteranopia. To my eyes both look like a similar muddy
tan. There is no icon, pattern, or text label printed directly on the thumbnail itself that
distinguishes them. I *can* read the image name below each card (e.g.
`conflict_pure_abstract_brushed-pa` vs `style_close-up_cat_face_portra`), so the filename prefix
saves me. But if I'm scanning the grid quickly for "which ones are conflict vs style," the color
flash does nothing for me and I have to read every label.

**Coverage / void map (coverage.html)**

This is a blue sequential heatmap (light-to-dark blue by image count) with numeric count labels
on each occupied cell and "F" labels on frontier cells. Blue is not affected by red-green color
blindness, and the brightness ramp is clear. The numeric labels and "F" text are redundant
encodings. The prose says "Gold-outlined cells are empty but sit next to a dense cell" but the
computed CSS shows the gold outline is either not rendered or uses the same gray border as every
other cell. The "F" label is the only reliable secondary signal, and it works. No issues here.

**Solution map (map.html)**

The scatter plot has three color-by modes:

1. **generation (ghosted)**: All dots are the same blue/gray shade against a dark background. No
   hue discrimination needed. Fine.
2. **prompt type**: This is the problem. Dots switch to orange and green to distinguish "style"
   from "conflict." Same collision pair as the gallery thumbnails. On a dark background, both
   colors look like similar brownish dots to me. There is **no legend** that says which color is
   which. The only way to find out is to hover over individual dots. For a scan of 50+ dots,
   that's unusable.
3. **picked**: Orange vs gold dots. The legend says "gold dot = picked winner." Orange and gold
   are close enough in lightness that a picked-vs-not-picked distinction relying on hue alone is
   fragile, though the size/brightness difference helps a little. Since nothing is picked in this
   dataset, the issue is theoretical right now.

The **nearest real training image** bar chart below the scatter uses solid black bars with
filenames and count numbers. No color at all. Clean.

The **legend** at the bottom-left of the scatter reads: "white dot = real training photo, gray
dot = generated, gold dot = picked winner." This legend has text labels next to each color
swatch. Good. But it only covers the default generation mode, not the prompt-type mode.

**Elite archive (archive.html)**

Each card has a "highest novelty" badge (dark background, white text), plus gold-bordered cards
for favorites and blue-bordered for model-picks. The gold vs blue border is a single-hue
distinction, but the page text explains the meaning clearly, and the badges carry text labels.
The "VIEW ALL X IN THIS CELL" buttons are plain bordered rectangles. No red-green collision here.

**Compare page (compare.html)**

Two images side by side with "OR" text between them. Progress bar is gray-scale. "Model unlocks
in 50 votes" is text. No color-coding at all. Perfectly accessible.

**Search runs (runs.html)**

The "SPENDS MONEY" badge is purple with white text. Purple contains blue, which I can see fine.
The text itself is the primary warning. The "NOT RUNNING." status is bold red text on a gray
background. Red text is harder for me to distinguish from dark brown or black, but the bold
weight and the period-terminated phrasing make it readable as a status label even without hue.

**Cockpit (cockpit.html)**

Four mission cards in a row. The selected one has a darker background. Selection is confirmed by
a checkmark and bold text. No color-only state. Clean.

### Color-only signals that would fail for red-green color blindness

- Gallery thumbnail inset shadows: `rgb(224, 162, 94)` (orange, conflict) vs `rgb(94, 201, 138)`
  (green, style). These are a textbook deuteranopia collision pair with no icon, pattern, or
  on-card text label to distinguish them. The filename prefix below each card is the only way to
  tell.
- Solution map "prompt type" mode: orange vs green dots with **no legend and no text labels** on
  the dots themselves. Indistinguishable without hovering.
- Solution map "picked" mode: orange vs gold dots. Closer in lightness than the prompt-type pair,
  making the picked/not-picked distinction rely on subtle hue shift. The legend text helps but the
  dots themselves carry no text.

### Places where redundant encoding (text/shape/icon) already saved the day

- Gallery filenames: Every card shows its full name (`conflict_...` or `style_...`), so the type
  is readable even when the shadow color fails.
- Coverage map: Blue sequential scale (safe for deuteranopia) plus numeric count labels and "F"
  frontier labels on every cell.
- Coverage map legend: The color bar at the bottom has numeric tick marks ("1", "median 2",
  "max 4").
- Solution map legend: Text labels next to each legend swatch ("real training photo",
  "generated", "gold dot = picked winner").
- Nearest-real-image bar chart: Pure black bars with filenames and count numbers. Zero color
  dependency.
- Elite archive badges: "highest novelty" text badges, "VIEW ALL X IN THIS CELL" button labels,
  gold/blue border explained in prose.
- "SPENDS MONEY" badge: Purple with explicit text. The warning is readable without color.
- "NOT RUNNING." status: Bold text with period emphasis. Readable without hue.
- Compare page: Spatial "OR" label, text instructions. No color coding.
- Cockpit: Checkmark icon and bold text for selection state.

Status: DONE

## Notes

Two new, actionable findings not previously flagged by any persona: the gallery grid's
type-indicator shadow color (orange/conflict vs green/style) is a direct deuteranopia collision
with no redundant signal on the card itself, and the solution map's "prompt type" color mode has
no legend at all (unlike its default "generation" mode, which does). Both are cheap fixes (an
icon or short text tag alongside the existing color, and a legend for the missing color mode).

## Process note

This task needed one resume: the first dispatch (`oc_mrr90l16`) did real browsing/screenshotting
work but completed with an empty message (`step-finish reason: "unknown"`). Resumed via
`--session-id` with an explicit "write up your findings now" prompt, per the crash-recovery
protocol.
