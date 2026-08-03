# Persona: Jordan — blind, screen-reader-only

- Task ID: `oc_mrr6eqqd_b320320d`
- Model: `cheapestinference/kimi-k2.7`
- Character: fully blind, evaluates via accessibility-tree snapshot as ground truth (Tab/Shift+Tab/Enter navigation)

## Report

I'm Jordan. I use a screen reader, so I don't look at the screen at all. I navigate by headings, landmarks, and the Tab key. Here is what I found on the CLAWMARKS homepage and a couple of related pages.

## What I heard

**Homepage structure**

The page title is "CLAWMARKS uncanny scan." The first Tab stop is a link named "CLAWMARKS," then buttons "trent_v3_epoch4/freeform1" and "Guide," then a link "session status," then a combobox labeled "jump to another page."

Headings: I found exactly one heading, level 1, "CLAWMARKS uncanny scan." There are no h2, h3, or lower headings, so the whole page is a flat outline.

Landmarks: Only a `banner` region exists. The rest of the page is inside generic regions, not a `main` or `navigation` landmark.

**Filters**

Tabbing through the filter bar I heard:
- "Sort" as plain text, then an unlabeled combobox.
- "Type" combobox.
- "Category" with a button "More information about MAP-Elites cell," then a combobox.
- "Prompt" combobox.
- Spinbutton "Similarity to real art >=" and spinbutton "Similarity to real art <= More information about Similarity to real art."
- "Search" textbox.
- Checkbox "picked only More information."
- Checkbox "favorited only More information."

Most controls are labeled, but the Sort combobox is only preceded by loose text.

**Image grid**

When I Tabbed past the filters, focus jumped straight to the body. The thumbnails are not in the Tab order at all. Looking at the accessibility tree, each thumbnail is a generic element with `cursor=pointer` and a truncated prompt string like "conflict_pure_abstract_brushed-pa." No image role, no alt text, no accessible name that says what the picture is, and no indication that clicking it opens anything. With a virtual cursor I would hear "generic, conflict_pure_abstract_brushed-pa," which tells me the prompt name but not that it is an image.

**Info popover**

I activated the button "More information about How new or different." The button gained an `expanded` state, but focus stayed on the button. A new generic text block appeared at the bottom of the tree: "Novelty measures how different an image is from everything the search has already explored..." There is no `dialog` role, no `aria-live` region, and focus does not move into the explanation. I would have to know to hunt down the page for the new text.

**Billable action**

On the "Run or monitor a search" page I found a button named "Back up and launch." Its accessible name does not mention money. The tree shows a separate adjacent text node "Spends money," but that text is not programmatically associated with the button, so when I Tab to it I only hear "Back up and launch." I would not know it costs money unless I read the surrounding page carefully.

**Other pages I checked**

- "Best images by area" (Elite archive): Each cell is described with text like "faithfulness=0.2738 novelty=0.7243 count=8 in cell" and a button "view all 8 in this cell." That's better than the homepage. However, the paragraph mentions gold-bordered cells are favorited winners and blue-bordered cells are predicted picks. Those border colors are visual-only cues; the cells themselves are not marked as "favorited" or "predicted" in their accessible names.
- "Choose between two images": Buttons are "Choose image A" and "Choose image B." The actual images are not described, so I can vote without knowing what either one looks like.

## screen-reader blockers

- The image grid thumbnails are generic clickable elements with no image role, no alt text, and no meaningful accessible name; they are also not in the Tab order, so they are essentially unreachable and unidentifiable.
- The homepage has only one heading level, so there is no structural outline to navigate by.
- The homepage lacks a `main` landmark and other useful landmarks; almost everything is inside generic regions.
- The Sort combobox is unlabeled (only a loose "Sort" text label next to it).
- The info popover does not move focus into the explanation, has no dialog role, and has no live-region announcement, so a screen reader user may not know it opened.
- The "Back up and launch" button's accessible name does not indicate that it spends money; the "Spends money" text is adjacent but not programmatically associated with the button.
- The comparison page asks the user to choose between Image A and Image B without describing the images.
- Visual-only cues on the elite archive page (gold/blue cell borders) are explained in a paragraph but not marked on individual cells, so I cannot tell which cell is which while navigating.

## what worked well for a screen-reader user

- Page titles are descriptive ("CLAWMARKS uncanny scan," "CLAWMARKS search runs," etc.).
- The `banner` landmark exists and contains the primary navigation.
- The "jump to another page" combobox is well labeled and lets me move between tools.
- Most form controls have labels, especially Type, Category, Prompt, and the similarity spinbuttons.
- Info buttons generally have useful accessible names like "More information about How new or different" rather than just "i."
- The status text "50 / 50 images | 0 picked | 0 favorited" is plain text and readable.
- The elite archive page includes textual metrics (faithfulness, novelty, count, bin ranges) so the image data is partially available as text.
- The "Choose image A/B" buttons themselves are clearly labeled, even though the images they represent are not.

I did not activate any billable controls.

Status: DONE
