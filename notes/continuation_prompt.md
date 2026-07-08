# Continuation prompt: CLAWMARKS project, reveal-plan branch

Use this to resume the conversation about the "show the artist something" branch of the
CLAWMARKS LoRA project. Read `notes/lab_notebook.md` first for full project background,
methodology, and reference tables; this file covers a newer thread that hasn't been merged into
the notebook yet.

## The real goal, restated

The DINOv2 hyperparameter sweep (5 rounds, probe-then-commit, see notebook Section 3) is not the
end goal. It's building a trustworthy instrument: a LoRA that has learned the CLAWMARKS style's
actual rules (marks, palette discipline, composition habits), not just memorized its most common
subject (cats). The real goal is to push that trustworthy instrument into new territory: generate
something novel enough, while still unmistakably in-style, to genuinely surprise the artist who
created the source images.

Two different jobs follow from this, and they're not the same checkpoint's job by default:

1. **Fidelity** (what the sweep optimizes): does the model reproduce the style's rules reliably.
2. **Novelty-within-style** (the actual goal): how far can a prompt push into subjects the 31
   training images never depicted before the output stops reading as CLAWMARKS at all.

A checkpoint that wins round after round on DINOv2-centroid similarity could still be narrow: it
nails cats and collapses into mush on anything unfamiliar. Winning the sweep and generalizing the
style are related but not guaranteed to be identical.

## Reusing the DINOv2 centroid for a different purpose

For novel-subject generations, the centroid metric changes role from a leaderboard to a floor
check. DINOv2 was chosen precisely because it doesn't encode "what object is this," only how it's
rendered. So a genuinely new subject, rendered faithfully in CLAWMARKS style, should still score
near the real self-similarity range (mean 0.61 among the 31 training images) even with zero
content overlap with the training set. A collapsed score on a novel subject is the signal that the
checkpoint learned "cat," not the style. Pass bar: lands near 0.5-0.6+, not "beats the previous
best."

## Timeline constraint

The artist sees something within the next few days. That rules out waiting on the full 5-round
sweep (~10-11 hours of GPU time across rounds, plus the noise-floor and data-side work between
them). The reveal piece needs to be a separate, faster branch built on the checkpoint that already
exists and already works (epoch 4, `checkpoints_v3_fixed/`), not a downstream product of the
sweep. The sweep keeps running as the longer-term whitepaper work in parallel.

## The creative concept: "counter-art"

Working idea, the user's words: "the same style and vibes applied to new and therefore uncanny
subjects. Put the artist himself in a liminal space almost. Counter-art maybe." The idea is to
turn the artist's own visual language back on him: render the artist himself, in his own style,
inside a liminal, dreamlike, unfamiliar space, subject matter his own 31 training images never
touched.

## Open question, deferred by the user, revisit next

Rendering a recognizable likeness of the artist needs one of:

- **A reference photo**, fed through img2img or a face-reference workflow (e.g. an IP-Adapter),
  so the model has an actual likeness to draw from.
- **A purely textual description** (no photo), which will produce "a man" in the CLAWMARKS style,
  not recognizably the artist himself.

The user said "we'll touch on that specific detail later." Ask again before building the reveal
generation pipeline: does a reference photo exist to work from, or does the piece stay
suggestive/abstracted rather than a recognizable likeness?

## Next steps once the reference-photo question is answered

1. Decide the prompt/workflow approach for rendering the artist (img2img+LoRA vs. text-only)
   based on the answer above.
2. Draft a small batch of "liminal space" subject prompts: uncanny, unfamiliar settings, still
   readable as CLAWMARKS.
3. Generate on the existing epoch-4 serverless endpoint (already stood up, see notebook Section
   5, Infra and access).
4. Score every generation against the real-image DINOv2 centroid as a floor check (pass bar
   ~0.5-0.6+), not a ranking exercise.
5. Curate the handful that pass the floor check and are visually striking; build a small contact
   sheet for the reveal.
6. After the reveal, fold whatever's learned from this branch back into `lab_notebook.md`.
