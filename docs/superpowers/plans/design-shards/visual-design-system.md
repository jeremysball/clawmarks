# Visual design system consistency (shard 7)

Angle: typography, color palette, spacing, and component (button, badge) drift across the curation server's ~14 routes, plus dark-mode/low-light suitability for allnight sessions.

## Architecture as it stands

There already is a shared module: `src/clawmarks/shared_ui.py`. It centralizes the lightbox JS (`_LIGHTBOX_JS`), the nav bar HTML (`nav_bar_html`), `TOPNAV_CSS`, `INFOTIP_CSS`, `MOBILE_BASE_CSS`, and the `info_btn`/`json_script` helpers. Every `build/*.py` `render_html()` pulls from it, and script tags (`lightbox.js`, `infotip.js`) are included consistently across all 12 pages that need them.

What is NOT shared is the per-page base design system: the `:root` CSS variables, the body font, and the button/badge classes. Each `render_html()` re-declares its own. The real situation is "shared chrome, divergent base," not "zero shared styles."

## What I observed (grounded)

### Color palette: the dark family is mostly in lockstep
The six core dark tokens `--bg:#0b0b0d; --panel:#16161a; --border:#2a2a30; --text:#eaeaee; --text-dim:#9a9aa4` appear verbatim, copy-pasted ~14 times: `map_view.py:63`, `coverage_map.py:172`, `elite_archive.py:142`, `preference_rank.py:73`, `preference_status.py:122`, `redundancy_view.py:83`, `runs_page.py:26`, `compare_page.py:36`, `scan_gallery.py:112`, `seed_browser.py:35`, `explore_hub.py:59`, `novelty_decay.py:89`, plus `curation_server.py:990` and `:1020`.

### Color palette: the drift within that family
- `--accent` (`#7c9eff`) is declared in scan/explore/runs/seed, but omitted in map/coverage/preference_rank/preference_status/redundancy/elite. Those pages inline `#7c9eff` literally instead (`a.navlink { color:#7c9eff }` at `map_view.py:70`, `novelty_decay.py:96`, `lineage_view.py:46`).
- `--pick` is semantically inverted: `#f5c542` (gold, "human picked") in `scan_gallery.py:114`, `elite_archive.py:143`, `map_view.py:64`, but `#7c9eff` (blue, the accent) in `compare_page.py:37`. Same variable name, opposite hue and opposite meaning. A reader who learned `--pick` as gold on scan will be misled on compare.
- "Good = green" is named `--up` in `runs_page.py:27` and `novelty_decay.py:90` but `--style` in `scan_gallery.py:114`. Same `#5ec98a`, two names.
- Three distinct second-surface greys for the same role: `#1f1f24` (`runs_page.py:38,45` selectors/stats), `#24242a` (`preference_status.py:137` `.secondary`), and `#1d1d22` (`scan`/`seed`'s `--panel-2`). Plus a blue-submit literal `#2a4a7c` repeated in `seed_browser.py:54` and the shared lightbox `shared_ui.py:281`.

### Typography
- Body font: `-apple-system,sans-serif` (short form) in ~9 pages; the full `-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif` only in `scan_gallery.py:120` and `seed_browser.py:41`. Same stack, two spellings.
- Body outer padding: `24px` is the norm; `explore_hub.py:60` uses `32px`, `map_view.py:66` uses `20px`, scan/seed use `0` with an internal `#bar`.

### Components: buttons
No shared `.btn` class. At least four primary-button recipes coexist:
1. Accent-filled: `background:var(--accent); color:#0b0b0d; font-weight:600` (`curation_server.py:1032` status picker, `runs_page.py:40` `button.primary`).
2. Surface-border: `background:#1f1f24; color:var(--text); border:1px solid var(--border)` (`runs_page.py:38` default button).
3. Blue-literal submit: `#2a4a7c` (`seed_browser.py:54`, shared lightbox).
4. Panel ghost: `button.playbtn { background:var(--panel) }` (`map_view.py:87`), `.secondary { background:#24242a }` (`preference_status.py:137`), `.viewall { background:var(--panel-2) }` (`elite_archive.py:163`).

### Dark-mode / low-light suitability
The 11 dark pages are genuinely night-friendly: explicit `color-scheme: dark`, `#0b0b0d` bg, `#eaeaee` text, high contrast. Two caveats:
- `lineage_view.py:42` and `novelty_decay.py:58` placeholder branches set `color-scheme: dark` but skip the `--bg/--text` vars and hardcode `background:#0b0b0d; color:#eaeaee` on `body`, so they cannot inherit a future token edit.
- **Cockpit is the only bright page.** `cockpit.py:102` declares `color-scheme:light` with `--paper:#F5F2E9` cream. Its docstring calls this a deliberate paper-craft direction. For an allnight tool, full-screen cream is a glare hit, and cockpit is where you draft prompts (a long-dwell task). It also overrides the shared nav: `.topnav.cockpit-topnav { background:...paper... }` at `cockpit.py:126`, because the dark nav bar (`TOPNAV_CSS` assumes `--bg`/`--panel`) clashes with a light page. That override proves the shared nav is dark-only by assumption; any second light page would need the same hack. Opening the dark lightbox from cockpit also flashes a dark scrim over a light page.

## Concrete problems

1. **Cockpit night glare.** Highest real user-impact: the page you spend the longest on is the only bright one, and sessions run late.
2. **`--pick` semantic inversion** across scan vs compare. A genuine trap, not cosmetic: same token, two colors, two meanings.
3. **No shared `:root` token block or button classes.** Fixing any single color (e.g. nudging `--bg`) means editing 14 places. The values are already identical across most pages, so consolidation is risk-free.
4. **Inline `#7c9eff` literals** on pages that forgot to declare `--accent`. Breaks the moment someone redefines the accent token.
5. **Three second-surface greys** for the same visual role.
6. **Placeholder branches** in lineage/novelty bypass the CSS vars entirely, so they drift silently.

## Recommendations (ranked by impact)

1. **Add a `DARK_TOKENS` constant + a `.btn` trio to `shared_ui.py`.** Define the canonical `:root{ color-scheme:dark; --bg:#0b0b0d; --panel:#16161a; --panel-2:#1d1d22; --border:#2a2a30; --text:#eaeaee; --text-dim:#9a9aa4; --text-faint:#6a6a74; --accent:#7c9eff; --pick:#f5c542; --up:#5ec98a; --down:#e0605e; }` block once, plus `.btn`/`.btn--primary`/`.btn--secondary` classes. Have every dark page inject `{DARK_TOKENS}` and use those classes instead of its hand-rolled copy. Mechanical find-and-replace, not a redesign: the values are already identical across 14 sites, so it changes nothing visually and gives one edit point. ~30 min.

2. **Fix `--pick` in `compare_page.py:37`.** Rename it to `--accent`, which is what it actually is there. Restores `--pick = gold (human-picked)` as a project-wide invariant. 2 min.

3. **Give cockpit a dark-mode override.** Repo precedent exists: `probe_report.py` does dual-theme via `@media (prefers-color-scheme: dark)` swapping its tokens (lines 167-175). Add the same block to `cockpit.py` below line 115, swapping `--paper`/`--ink` for dark sheet/ink equivalents, and drop the `.cockpit-topnav` hack once the nav works on both. Lets the allnight prompt-drafting page stop glaring. ~20 min.

4. **Replace inline `#7c9eff` literals** in map/novelty/lineage nav links with `var(--accent)`. ~5 min, included in step 1's pass.

5. **Collapse the three surface greys** (`#1f1f24`, `#24242a`, `#1d1d22`) to the shared `--panel-2`. ~10 min.

None of this needs a framework or a rewrite. The shared helper already exists; extending it with one token block + a button class trio is the minimum viable fix and stops the drift at its source without touching any page's layout or behavior.