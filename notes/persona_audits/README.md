# CLAWMARKS persona audits

Two waves of simulated-persona usability, security, and accessibility walkthroughs of the
CLAWMARKS curation app (`curation_server.py`), run against a live tailnet instance. Every
walkthrough was read-only: no persona clicked a real billable action (generate, launch, retrain).

## What this was

Each "persona" is a role-played user brief (a mobile user in a hurry, a screen-reader user, an
adversarial security tester, and so on) dispatched as an independent task to an LLM that browsed
the live app and reported back what it found. Running many different personas independently
surfaces problems no single reviewer would catch: a keyboard-only walkthrough finds different bugs
than a colorblindness audit or a penetration test, even against the exact same pages.

**Dispatch mechanism:** every persona ran through `taskferry`, this project's tool for sending a
task to an OpenCode-hosted model and waiting for it to finish (see the `using-taskferry` skill).
Model choice for each persona followed the `picking-a-free-model` skill, which ranks free-tier
OpenCode models by capability and reliability; a few personas needed a paid model
(`cheapestinference/glm-5.2 --variant max`) when the free tier's reasoning wasn't strong enough for
an adversarial angle. There is no dedicated "persona-testing" skill; this is taskferry dispatch
applied to a batch of role-play briefs, one per persona.

## Directory map

- **`personas/`** — Wave 1 (2026-07-19): 19 personas covering mobile, accessibility, ESL,
  research-efficiency, power-user, stakeholder, ADHD, colorblindness, plain-language, and
  adversarial angles, three of them re-run on a vision-capable model after the text-only model
  couldn't judge actual pixels. `personas/README.md` indexes all 19 with the model each one used
  and the cross-cutting findings shared by 3+ personas. `personas/ISSUES.md` and
  `personas/issue_numbers.json` consolidate every bug from both waves into the list that was
  actually filed to GitHub.
- **`reports/`** — Standalone Wave 2 reports (2026-07-19) that didn't fit the Wave 1 persona
  template: Nadia's penetration test, Oren's structural/error-state audit, and Grace's blind
  art-judgment comparison (the one that corroborates Viktor's finding that `novelty` and
  `faithfulness` don't track perceived quality). Femi's reproducibility audit and Diego's mobile
  sweep don't have standalone reports; their findings are folded directly into
  `personas/ISSUES.md`, and Diego's evidence is the mobile screenshot set in `screenshots/`.
- **`captures/`** — Raw Playwright accessibility-tree snapshots (not screenshots) that some
  personas captured as supporting evidence for DOM-structure claims.
- **`screenshots/`** — Every visual capture behind the audits: Diego's numbered mobile-viewport
  sweep (`01` through `12`, plus `b`/`c` scroll variants), the vision-round re-runs' captures
  (`*_375x667.png`), and a handful of desktop reference shots used by early personas.

## Outcome

Every bug from both waves was filed as a GitHub issue, **#58 through #89** (32 issues: 7 P0,
14 P1, 11 P2). None had a fix started as of 2026-07-20. See the lab notebook's 2026-07-19 entries
for the full narrative, including the headline research finding for the whitepaper: given real
pixels, a human-plausible judge's pick for the single most visually striking image scored mid-pack
on both `novelty` and `faithfulness`, so neither metric is a stand-in for aesthetic quality.

## Provenance note

This audit ran in a git worktree (`worktree-ux-persona-tests`) that was already merged into `main`
by the time this folder was created; the write-ups and screenshots themselves were never
committed until this reorganization. The screenshots are tracked despite the repo's blanket
`*.png`/`*.jpg` ignore rule (see `.gitignore`'s exception for this path) because they are audit
evidence, not generation output, and are small enough (under 10 MB total) to track directly.
