# Persona: Carla — non-technical stakeholder evaluating ROI/trust

- Task ID: `oc_mrr6erky_d0fc90b0`
- Model: `opencode/deepseek-v4-flash-free`
- Viewport: 1440x900
- Character: small-business owner considering paying for more search rounds, non-technical, money-focused

## Report

Okay, so I spent a good 15 minutes poking around this CLAWMARKS thing. The artwork -- I gotta say, some of those cat and wolf portraits genuinely made me stop and look. They've got this sketchy, inky, mixed-media feel that my customers would go nuts for. If I could get a steady stream of images that look like the best ones I saw in that grid, I could build a whole product line around them. The "style" ones -- the close-up cat faces, that wolf howling -- those have real commercial potential. The "conflict" ones are weirder, more abstract, harder to see on a mug or a tote bag but maybe that's part of the process.

But then I hit the "Run or monitor a search" page. That's where I found the only dollar figure in the whole app: **"Spend: started $9.91"** -- for one generation, 50 images. Zero picked, zero favorited. So $9.91 bought 50 images that nobody even bothered to say yes or no to. And the page is wide open to spend more: a big "Back up and launch" button with a "Spends money" sticker on it. There's no budget cap, no running total, no "this round will cost approximately X." Just a $9.91 starting point and an invitation to spend more.

I looked for any sign of quality getting better. The "novelty decay" page told me there's nothing to measure yet because there's only been one generation. The coverage map is probably useful to somebody but to me it looked like a spreadsheet of decimal ranges that I would never show a client. The "taste model" needs 50 comparisons to work -- they've done 6. So the tool can't tell what I like yet. My artists haven't picked or favorited a single image either.

**What would make me trust this with my money**

- A real budget dashboard. Show me "Round 1 cost $9.91 for 50 images. Round 2 would cost approximately $X. Your total spend to date is $Y." Give me a slider or a cap I can set so I'm not surprised.
- Before-and-after proof. If a second generation happens, show me "Generation 1 had 3 images worth keeping. Generation 2 had 8." I need to see the needle moving.
- Someone has to actually pick and favorite images. You can't sell me on a process when 0 out of 50 images caught anyone's eye. If nobody on your side is willing to say "that one's good," I'm not paying for another round.
- Plain English labels. "Faithfulness" and "novelty" mean nothing to me. Call them something like "follows the prompt" and "surprising / different from what we've seen." The (i) buttons might explain it but I shouldn't need to hunt for a definition.
- A one-page executive summary. Before I approve money, I want one page that says: "Here's what we spent, here's what we got, here's how the quality trend looks, here's what the next round targets." I'd want to look at the "Run or monitor a search" page right before saying yes, but right now that page only shows one number and a launch button.

**What made me hesitate**

- **$9.91 bought 50 images and zero reactions.** If I paid a freelancer $10 to paint something and they showed me 50 sketches without picking a favorite, I'd be annoyed.
- **No cost-per-round estimate anywhere.** Is the next round $10 or $100? I have no idea. The app clearly knows it costs money (it labels the button "Spends money") but won't tell me how much until after I've spent it.
- **The jargon wall is real.** "MAP-Elites cell," "taste-model readiness," "faithfulness x novelty frontier," "DINOv2," "LoRA search," "counterfactual generation" -- I read English fine but this is technical gatekeeping. I don't need to understand the engine to decide whether the car is worth buying, but right now the dashboard only speaks engine.
- **Too many pages.** There are 14+ navigation options. For someone evaluating whether to pay for more work, that's overwhelming. I'd want maybe 5 clear sections: gallery, results progress, budget, next steps, settings.
- **No "what's working" signal.** The compare page shows "0/50 usable comparisons" -- the model that learns my taste can't even be built yet. Nothing in the app says "these prompts did well, these didn't."
- **The search prompts are cryptic.** "conflict_pure_abstract_brushed-pa" -- this reads like a filename, not a description of what the AI was asked to make. If I'm funding prompt ideas, I want to understand what idea was tested.
- **The coverage map is the most visual progress indicator** and it's a spreadsheet of decimal-bounded cells. I can see the concept (some areas filled, some empty) but presented this way I can't actually use it to make a funding decision.

The artwork itself is genuinely exciting. The process might be brilliant. But as a paying customer, there is not nearly enough transparency on cost, improvement over time, or what my money would specifically buy.

Status: DONE
