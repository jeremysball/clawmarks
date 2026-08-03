# Persona: Walt — money-anxious, warned about billable actions

- Task ID: `oc_mrr5gy6n_4f8a37cb`
- Model: `cheapestinference/glm-5.2`
- Viewport: 1440x900
- Character: older, non-technical, nervous about accidentally spending someone else's money

## Report

# Walt's walkthrough report

OK, hold on. My grandson said "just look around, you can't break anything," and I wanted to believe him, but I'm gonna be honest with you: this thing made me nervous within about thirty seconds, and by the time I'd hit every page in that dropdown I was scared to click half of what I saw.

The very first thing that spooked me: I clicked one of the little picture tiles on the home page just to see it bigger, and a panel pops up with two buttons side by side, "favorite" and "↻ generate counterfactual." The word **generate** jumped right off the screen at me. Wait, is THIS the one that costs money? I almost didn't click the little "i" next to it because I figured if I had to dig for the warning, the warning wasn't really there for me. But I did click it, and sure enough, buried in the popover: "It costs real generation time/money." Good that it's there. Bad that the button itself looks exactly as safe as the "favorite" button right next to it. An anxious fella like me sees the word "generate" with no warning on the button, he doesn't click the "i," he just backs out of the whole panel.

Then I opened the dropdown and saw "Build one image trial." **Trial** sounds free, like a sample, right? I went there. The whole page is called "Generation cockpit," there's a button that says "Send draft to queue," and above it the words "4 images queued as a draft" and "New images will enter the trial record as a draft." Draft, draft, draft. That word made me feel like nothing was really happening, it was just a draft. But the button's inner workings are literally called "generate" (I'm not a coder, but the page title did say *Generation* cockpit, and there was a "Batch size" spinner and a "LoRA strength" spinner). I poked around that page for two minutes and never once saw the words "spends money" anywhere. That is the page I'd have gotten burned on. If my grandson hadn't warned me, I'd have hit "Send draft to queue" thinking it was free, because everything about it, the words, the framing, was designed to feel non-committal.

Then I went to "Run or monitor a search," which sounds the most expensive of all, and LO AND BEHOLD, this page does it right. Big button "Back up and launch," and right next to it, in plain text, "Spends money." Even a "$9.91" line showing what the last one cost. THIS is the page that made me exhale. Why can't the cockpit page do this? Why can't the "generate counterfactual" button?

One more: "Check taste-model readiness." I get there, there's a button labeled "Retrain now." No badge, no warning, no little "i" next to it, nothing. Is retraining free? Is it a nickel? Is it twenty dollars? I have no way to tell. I left that page immediately.

A bunch of other stuff left me shrugging. Every page has a "trent_v3_epoch4/freeform1" button top right that opens a panel with "+ new expedition" and "+ new leg" and a "create" button. I don't know what any of that costs, if anything. Same with the "Create Focus" button I saw on the map and coverage pages. Maybe it's a free note-taking thing. Maybe it isn't. Nobody told me. And on the home page the "trent_v3_epoch4/freeform1" button itself looks identical to a real action button, so I didn't even know it was navigation until I clicked it.

The stuff that's just pictures and graphs and "i" buttons, the lineage tree, the novelty decay watchlist, the redundancy clusters, the predicted-favorites page, those I felt fine on. Read-only. Nothing to bump into. That's what I wish the whole app felt like.

## controls I was unsure about and why

- **"Send draft to queue" (Build one image trial / cockpit page).** Worst offender. The internal class is literally `generate striate`, the page is titled "Generation cockpit," there's a batch size spinner, and yet there is no "Spends money" badge anywhere on the page. The word "draft" is used three times near it, which actively minimizes the action. An anxious user has no chance here.
- **"Retrain now" (Check taste-model readiness page).** "Retrain" sounds expensive (the task description even flagged training controls as billable), but there's no badge, no popover, no info button next to it. Zero cost signal either way.
- **"↻ generate counterfactual" (image lightbox on home / scan page).** Cost warning DOES exist, but only inside the "i" popover. The button itself sits next to "favorite" with identical styling, so the billable one doesn't stand out. The word "generate" is the only on-button hint, and an anxious user won't trust a hint.
- **"+ new expedition" / "+ new leg" / "create" (header dialog on every page).** No idea if creating a new expedition spins up anything billable. The "create" button has a class called `primary-action` (looks like a real action), but no context about what it actually does.
- **"trent_v3_epoch4/freeform1" button (top of every page).** Looks like an action button, is actually a navigation/workspace-picker. Misleading shape.
- **"Create Focus" (Explore image neighborhoods, Find gaps in the image space).** Two form fields and a "Create" button with no explanation of whether "Focus" is just a saved note or something that triggers work. Ambiguous middle ground.
- **"Mission" cards, target-cell selectors, Batch size / LoRA strength +/- spinners, "Autopilot" tab, "refresh suggestions" (cockpit page).** Each is unlabeled either way. "Autopilot" especially sounds like it might run something on its own. Individually they may be harmless, but they sit on the same page as the unlabeled "Send draft to queue," so once I'm suspicious of the page I'm suspicious of all of it.
- **"Guide" button.** I clicked it twice, it went "active," nothing visible happened. Not a cost issue, but worth flagging that the one button that should have explained all this didn't open anything I could read.
- **▶ play button (solution map).** Probably plays an animation. Probably free. The word "play" is innocuous but on an unfamiliar page I'm not certain.

## what made me feel safe

- **The "Spends money" badge on the "Back up and launch" button (Run or monitor a search page).** Clear, unambiguous, right next to the button, not buried behind a popover. This is the gold standard and what I wish every billable control looked like.
- **The "SPENDS MONEY" badge on the "Generate" button (Edit candidate ideas page).** Same pattern, equally clear. Bonus points because the page also explained in prose: "ask GPT-5.5 for more right now instead of waiting."
- **The plain-language safety paragraph on the runs page** ("Every launch backs up the round's out_dir first and refuses to start if that backup can't be verified by file count, checks the RunPod balance floor once up front, and refuses a second launch while one is already running"). That paragraph alone lowered my blood pressure. It told me the app itself was watching out for accidental spends.
- **The visible spend number "$9.91" on the runs page.** Showing me the past cost, openly, made me trust that costs weren't being hidden.
- **The pure read-only pages** (Trace image ancestry, See which prompts are running out, Find near-duplicate groups, See predicted favorites, Best images by area). No buttons except little "i" info popovers. Nothing to accidentally bump. This is what most of the app felt like, and it felt fine.
- **The "i" info popovers in general.** Where they existed, they were written in plain English, no jargon. The counterfactual one told me exactly what would happen and what it would cost. The problem was that they were opt-in, not that the content was bad.
- **The "Stop" button on the runs page.** Told me that if a run did get started, there was a way to halt it. (It was disabled because nothing was running, which itself was reassuring, the page was honest about state.)

The bones are good. Half the app already knows how to talk to someone like me. The other half, the cockpit page especially, is going to cost my grandson real money the day he stops paying attention, because nothing on the page told him it would.

Status: DONE
