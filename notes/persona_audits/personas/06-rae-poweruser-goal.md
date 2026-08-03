# Persona: Rae — goal-directed power user

- Task ID: `oc_mrr5k6h9_783160e4`
- Model: `opencode/hy3-free`
- Viewport: 1440x900
- Character: former data engineer, came in with two concrete goals, no patience for vague nav

## Report

## Rae's walkthrough notes

I came in cold with two concrete asks: (A) training-readiness for the preference model (comparisons submitted vs needed) and (B) the single highest-scoring / most-favorited image in the active leg. Both ended up answerable, but B was a mess of blurred concepts and I had to read three separate info popups to disentangle them.

For A: dead easy. The dropdown literally has "Check taste-model readiness," and that page states up front "Comparisons: 0 usable of 6 total (needs 50)." One click, unambiguous number. Good.

For B: this is where the tool fumbled me. There is no "highest score" or "most favorited" sort, and no single page that names the top image. The browse default sorts by novelty, not score. I visited "Best images by area" expecting a top-ranked image but it's the MAP-Elites archive (one representative per grid cell, each labeled "highest novelty" in that cell, not globally highest anything). "See predicted favorites" is dead because the model isn't trained (needs 50 comparisons, has 0). The only count of favorites anywhere is the footer "0 picked | 0 favorited" on the browse page. So the honest answer to "most favorited in this leg" is **zero favorited, zero picked** — there is no standout favorite to name. The concepts of "favorited" (bookmark for a writeup, no search effect), "picked" (human-flagged winner in the lightbox that feeds the next generation), "best" (highest novelty per MAP-Elites cell), and "highest novelty" are four different things, and the UI blurs them: the archive page calls everything "highest novelty," the browse footer says "favorited," the lightbox says "favorite," and none of them is an aesthetic "best" score. There is no composite score field anywhere; only faithfulness and novelty are shown, per image, in the lightbox.

No command palette or global search exists. Navigation is 100% dropdown-menu-driven (the "jump to another page" select) plus the top-of-browse filters. For a goal-directed user who knows the label, the dropdown is fine; the bottleneck is that the labels don't map cleanly to user intent ("Best images by area" ≠ "best image," and there's nothing called "top image" or "favorites ranking").

One number I had to infer rather than read: whether any image is actually favorited/picked. The only statement is the browse footer counter "0 picked | 0 favorited"; nothing on the detail pages or archive says it explicitly, so I'm trusting the footer rather than a per-page confirmation.

## path taken for Goal A
- Landed on Browse (default page, sorted by novelty).
- Scanned the "jump to another page" dropdown; saw "Check taste-model readiness" — obvious label match.
- Selected it. Page "Preference classifier status" stated: "Comparisons: 0 usable of 6 total (needs 50)." Goal met in one hop. No backtracking.

## path taken for Goal B
- From Browse, tried the dropdown "Best images by area" (hoping for a ranked top image).
- Got the MAP-Elites "Elite archive" — 12 cells, each tagged "highest novelty" for that cell, NOT a single global best. Dead end for "single highest."
- Tried "See predicted favorites" in the dropdown.
- Page said no trained model exists (needs 50 comparisons). Dead end.
- Back on Browse, read footer: "50 / 50 images | 0 picked | 0 favorited" — so no favorites exist.
- Clicked the "favorited only" info (i) button: "Favorited images are bookmarked for reference... have no effect on the search."
- Clicked the "picked only" info (i) button: "Picked images are ones a human has flagged as winners in the lightbox... next generation prefers picked images."
- Opened an image lightbox to check for a score/favorite count: shows faithfulness & novelty numbers and a ♡ favorite button, but no composite "score" and no "most favorited" ranking.
- Conclusion: zero favorites/picks in this leg; no single top image is defined by the UI.

## what would make this faster for a goal-directed user
- Add a sort option "Favorited first" / "Most picked" / "Highest score" to Browse, not just novelty/similarity/generation/prompt.
- Give "Best images by area" a clearer name (e.g. "MAP-Elites archive (one per cell)"); the "Best" word implies a ranked winner it doesn't deliver.
- Surface a single line on a results page like "Top image: <name> (faithfulness x, novelty y, N favorites)" instead of forcing users to open the lightbox per image.
- Add a global search / command palette (Ctrl-K) so power users can jump straight to "favorites" or "top image" without scanning a 14-item dropdown.
- Distinguish the four concepts ("favorited" vs "picked" vs "best/novelty" vs "predicted favorite") in one short glossary on the browse page, since they currently collide in labels.

Status: DONE
