# ADR 0001: Expedition/leg config lives under `$XDG_STATE_HOME`, not the git repo

**Status:** Accepted
**Date:** 2026-07-16

## Context

`config.EXPEDITIONS_DIR` originally pointed at `ROOT / "expeditions"`, a git-tracked directory
holding each expedition's small `expedition.json` and `legs/<leg>.json` config files. This was a
deliberate split from `config.leg_dir()`, which points at
`$XDG_STATE_HOME/clawmarks/expeditions/<expedition>/<leg>/` and holds the real generation output
(images, manifests, embeddings). The intent, documented in `CLAUDE.md` and asserted by
`test_config.py::test_expeditions_dir_is_repo_relative`, was that small reviewable config belongs
in git while heavy regenerable output stays outside the repo.

In practice this split caused a real problem. An expedition (`trent_v3_epoch4`) accumulated 50
real generated images and a full `scored_manifest.json` under `$XDG_STATE_HOME`, entirely through
normal use of the curation server, but its `expedition.json` was never created, because nothing
in the actual workflow (the curation server's "create expedition" UI) writes to a git-tracked
path. The server correctly refused to recognize the expedition (`ValueError: unknown expedition
'trent_v3_epoch4'`) until its config was reconstructed by hand from the manifest data, an
avoidable manual-recovery step. Two directory trees sharing the same `expeditions/<name>/` shape
for related but different content (config vs. output) was also a standing source of confusion
during debugging (see `notes/lab_notebook.md`, 2026-07-15 entry).

## Decision

`config.EXPEDITIONS_DIR` now resolves to `STATE_DIR / "expeditions"`, the same root
`config.leg_dir()` already uses. An expedition's config
(`EXPEDITIONS_DIR / expedition / "expedition.json"`,
`EXPEDITIONS_DIR / expedition / "legs" / "<leg>.json"`) and its per-leg generation output
(`EXPEDITIONS_DIR / expedition / "<leg>"`) now live side by side under one directory per
expedition, distinguished by the `legs/` subdirectory (config) versus a bare `<leg>/`
subdirectory (output). The repo's `expeditions/` directory is removed and gitignored; creating or
editing an expedition or leg is now a runtime action against `$XDG_STATE_HOME`, not a git commit.

## Consequences

- An expedition created through the curation server's UI (`_create_expedition`, `_create_leg`)
  now needs no follow-up commit to become usable; the class of bug that motivated this ADR
  (config silently missing for an expedition that has real generation output) cannot recur.
- Expedition/leg config is no longer reviewable via `git log`/`git diff`, and is not backed up by
  the repo's own version control. It is covered by the same `$XDG_STATE_HOME/clawmarks/` backup
  discipline `CLAUDE.md`'s data-integrity section already mandates for generation output, but that
  discipline now has to extend to config too, not just images and manifests.
  A fresh clone of the repo starts with zero expeditions defined; onboarding a new checkout (or a
  new machine) requires either copying `$XDG_STATE_HOME/clawmarks/expeditions/` across or
  recreating expeditions through the UI, a step that used to be implicit (clone the repo, get the
  configs for free).
  This project has exactly one active researcher and one working checkout at a time, so the lost
  git-history/multi-machine-onboarding value costs little in practice; it would weigh more heavily
  on a team project or one with several checkouts kept in sync.

## Alternatives considered

- **Keep config in git, fix the workflow instead** (make `_create_expedition`/`_create_leg` write
  into the repo and require a commit as part of expedition creation). Rejected: this would still
  leave the state-dir generation output and the git-tracked config able to drift apart (an
  expedition's output could be deleted or a repo could be re-cloned at an older commit), and it
  adds a git-commit step to routine curation-server usage that the rest of the state-dir workflow
  doesn't require.
- **Leave the split as-is, treat `trent_v3_epoch4` as a one-off** that just needed its config
  reconstructed and committed. Rejected: the split was the actual root cause, not the specific
  missing file; leaving it in place means the same failure mode recurs for the next expedition
  created without a matching manual commit.

## Revisit this decision if

This project ever needs config synced across multiple machines/checkouts, or needs expedition
config under code review before it takes effect. At that point the config-in-git approach (with
the workflow fix from "Alternatives considered") becomes worth the onboarding cost this ADR
accepts today.
