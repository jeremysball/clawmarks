# Research Workspace Navigation Design

## Goal

Turn the existing curation tools into one research workspace. A researcher starts with a visual
question, gathers evidence, runs one bounded trial, and returns the results to that question.

This specification defines the site-level workflow and information architecture. The Focus data
model, OpenCode Guide, and visual system have separate specifications.

## Research Loop

The workspace uses five stages:

1. **Orient:** choose an expedition and leg, state the visual question, and resume or create a
   Focus.
2. **Scout:** locate a cluster, real-art anchor, or reachable frontier on Solution Map or Coverage.
3. **Explain:** inspect images, prompts, preferences, redundancy, novelty decay, and lineage. Record
   the strongest explanation and at least one plausible alternative.
4. **Act:** turn one Focus revision into a bounded trial in Cockpit. Confirm the changed variable,
   constants, expected move, evidence against, exact payload, and spend cap.
5. **Learn:** review the generated images, compare them with the Focus evidence, record the human
   judgment, and revise or close the Focus.

These stages organize navigation. They do not claim that research proceeds in a strict line. A
researcher can return from Explain to Scout or from Learn to Explain without losing the Focus.

## Explore Page

`GET /` and `GET /explore.html` render the Explore page described by
`2026-07-16-explore-root-status-page-design.md`. Explore contains:

- the active expedition and leg;
- the active visual question, when a Focus is open;
- a compact five-stage workflow control;
- Focus and Saved Observations tabs;
- the active Focus's evidence wall, next decision, and activity ledger;
- direct access to the full tool index.

Explore is an active research desk, not a landing page. It has no oversized welcome headline,
decorative collage, product pitch, or row of feature cards. The workflow control sits directly below
the shared header. Focus and Saved Observations form two tabs below the shared workflow explanation.
The Focus tab presents identity and revision beside a compact research-question readout with scope,
member count, real-anchor count, and last edit. A full-width evidence wall follows. The lower surface
pairs a dense chronological activity ledger with a narrower Next Decision column. The Sulfur Proof
design-system specification defines their approved depth hierarchy.

Without a Focus query, Explore shows a ruled list of open Foci for the explicit expedition and leg,
plus Create from Map and Create from Coverage actions. It does not silently choose the most recent
Focus. Resuming one navigates to a URL that names the full scope and Focus ID.

Saved Observations is not another mutable record type. It is a ruled index of the current scope's
Focus records that shows each Focus label, verbatim observation, status, revision, and last edit.
Selecting one opens its explicit Focus URL. The tab may include archived Foci but never silently
changes the active Focus.

The five-image evidence wall uses deterministic stored order: up to four generated members, then
the first real anchor. If no real anchor exists, it fills the remaining positions with generated
members up to five. Missing files keep their position and render a labeled missing-evidence mount;
the UI never substitutes a current nearest neighbor.

The activity ledger is a read-only merge of existing authoritative records: Focus creation and
current revision timestamps, Guide messages, trials, paid-launch state changes, results, and human
evaluation. It sorts by timestamp and stable record ID. The initial version does not add a second
audit-log store or pretend overwritten intermediate Focus edits remain available.

Explore derives the active stage and Next Decision from persisted readiness in this order:

1. no Focus: Orient, with Create from Map and Create from Coverage;
2. incomplete six-part test contract: Explain, with Edit Focus;
3. no confirmed, active, or completed trial for the current Focus revision: Act, with Open Cockpit;
4. a confirmed, launching, or running trial: Act, with Open Trial or Runs;
5. a completed or failed trial without human evaluation: Learn, with Review Result;
6. an evaluated latest trial: Learn, with Revise Focus or Archive Focus.

The server returns the readiness facts. Client-side workflow-button exploration may show another
stage's explanation, but it cannot change the persisted or initially active stage.

### Workflow control

Orient, Scout, Explain, Act, and Learn appear as one connected stepper or tab bar. They must not
appear as five cards.

- Each stage is a native `<button>` with a visible hover state, keyboard focus state, and one clear
  active state.
- Selecting a stage updates one shared explanation and one shared row of relevant actions below
  the bar. It does not create five repeated description panels.
- The selected stage uses `aria-current="step"`. The explanatory region uses `aria-live="polite"`.
- The control scrolls horizontally at narrow widths instead of shrinking labels below a readable
  size.
- Selecting a stage does not mark it complete. Completion claims require recorded evidence, a
  trial, or a result judgment.

The default actions for each stage preserve the current Focus query:

| Stage | Primary destination | Other destinations |
| --- | --- | --- |
| Orient | `/status.html` | resume Focus, create Focus |
| Scout | `/map.html` | `/coverage.html`, `/archive.html` |
| Explain | `/redundancy.html` | `/novelty_decay.html`, `/lineage.html`, `/compare.html`, Guide |
| Act | Focus-scoped `/cockpit.html` | return to Focus evidence |
| Learn | `/runs.html` or completed trial | `/scan.html`, `/coverage.html`, Focus debrief |

If Act has no active Focus, its shared action area explains that a trial needs a question and
evidence scope, then offers Create Focus. It must not silently create a freeform trial.

## Tool Responsibilities

### Solution Map

Solution Map scouts visual neighborhoods. A lasso or selected group can create a Focus. Member
tags and high-dimensional image neighbors define the durable selection; the 2D projection only
helps the researcher see and replay it.

Pointer drag draws a labeled polygon and selects generated points inside it. A drag shorter than 6px
remains the existing single-point inspection. The polygon stores normalized canvas coordinates only
as `projection_hint`; selected generated tags are authoritative. A synchronized accessible list
provides checkboxes for adding or removing the same members without a pointer. Create Focus remains
disabled until at least one valid generated member is selected.

### Coverage

Coverage scouts empty cells adjacent to populated cells. Creating a frontier Focus records the
cell's faithfulness and novelty ranges, adjacent member tags, and nearest real-art anchors.
Coverage describes a frontier as plausible, not promising or superior.

Each frontier cell is a native button mirrored by an accessible table row. Selecting it exposes its
exact faithfulness and novelty ranges, adjacent member count, and a Create Focus action. Axis edge
ranges use the declared metric domains (`[-1, 1]` and `[0, 2]`), not display defaults of zero and one.
Quantile binning may repeat an edge when a leg contains few records or many equal scores. Coverage
marks a cell actionable only when all four bounds are finite and both ranges are strictly
increasing. A zero-width cell can remain visible as a density artifact, but it is never a frontier,
button, or Create Focus source.

### Archive and Scan

Archive and Scan supply image-level evidence and human judgments. They show whether an image is a
Focus member or trial result and provide a direct return to that Focus.

### Redundancy, Novelty Decay, and Lineage

These tools explain a Focus from different angles:

- Redundancy tests whether apparent breadth is repeated composition or near-copy structure.
- Novelty Decay tests whether a prompt family still yields new territory.
- Lineage tests whether local mutations improve on their parents.

Each page receives the current Focus explicitly. A page may calculate live evidence from stable
member tags, but it must distinguish a current calculation from the saved Focus revision.

### Compare

Compare records human preference evidence. It remains a leg-scoped labeling tool, but it marks
pairs that intersect the active Focus and offers a return link after the choice.

### Cockpit

Cockpit tests one Focus revision. It receives the Focus and source scope explicitly and never
changes the global active leg during a GET request. The Focus and trial specification defines this
handoff.

### Runs

Runs reports trial progress, spend, stop reason, and result links. A completed Focus-derived trial
links to result review and the exact source Focus revision.

## Shared Context

Every page header shows:

- current page;
- active expedition and leg;
- active Focus label and revision, when present;
- running-search state, when present;
- the Guide control.

The active expedition and leg remain explicit even when a Focus temporarily displays evidence
from another leg. A Focus-scoped page labels that difference instead of mutating
`active_leg.json` on read.

Focus identity and scope travel in explicit URLs and API payloads, for example
`/cockpit.html?expedition=trent_v3_epoch4&leg=freeform1&focus_id=focus_<uuid>`. The server validates
the Focus's recorded expedition and leg; it does not infer scope from the current global selection.

Every Focus-capable page uses the same `expedition`, `leg`, and `focus_id` query keys. Shared header,
workflow, evidence, Guide, and return links preserve all three values. "Active Focus" means the
Focus named by the current URL. The application must not create another mutable global active-Focus
pointer. A bare tool URL remains leg-wide and shows no active Focus.

## Language and Interpretation

The interface explains technical terms the first time they appear:

- A **centroid** is the average location of a group of image embeddings.
- **Cosine similarity** measures how closely two embedding directions align; higher values mean
  the model sees the images as more alike.
- A **frontier** is an empty metric cell next to populated cells. It is reachable evidence, not a
  predicted improvement.
- A **noise floor** is the ordinary variation seen when the same setup runs again. Changes smaller
  than that variation do not support a useful conclusion.

The interface must distinguish observation from interpretation. "This region contains six
redundancy clusters" is an observation. "Mark-making matters more than subject" is an
interpretation that needs a test.

## Empty and Failure States

- A tool with no active Focus remains usable in leg-wide mode and offers Create Focus where a
  stable selection exists.
- A Focus with missing member tags shows the missing count and preserves the saved record. It must
  not replace missing members with new nearest neighbors.
- A tool that cannot calculate Focus evidence explains which input is absent and links to the
  nearest useful stage.
- A failed trial remains attached to its Focus with the failure receipt. Learn can record what the
  failure taught about the process without pretending it tested the hypothesis.
- Read-only navigation never writes selection state or generation data.

## Non-Goals

- The workflow does not automate scientific judgment.
- The 2D Solution Map does not become a literal or stable coordinate system.
- The workspace does not hide the existing tools behind one opaque assistant.
- This work does not turn every tool into a linear wizard.

## Acceptance Criteria

- Explore presents the five stages as one connected keyboard-accessible control, not cards.
- A user can create a Focus from Solution Map or Coverage and open it from every evidence tool.
- Tool navigation preserves the Focus and its expedition/leg scope.
- Opening Cockpit cannot change the active leg as a side effect of GET.
- A completed trial links to both its result images and source Focus revision.
- Empty, stale, and failed states preserve evidence and offer a concrete recovery route.
- Desktop and 390px mobile views keep the active scope, Focus, and Guide entry understandable.
- Explore opens as a dense research desk with evidence and current work, not a marketing homepage.
