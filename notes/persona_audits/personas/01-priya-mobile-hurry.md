# Persona: Priya — mobile, in a hurry

- Task ID: `oc_mrr56l4i_c3124dc1`
- Model: `cheapestinference/glm-5.2`
- Viewport: 390x844 (mobile)
- Character: young vet tech checking the app on a phone during a work break

## Report

# Priya's walkthrough notes (in her voice)

Okay so my friend texted me this link "CLAWMARKS" and said it's an AI art tool. I'm on my break, phone in one hand, eating a granola bar. Let me see.

**Landing on the homepage.** "CLAWMARKS uncanny scan. Browse and curate AI-generated artwork from this LoRA search." Wait, what's a LoRA? What's an "uncanny scan"? I guess there's pictures here somewhere. There's a grid of little square thumbnails, okay, art, finally. But above the grid is this WALL of dropdowns: Sort, Type, Category, Prompt, "Similarity to real art >=", "Similarity to real art <=", Search, "picked only", "favorited only." Every dropdown has weird options like "grid (fixed sweep)", "negtrigger", "allnight explore", "round2 exploit." I have no idea what any of that means. I just want to look at the cat pictures.

**Actually finding the pictures.** Easy on this page, they're right there. But on every OTHER page the pictures vanish and I'm staring at jargon. So, mixed.

**Tapping a picture.** A little popup opens with the image, a heart button, and "generate counterfactual." Okay wait, what does this even mean, "counterfactual." I tap the tiny "i" next to it and it says "It costs real generation time/money." WHOA okay good thing I didn't tap the actual button. But also, why is the spending-money button just sitting there looking like a normal button with no warning on it? That feels mean.

**The "Guide" button in the top bar.** I tap it. Nothing happens. I tap it again. Nothing. It's just dead. Cool, thanks.

**Top-right "session status" link.** I tap. Get a page literally titled "clawmarks curation server" that says "sweep dir: /home/jeremy/.local/state/clawmarks/expeditions/..." Wait, whose computer is this, Jeremy's? Why am I seeing file paths? This is a developer's debug page, not for me.

**The page-jump dropdown** at the top has like fifteen destinations. "Find gaps in the image space", "Find near-duplicate groups", "See which prompts are running out", "Trace image ancestry." Sounds like a sci-fi movie. Also literally the same item "Choose between two images" shows up twice in the list. Bug?

**"See predicted favorites."** Sounds promising, show me the good ones. I tap. Get an error: "No trained model at /home/jeremy/.local/state/clawmarks/expeditions/trent_v3_epoch4/freeform1/preference_pairwise_model.joblib. Run python -m clawmarks.search.preference_pairwise_model first." EXCUSE ME? I'm a vet tech on my break, I am not running Python commands.

**"Check taste-model readiness."** Slightly better. "Comparisons: 0 usable of 6 total (needs 50)." Okay that I kind of get, I need to do more something. But there's a button that just says "Retrain now" and no warning on it. "Retrain" sounds expensive and ML-y so I'm not touching it.

**"Choose between two images."** THIS page makes sense. "Tap or click the image you prefer." Two pictures side by side, a little magnifier to zoom. Progress bar: "Model unlocks in 50 votes, 0/50 usable comparisons (6 submitted)." Clean. This is the one page that talks like a person. Tiny gripe: it says "press ←/→" but I'm on a phone, no arrows.

**"Build one image trial."** Holy jargon, Batman. "Reach a sparse faithfulness x novelty frontier." "LoRA strength." "ddim / 28 / 7.5." "Seed strategy." Buttons labeled "Send draft to queue" and "Autopilot." None of them say they cost money but I can smell it. I backed out fast.

**"Best images by area."** This is the one I wanted. But the very first paragraph is a giant wall of text about MAP-Elites and DINOv2 and "population quartiles" and then admits "the scorer can't tell which image in a cell is the better picture." So... they're not the best? Also every thumbnail says "highest novelty" underneath. Which is it, best or novel? Make up your mind!

**Tiny header button "trent_v3_epoch4/freeform1."** I tap it, a box pops up: "Switch research context" with "+ new expedition" and "+ new leg." Sure, I definitely know what an expedition or a leg is.

Also random: a few pages have a console error ("Transition was skipped") but I don't think that's user-visible.

Honestly? If my friend hadn't asked, I would've bounced after ten seconds. The compare-two-images page is great. Everything else feels like it was built for the person who made it, not for me.

## What actually confused me
- "LoRA", "uncanny scan", "expedition", "leg", "MAP-Elites cell", "DINOv2", "faithfulness/novelty", "ddim", "cfg", "counterfactual", "redundancy clustering", "lineage" — none of it is in English I speak. No glossary in sight on the homepage for a first-time visitor.
- The "Guide" button in the header is dead. Tapped twice, nothing happens.
- "See predicted favorites" threw a raw error with a `/home/jeremy/...` filesystem path and told me to run a Python command. That's not okay for an end-user page; also it leaks a username.
- Same `/home/jeremy/...` path leak on the "session status" page.
- Money-spending buttons ("generate counterfactual", "Send draft to queue", "Autopilot", "Retrain now") have no visible warning on the button itself. The cost is only revealed if you happen to tap the tiny "i" beside one of them, and most don't even have an "i".
- The page-jump dropdown lists "Choose between two images" twice.
- Page titles vs nav labels are inconsistent: nav says "session status" but the page heading is "Status" and the browser title is "clawmarks curation server." Nav says "Best images by area" but the page heading is "Elite archive."
- "Best images by area" page tiles all say "highest novelty" instead of "best," and the intro paragraph admits the scorer can't actually pick the best image. Contradicts the page name.
- "Check taste-model readiness" says "0 usable of 6 total" comparisons. Why are 6 submitted but 0 usable? Am I doing something wrong? Not explained.
- Compare page tells me to "press ←/→" which doesn't exist on a phone.
- The "Switch research context" dialog uses jargon ("expedition", "leg") with no plain-language hint about what those are.

## What worked well
- The compare-two-images page is genuinely friendly: clear instruction, big tap targets, magnifier zoom, "Model unlocks in 50 votes" progress bar. Felt designed for a human.
- The "i" tooltip next to "generate counterfactual" is, once opened, blunt and honest ("It costs real generation time/money"). Good text, just needs to be the default state, not buried behind an "i".
- Image lightbox has clear close (×) and prev/next (‹ ›) arrows, plus a row of "similar images" underneath. Nice for browsing.
- The filter bar shows a live count ("50 / 50 images | 0 picked | 0 favorited") so I always knew how many things I was looking at.
- The "Check taste-model readiness" page at least told me in plain numbers what was missing (needs 50, have 6) and linked me to the compare page to fix it.
- Page load was snappy and the layout didn't make me horizontally scroll on the phone-width viewport, which I was bracing for.

Status: DONE
