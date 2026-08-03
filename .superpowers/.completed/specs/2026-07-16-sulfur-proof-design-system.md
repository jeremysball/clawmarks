# Sulfur Proof Site Design System

## Goal

Apply one distinctive visual language across the complete curation site: an olive-gray working
proof, dense process-black hierarchy, and muted sulfur annotation. The system must improve reading
order and evidence legibility without wrapping every item in a card.

This specification supersedes the visual tokens, dark-theme default, typography, and component
surface rules in `2026-07-10-tool-suite-ui-design-brief.md` and other earlier page specifications.
Those documents still govern behavior that this specification does not replace.

## Visual Principle

The page is a working print proof, not a paper-themed dashboard.

- Olive-gray paper forms one continuous workspace.
- Visible fine ruling and mild tonal variation make the workspace read as proofing paper rather
  than a flat gray application background.
- Dense black ink creates hierarchy through type scale, rules, reversal, and negative space.
- Sulfur behaves like translucent annotation material: underlines, hatching, registration halos,
  selected states, and compact active marks.
- Abstract skeuomorphism gives important controls and decision surfaces crisp physical depth without
  imitating a specific real-world object.
- Real CLAWMARKS images carry visual weight. Interface chrome remains restrained.
- Sections use spacing and rules before containers. A bordered panel needs a functional reason,
  such as clipping a map or separating the Guide from its source page.

## Color Tokens

```css
:root {
  --paper: #C3C5BA;
  --paper-deep: #B3B5A9;
  --ink: #11120F;
  --text-soft: #4D5048;
  --rule: #898D81;
  --sulfur: #CBD63F;
  --guide-surface: #20251B;
  --guide-ink: #ECEFDF;
}
```

Measured contrast ratios:

| Pair | Ratio | Use |
| --- | ---: | --- |
| `--ink` on `--paper` | 10.75:1 | primary text |
| `--text-soft` on `--paper` | 4.70:1 | normal secondary text |
| `--guide-ink` on `--guide-surface` | 13.40:1 | Guide text |
| `--sulfur` on `--guide-surface` | 9.86:1 | Guide highlights |
| `--ink` on `--sulfur` | 11.84:1 | compact selected controls |

The original `#55594F` secondary token reached only 4.10:1 on paper and is not approved for normal
text. Rules and decorative marks need not meet text contrast, but they cannot carry meaning alone.

Status colors must remain distinct from sulfur selection. Error, warning, success, and running
states require text or an icon in addition to color. Their final accessible tokens may extend this
palette during implementation.

## Typography

- **Display and condensed headings:** Barlow Condensed, weights 600 through 800.
- **Body and controls:** IBM Plex Sans, weights 400 through 700.
- **Metadata and receipts:** IBM Plex Mono, weights 400 through 600.

Production assets must be self-hosted or bundled. Pages must not depend on Google Fonts or another
runtime network request. Fallback stacks are:

```css
--font-display: "Barlow Condensed", "Arial Narrow", sans-serif;
--font-body: "IBM Plex Sans", Arial, sans-serif;
--font-mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
```

Headings may use uppercase when they remain short. Body text and research questions use sentence
case. Metadata labels may use uppercase with tracking. Normal body text starts at 14px on desktop
and 15px on mobile; explanatory text must not shrink into 10px dashboard copy.

## Layout

- Desktop content uses the full useful width with 22px to 30px side gutters.
- Major sections separate with 1px or 2px ink/rule lines and 24px to 54px vertical space.
- Editorial headlines establish the first eye path. Evidence, action, and metadata follow in that
  order.
- Maps and large images may use dark reversed surfaces when contrast helps the evidence.
- Three-column evidence layouts collapse to one column before text becomes cramped.
- Horizontal overflow is reserved for image strips, data grids, and the compact workflow stepper.

## Dimensional Grammar

The interface uses tactile, dimensional cues instead of soft neumorphism:

- raised controls use a 1px to 2px light inner edge on the top and left, a darker inner edge on the
  bottom and right, and a hard 3px to 6px offset shadow with no blur;
- recessed instrument areas reverse the inner light and dark edges and use no outer shadow;
- press states remove the outer shadow and move the control into its former offset;
- hover states increase the hard offset by 1px to 2px;
- paper, deep paper, and ink create depth; sulfur remains a small registration or active-state mark;
- data rows, prose, and ordinary section boundaries stay flat so depth continues to signal meaning.

Use raised surfaces for actions, selected decisions, map callouts, paid-payload confirmation, and
bounded evidence objects. Use recessed surfaces for context receipts, composers, counters, and
instrument readouts. Do not place every section in a raised container.

Depth has three approved strengths:

1. **Shallow raised readout:** a 1px rule, 1px inner edges, and a hard 3px shadow. Use this for the
   active research question and compact working-state summaries.
2. **Mounted working piece:** 1px to 2px inner edges and a hard 4px to 5px shadow. Use this for
   labeled evidence images and the Next Decision plate.
3. **Light detent:** a 1px rule and 1px to 2px reversed inner edges with no outer shadow. Use this
   for chronological activity rows and other history that should recede without looking deeply
   inset.

Do not mix those strengths arbitrarily. A shallow readout must remain visibly quieter than mounted
evidence and the decision plate. Light detents must never resemble deep wells, text inputs, or
disabled controls.

## Shared Header

The shared header contains, in order:

1. CLAWMARKS wordmark;
2. current page;
3. active expedition and leg;
4. active Focus and revision, when present;
5. running-search state, when present;
6. Guide button.

It uses one strong bottom rule, not a floating card. On narrow screens, expedition/leg and Focus
collapse into one labeled context control rather than disappearing without replacement. The Guide
button remains visible.

## Controls

### Primary actions

Primary actions use black fill with paper text. Sulfur appears as a bottom registration mark or
short underline. Their tactile edge and hard offset shadow distinguish them from flat data rows.
Large sulfur-filled call-to-action blocks are prohibited.

### Selected controls

A compact selected tab or step may use sulfur fill with black text. The selected state also uses
shape, weight, or `aria-current`; color is not the only cue.

### Workflow stepper

Orient, Scout, Explain, Act, and Learn form one compact stepper of light raised keys with real button
elements. The active stage becomes one black key with a sulfur hard shadow or registration edge.
One shared detail/action strip sits below the stepper. Five content cards or five repeated
descriptions are prohibited.

### Links and secondary actions

Text links use ink, weight, and an underline. Focus links may use a thicker sulfur underline.
Secondary buttons use a clear ink rule or black fill according to hierarchy. Controls never rely
on paper texture for their affordance.

### Focus and keyboard states

Interactive controls use a visible 3px sulfur or ink focus outline with sufficient offset. Hover,
focus, selected, disabled, working, and error states remain visually distinct.

## Evidence Treatments

### Map selection

A selected map region uses an ink boundary plus sulfur hatch or registration halo. It includes a
direct label such as `SELECTED REGION` and a member count. An unlabeled dashed ellipse is
prohibited.

### Coverage frontier

A frontier cell uses diagonal sulfur hatching, a strong ink border, and a visible `F` or text label.
The side explanation states that the cell is empty but adjacent to populated evidence.

### Images

Evidence images use consistent hard-edged mounts: a thin ink border, small paper margin, inner light
edge, and a 4px to 5px unblurred shadow. The mount communicates that the image is a bounded working
piece, not decoration. Avoid ornamental mats, rounded frames, and frame treatments on incidental
imagery. Use consistent cropping only in grids and preserve access to the full image. Focus members,
real anchors, and trial results receive text labels or patterned marks, not color-only borders.
Evidence images need meaningful `alt` text or an adjacent caption that names their evidence role.
Decorative texture uses empty alt text. Solution Map and Coverage provide an accessible list or
table equivalent for every selected point, region, frontier, and value exposed only through the
visual canvas.

### Data and metadata

Use aligned rows, rules, and mono labels before table-like cards. Keep units, score definitions, and
uncertainty close to their values. Charts include text summaries and do not depend on sulfur alone.

## Guide Surface

The Guide uses `--guide-surface` and `--guide-ink` as one continuous dark layer. Sulfur marks the
context receipt, assistant label, focus state, and active composer controls. Messages separate with
rules and spacing rather than chat bubbles.

Context receipts and composers appear recessed through crisp inner edges. Guide actions use the
same hard raised-control treatment as the paper workspace.

The desktop drawer casts one restrained left shadow. The mobile sheet uses rounded top corners and
a drag handle because those shapes communicate the sheet interaction; this exception does not
license rounded cards elsewhere.

## Page Applications

### Explore

Place the connected workflow stepper directly below the shared header. Follow with the current
Focus and Saved Observations as two explicit tabs. The Focus tab contains a compact identity block,
a shallow raised research-question readout, scope metadata, and Edit Focus. The question remains
sentence case and visually quieter than the evidence wall.

Place the five-image evidence wall across the full useful width. Each image uses the mounted working
piece treatment and a mono evidence-role caption. A real-art anchor may use a sulfur border or hard
shadow in addition to its text label. Use images as labeled evidence, not a decorative collage.

Below the evidence wall, place the chronological Focus activity on the left and Next Decision on the
right. Activity rows use light detents with no outer shadow. Next Decision uses the mounted working
piece treatment as one raised abstract plate, including a crisp inner light edge and hard black
shadow. Its readiness values remain ruled rows inside the plate. Sulfur marks the active action and
small registration details; it does not fill the plate.

Prohibit an oversized welcome hero, marketing copy, feature cards, deep activity wells, and broad
empty space that makes the tool resemble a SaaS homepage.

Without a selected Focus, show a compact ruled Focus ledger and direct evidence-creation actions.
Do not replace the missing work with a promotional empty state.

### Solution Map

Give the map most of the viewport. Place interpretation directly over or beside the relevant
region, with a labeled selection and one Create Focus action.

### Coverage

Pair the grid with one editorial explanation column. Use ruled evidence rows, not statistic cards.

### Compare

Let the two images dominate. Separate them with one clear `OR` axis and keep model readiness in one
thin progress row.

### Cockpit

Present the research brief, fixed generation settings, and existing evidence as one ruled recipe.
Place paid payload review in one full-width final strip.

### Runs

Lead with run outcome and three inline statistics. Show trajectory and event log as continuous
evidence, not a dashboard of tiles.

### Error and empty states

Keep errors and empty states within the same paper/ink system. Use a clear heading, concrete cause,
affected scope, and one recovery action. Data-integrity errors must remain visually stronger than
ordinary empty states.

## Motion and Texture

Paper texture must be visible enough to distinguish the surface from a flat gray fill. Use fine 1px
ruling, a second faint cross-grain, and broad low-contrast tonal variation. Texture remains below
text, rules, images, and controls; it must not reduce text contrast, shimmer during scrolling, or
create large paint effects. Raised surfaces inherit the same paper family rather than switching to
clean digital white.

Motion is limited to drawer/sheet transitions, progress updates, and direct manipulation. Honor
`prefers-reduced-motion` by removing nonessential transitions.

## Responsive Behavior

At 700px and below:

- the header preserves page, compact context, and Guide;
- editorial two-column layouts become one column;
- the workflow stepper scrolls horizontally and keeps each label readable;
- map annotations remain inside the viewport;
- Compare stacks images with a horizontal `OR` divider;
- Cockpit's recipe becomes one ruled sequence;
- payload actions become a full-width final row;
- Guide opens as a pull-up sheet no taller than the available viewport.

Mobile buttons, inputs, and icon controls provide at least a 44px by 44px touch target. Inline text
links remain exempt but use at least a 24px line box. Horizontal scrolling must show a visible
clipped edge or other cue that more content exists.

Drawers, sheets, lightboxes, and selection dialogs use named native dialog semantics or equivalent
`role="dialog"`, `aria-modal`, accessible name, focus trap, Escape behavior, and focus restoration.
Screen-reader order follows the visual evidence order rather than hidden layout columns.

## Non-Goals

- The system does not imitate torn-paper scrapbook decoration on every surface.
- The system does not use soft, blur-heavy neumorphism or literal replicas of physical controls.
- Sulfur is not a general brand fill or decorative accent.
- The redesign does not erase dense research data to create marketing-page whitespace.
- Cards, pills, shadows, and rounded corners are not default grouping tools.

## Acceptance Criteria

- Shared tokens, typography, header, controls, and Guide treatment apply across every live tool.
- Explore's workflow reads and operates as a connected stepper, not five cards.
- Explore reads as an active research desk, not a product or SaaS landing page.
- Explore uses the approved depth allocation: shallow raised question readout, mounted evidence
  images, shallow activity detents, and one raised Next Decision plate.
- Paper texture remains visibly present at desktop and 390px mobile widths without reducing
  legibility.
- Secondary normal text meets WCAG AA contrast on paper.
- Every selected map region and frontier has a direct non-color label.
- Primary actions remain black-led with restrained sulfur annotation.
- Raised and recessed states use the same crisp abstract-skeuomorphic depth grammar across pages.
- No production page fetches fonts from an external runtime service.
- Keyboard focus, reduced motion, 200% zoom, and 390px mobile layouts remain usable.
- Screen-reader checks cover the shared header, workflow stepper, map and Coverage equivalents,
  evidence images, image detail view, active-leg dialog, and Guide.
- Playwright live checks cover Explore, Map, Coverage, Compare, Cockpit, Runs, one empty state, one
  integrity error, and desktop/mobile Guide states before release.
