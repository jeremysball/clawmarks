# Persona: Dana — keyboard-only, low-vision, 200% zoom

- Task ID: `oc_mrr5z6fb_de922180` (resumed from crashed session `oc_mrr5hwo3_2bc33670` via `--session-id`)
- Model: `opencode/mimo-v2.5-free`
- Viewport: 1440x900
- Character: keyboard-only navigator, low vision, uses browser zoom

## Report

## Dana's Usability Walkthrough Report

Hi, I'm Dana. I just spent about 15 minutes tabbing through CLAWMARKS. Here's what it was like for me.

### First impressions

The page loaded and I could see the header bar with the CLAWMARKS link, some buttons, and a dropdown. The navigation bar is straightforward. The heading says "CLAWMARKS uncanny scan" with a description underneath. There are filter controls (Sort, Type, Category, Prompt, Similarity, Search, picked/favorited checkboxes) and then a grid of artwork thumbnails below.

The background is a muted greenish-gray which gives decent contrast for the text. The overall layout at normal zoom looks organized.

### Tabbing through the homepage

I started Tabbing from the very top. The focus order flows like this:

1. CLAWMARKS link
2. The expedition name button ("trent_v3_epoch4/freeform1")
3. Guide button
4. Session Status link
5. The "jump to another page" dropdown
6. Then into the filter controls: Sort "i" button, Sort combobox, Type combobox, Category "i" button, Category combobox, Prompt combobox, Similarity spinbuttons, Similarity "i" button, Search textbox, picked checkbox, picked "i" button, favorited checkbox, favorited "i" button

The focus indicator is a yellow outline (`3px solid` with `3px offset`). On the navigation links it was clearly visible against the background. The Session Status link showed a bright yellow outline I could easily spot even with my magnification.

### The big problem: image thumbnails are unreachable by keyboard

After tabbing through all the filter controls, I hit the end of the tab order and focus dropped to the body element. **The entire grid of 50 image thumbnails is completely unreachable by keyboard.** Each thumbnail is a plain `div` with a click handler and no `tabindex`, no `role`, no `aria-label`, and the `<img>` elements inside have no `alt` text. I cannot select, view, pick, or favorite any image without a mouse. This is the single biggest accessibility barrier in the app. For someone like me who can't use a mouse easily, the entire core purpose of the app is locked away.

### Info popover test

I clicked the "i" button next to Sort. A popover appeared with a clear explanation of what "novelty" means. The popover has a dark background with light text, good contrast. I pressed Escape and the popover closed, and focus returned to the "i" button that opened it. That part works well.

### Compare page ("Choose between two images")

I navigated to the compare page via the dropdown. This page is much better for keyboard access. The two image panes are actual focusable elements with `role="button"` and `aria-label="Choose image A"` / `"Choose image B"`. The focus indicator is a thick yellow border around the selected image, very clear even at my zoom level. Each image also has a magnifier button labeled "Inspect image A at full resolution" that's in the tab order. The instructions say I can press arrow keys to choose, which is good. This page feels usable.

### Generation cockpit page

I visited the Generation cockpit. It has a "Send draft to queue" button which I believe triggers GPU compute (billable). The button is styled as a dark rectangle with bold white text. It has **no warning label, no icon, no special border pattern, or any other visual cue** beyond its text label that it spends money. The text "Send draft to queue" doesn't mention cost. For a low-vision user who might activate it accidentally, there's nothing that screams "this costs money" beyond reading the button text carefully.

### Combobox labeling

Several filter comboboxes lack proper accessible names:
- The **Sort** combobox has no `aria-label` at all
- The **Category** combobox has no `aria-label`
- The **Prompt** combobox has no `aria-label`

Only the **Type** combobox and the **jump to another page** combobox have proper `aria-label` attributes. When I Tab to the Sort combobox, a screen reader would have no idea what it controls.

### Thumbnail color coding

The image thumbnails use colored inset shadows to indicate type: orange/amber for "conflict" images and green for "style" images. This is **color-only** differentiation. There's no icon, text badge, or pattern to distinguish them for someone who can't perceive color differences.

### Some "i" buttons have vague labels

Two of the info buttons just say "More information" with no context about *what* they're about. The first three are well-labeled ("More information about How new or different", "More information about MAP-Elites cell", "More information about Similarity to real art"), but the last two on the picked/favorited checkboxes are generic.

### 200% zoom

At my usual zoom level, the filter bar wraps a bit but remains functional. The image thumbnails grid stays in a reasonable layout. I didn't encounter horizontal scrolling or major text clipping on the main browse page. The compare page's side-by-side layout fits within the viewport. The popover text was readable at my zoom.

---

### keyboard/focus problems

- **Image grid thumbnails (browse page) are completely unreachable by keyboard.** No `tabindex`, no `role`, no `aria-label`. Focus jumps from the last filter control straight to `<body>`. The entire core curation workflow (viewing, picking, favoriting images) requires a mouse.
- **Image `<img>` elements inside thumbnails have no `alt` text.** Even if thumbnails were made focusable, a screen reader would have nothing to announce.
- **Sort, Category, and Prompt comboboxes have no `aria-label`** or associated `<label>` element. Only Type and jump-to comboboxes are properly labeled.
- **Two info buttons have the generic label "More information"** without specifying what they explain (the ones next to "picked only" and "favorited only" checkboxes).
- **Billable "Send draft to queue" button has no warning or cost indicator** beyond its text. No icon, no special border, no aria description mentioning cost. Activating it by accident could trigger GPU billing.
- **Thumbnail type indicators (conflict vs style) use color alone** (orange vs green inset shadow). No icon or text badge distinguishes them for color-blind users.
- The "i" info buttons are very small (`font-size: 10.5px`) and could be hard to target visually, though they are in the tab order.

### what worked well for keyboard/low-vision use

- **Focus indicator is clearly visible** on navigation links and controls: a yellow 3px solid outline with 3px offset, high contrast against the page background.
- **Info "i" popovers open on click and close on Escape**, with focus returning to the button that opened them. Proper keyboard pattern.
- **Compare page image panes are fully keyboard accessible** with `role="button"`, descriptive `aria-label`s, and a thick yellow focus border. The magnifier buttons are also properly labeled and in the tab order.
- **Filter controls are logically ordered** in the tab flow: nav bar, then Sort, Type, Category, Prompt, Similarity range, Search, checkboxes.
- **The "jump to another page" dropdown** provides a keyboard-accessible way to navigate between all app sections without needing to find specific links.
- **Text contrast is generally good** throughout: dark text on light backgrounds, light text on dark buttons.
- **The compare page's arrow-key instructions** are documented in visible text near the controls.

Status: DONE
