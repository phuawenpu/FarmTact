# Hong Sang-soo, repeated days, and learning to see a farm

FarmTact could make a small change in a familiar situation feel consequential. The player sees the same bed, the same customer order and the same approaching harvest twice. The second time, one date has moved. Nothing looks spectacularly different. Yet a promise that was possible has become impossible. The player discovers a relationship between things they had already seen.

That is the most useful connection to Hong Sang-soo's cinema: repetition can change the observer. Applied to FarmTact, it gives us a design ambition: after a short round, players should notice something about farming that they would previously have overlooked. A bigger score may accompany that change, but a better question is also a meaningful result.

This essay separates research about Hong and learning from a proposed direction for FarmTact. Proposed scenes, interface labels, rewards and learning measures below are design concepts. Existing capabilities are identified separately. None of the proposals establishes real-farm validity for the synthetic model.

An accompanying [offline playable storyboard](repeated-day.html) lets the reader try the two-date discovery directly. It is deliberately a small timing exercise, with its assumptions visible; it does not pretend to run the full planner.

**The first distinction is between having a form and carrying one predetermined message.** It is tempting to say that Hong's films look meaningless until a hidden message is decoded. His own account suggests something more interesting. In the 2015 Cinema Scope interview about *Right Now, Wrong Then*, he allows that viewers can connect the two parts through differences in conduct, but insists that the worlds retain independence. He resists reducing their relationship to one moral interpretation. The sequence of experiencing them matters, even when a final explanation remains unsettled. [Francisco Ferreira and Julien Gester, Cinema Scope, 2015](https://cinema-scope.com/cinema-scope-online/tiff-2015-cinema-scope-64-preview-right-now-wrong-then-hong-sangsoo-south-korea-masters/page/2/).

We can distinguish three questions. What happened? How did its presentation organize my attention? What do I think about it now? A film can be very precise about the second while leaving the third open. In a farm game, we need an additional question: what could I actually change? A player must be able to answer that without decoding the interface.

Suppose a player has a feasible plan that protects cash but leaves some delivery shortfall. The quantities, dates and unmet commitments should be explicit. Whether protecting cash was worth that cost can remain a subject for judgment. The system can establish the consequence under its assumptions without announcing that the player has become a bad farmer.

This gives us a useful division of responsibilities. The rules owe the player clarity. The experience can leave the player with an unresolved priority. Mystery about another person's values may be fruitful; uncertainty about whether the Save button worked is simply a defect.

**Hong's ordinary surfaces already contain the evidence.** In the MUBI interview on *Right Now, Wrong Then*, he locates much of the difference between the doubled encounters in emotional attitude, facial expression and vocal intonation. He also describes starting with people and places, discovering a structure during shooting, and adapting a final scene when snow arrived. The resulting coherence does not require every detail to have been planned from the outset. [Christopher Small and Daniel Kasman, MUBI Notebook, 18 August 2015](https://mubi.com/en/notebook/posts/an-interview-with-hong-sang-soo).

The useful analogy is an order label. On a first pass, a player sees “22 kg caixin” and thinks about volume. On a second pass, they notice the delivery date. On a third, they notice that the only stock on hand expires before that date. Those are ordinary fields in a record. Together they become a situation.

We should therefore make important relationships visible in the farm itself. Selecting a crate could highlight the bed that supplies it and draw a line to its delivery date. Selecting a due-date marker could reveal the eligible harvests. An expired inventory lot should remain available as evidence, with its status explained, rather than silently disappearing from the player's account of what happened.

The discovery is not that the crate secretly symbolizes something else. It is that a crate means something different when it has to be ready for a particular person at a particular time.

**Three films suggest different kinds of playable structure.** These are analogies, not claims that Hong designed instructional experiments.

| Film or documented method | What the structure makes available to a viewer | A corresponding FarmTact experience |
|---|---|---|
| *Right Now, Wrong Then*: a similar encounter is presented twice | Recognition makes small differences available for comparison | Replay a frozen farm with one assumption changed; keep the policy and other inputs fixed |
| *The Power of Kangwon Province*: separated accounts occupy overlapping time | Later information reorganizes the viewer's understanding of earlier events | First inspect the harvest schedule, then the order schedule, then align both on the same dates |
| Hong's account around *The Day He Arrives*: form develops from everyday situations | Familiar material can acquire structure through arrangement and return | Build episodes from actual shortages, occupied beds and expiring stock found in a saved snapshot |

Marshall Deutelbaum's analysis of *The Power of Kangwon Province* explains how the separately presented trips can be reconstructed as overlapping action. A repeated train image helps establish their temporal relation. This is evidence for formal organization beneath apparently casual movement, rather than evidence of a single concealed moral. [Deutelbaum, *Reconstruction* 8.3, 2008](https://digitalcommons.odu.edu/reconstruction/vol8/iss3/3/).

In a 2011 interview, Hong describes using everyday situations and allowing form to arise from the material or change with it. [Gabe Klinger, MUBI Notebook, 10 May 2011](https://mubi.com/en/notebook/posts/catching-up-with-hong-sang-soo). For FarmTact, the design implication is to inspect our numerical world before inventing a dramatic plot. A real conflict between two dates is enough to begin a scene.

**A short episode could begin with the sentence: “There is enough caixin. Why is the order still late?”** The following facts come from FarmTact's reference fixture, not from real agronomic observations. On the planning date, 8 September 2026, the first caixin batch is scheduled to produce 44 kg on 14 September. A booked order requires 22 kg on that date. The opening 5 kg inventory expires on 10 September. The declared caixin recipe takes seven nursery days and twenty-one growing days. [Reference generator at the frozen release source](https://github.com/phuawenpu/FarmTact/blob/e9c3edfe10da162e4f50fd5a69df5a4394aa0812/packages/fixtures.py).

The first pass shows the scheduled harvest beside the order. The second pass starts from the same saved state and delays that batch by three days. Its quantity is unchanged, but it now arrives on 17 September. Ask the player to choose what deserves inspection: total kilograms, harvest date or selling price. All three remain inspectable; the choice indicates where the player expects the explanation to lie.

After the player selects the dates, align them. The order needs crop on 14 September; this batch now arrives on 17 September. The opening stock expired earlier. New sowing on 8 September cannot mature by 14 September under the declared 28-day recipe. This establishes why those sources cannot fill that booked order. It does not establish the exact whole-farm shortfall, which also depends on the rest of the simulated demand and allocation rules.

The next prompt could be: “Would planting more today rescue this delivery?” The important action is a prediction followed by checking the timeline. A player who correctly identifies the limit has accomplished something even if the delivery remains impossible in this branch.

An optional final prompt changes the task: “Find a later delivery that new sowing could still help.” That moves the player from accepting a constraint to finding an opportunity. It also avoids teaching a simplistic lesson that planting is useless. Timing determines which problem a planting decision can address.

The expected experience is specific: initial confidence, a small surprise, inspection, then a more precise question. The intended learning result is also specific: on a fresh example, the player compares maturity with the deadline before choosing a response. Both are hypotheses to test with people, not outcomes guaranteed by an elegant analogy.

The full local planner supplies a concrete example of the wider consequences. With the reference fixture, alpha 0.35, the Balanced policy, and only `batch-01` delayed three days with yield unchanged, the following results were calculated during this research. They cover the complete planning horizon, not just the 22 kg order. Both plans were feasible under the validator, which does not mean that all demand was satisfied.

| Synthetic planner metric | Reference | Three-day delay | Change |
|---|---:|---:|---:|
| Total harvest | 814.00 kg | 814.00 kg | 0.00 kg |
| Delivery shortfall | 505.01 kg | 536.02 kg | +31.01 kg |
| Waste | 181.99 kg | 212.99 kg | +31.00 kg |
| Margin | SGD 2,957.37 | SGD 2,776.01 | −SGD 181.36 |
| Labour used over the horizon | 71.38 hours | 71.38 hours | 0.00 hours |

Here the philosophical point has numerical substance: the same total harvest can have different usefulness because availability occurs at different times. These are reproducible-input synthetic computations, not observed farm outcomes, buyer-level allocation proof or a promise of a unique optimum from a time-bounded solver. [Calculation record, settings and solver status](hong-delay-calculation.json).

**We should design the comparison so that it deserves the player's trust.** Hong can preserve an unresolved relationship between two cinematic worlds. A simulation that attributes a delivery change to a harvest delay has a stricter obligation. The comparison must start from compatible frozen inputs, use the same forecast settings and selected policy, and identify the changed assumption. If several inputs differ, the interface should describe a combined scenario instead of attributing the result to one slider.

FarmTact already has much of this machinery: immutable explorer datasets, recorded generator and forecast settings, numerical branches, baseline compatibility checks and same-policy comparisons. The proposed player experience is a clearer path through those capabilities. [Current scenario implementation](https://github.com/phuawenpu/FarmTact/blob/e9c3edfe10da162e4f50fd5a69df5a4394aa0812/services/api/scenarios.py).

There is an important difference between changing the world and changing a decision. A harvest-delay assumption asks what happens if the crop becomes available later. A cash constraint asks what the plan can achieve with less money. Selecting a different strategy asks what the planner recommends under another objective. Those are three distinct experiments. Calling all of them a player “choice” without explaining their role would blur responsibility.

Use separate verbs: **Change an assumption**, **Compare a strategy**, and **Inspect the evidence**. A player can then say, “I did not cause the delay; I tested how my plan copes with it.” That is a richer kind of agency than pretending the farmer controls every event.

**A second episode can make forecasting feel understandable without giving the forecast a personality.** Begin with a small line of historical demand and one recent increase. Offer two settings labelled “Respond more slowly” and “Respond more quickly,” with the EWMA alpha visible in details. Ask which forecast will react more to the recent observation. Reveal both on the same scale.

The player learns that changing a forecast setting changes how the same history is weighted. It does not change the booked orders that already exist. A useful little challenge is to find the card that should remain unchanged when alpha changes. That turns an abstract boundary between evidence and interpretation into a visible invariant.

Afterward, an explanation can name EWMA and show its formula. The solver should receive exactly the selected saved forecast configuration. A smooth line should never earn a badge merely for looking plausible. If we want to assess predictive performance, we need an appropriate held-out comparison and clear limits on what synthetic history can demonstrate.

An episode might end with: “Your forecast changed. What new fact did you learn?” The correct response may be “No new fact; I changed how I used the old facts.” This is useful epistemic humility expressed through a small game action. It is especially relevant in an app containing advisors: a different explanation or projection is not automatically new evidence.

**A third episode can put two reasonable priorities into tension.** Present one completed result through Ravi's order perspective and Ben's resource perspective. Ravi draws attention to unmet deliveries. Ben draws attention to the labour and cash the plan requires. Both use the same frozen numbers. The player switches the visible emphasis and sees how one result can support two concerns.

Then ask: “What are you trying to protect in this experiment?” Offer a concrete target such as reducing delivery shortfall or staying within available labour. Show the resulting tradeoff under the actual policy comparison. The ending need not select a universal winner. It should make the chosen sacrifice visible.

Lean, Balanced and Resilient need descriptions of their operational objectives and observed consequences. Their names must not function as personality judgments. “Balanced” can sound like an official moral endorsement before a player has read a single result. We should let the figures establish what each policy does in this particular situation.

A professional player may reject our objective entirely. That can be an intelligent response: perhaps a buyer relationship, overtime preference or quality threshold is missing from the model. An optional note—“What would change your decision on a real farm?”—can record that boundary. It should not manufacture a numerical trust or wellbeing score for something the engine does not calculate.

**A fourth episode can teach the difference between a pattern and an explanation.** The reference history contains a repeating demand pattern created by a deterministic formula. A player can enlarge or remove its amplitude and watch the preview change. The game then asks whether the repetition was measured seasonality or an assumption supplied by the generator.

This is a compact form of model criticism. A visually convincing pattern has a provenance. The player taps it, sees its source and learns that explanation includes asking how the data was made. The corresponding public-context challenge could show a source with registry information but no ingested observations and ask what can actually be plotted. The available answer is absence of data, not a decorative invented curve.

That kind of scene makes the data explorer part of the game world's evidence. It ceases to be a room visited only to satisfy a transparency checklist. The player's immediate task supplies a reason to open the record.

**A fifth episode should allow nothing to change.** One archived AI-persona review reported reducing weekly labour availability to 70% while every displayed outcome stayed the same. The review did not establish the reason; it noted that the interface failed to reconcile weekly allowance with labour use over the whole horizon. [Original review 04](https://github.com/phuawenpu/FarmTact/blob/e9c3edfe10da162e4f50fd5a69df5a4394aa0812/reports/panel/review04.json).

This is a good candidate for a scene called “The quiet week.” Ask: “I gave the farm fewer hours. Why did the plan stay the same?” Possible explanations include spare capacity, another binding constraint, or an unrefreshed result. The game must verify which applies. Show original and changed capacity, required labour, and slack for the same week and units. An unchanged result alone does not prove spare capacity.

If verified spare capacity explains the outcome, the player has discovered a buffer. They can then make another bounded experiment to locate when labour begins to matter. If another constraint dominates, link to it. If a run failed or the interface is stale, repair and report that state rather than disguising it as a lesson. A designer who forces every slider movement to produce dramatic punishment would destroy the very opportunity to understand a system's structure.

**The order of discovery and explanation matters.** Schwartz and Bransford's *A Time for Telling* reported three classroom studies with college students learning psychology concepts. Analyzing contrasting cases followed by an explanation improved later predictions relative to the study's comparison treatments. Analysis without subsequent explanation was insufficient in a relevant comparison. This supports a guided sequence worth testing, not a claim that unguided discovery or a farm game necessarily teaches twelve-year-olds better. [Schwartz and Bransford, 1998](https://aaalab.stanford.edu/papers/time_for_telling.pdf).

For FarmTact, a candidate sequence is:

1. Show a situation small enough to understand.
2. Invite one prediction, with “I'm not sure” available.
3. Reveal a completed calculation and the changed records.
4. Let the player compare the relevant dates or quantities.
5. Give a brief explanation of the relationship.
6. Offer one different case to see whether the relationship transfers.

Do not hide operating instructions in pursuit of discovery. Tell players how to move the map, what the slider changes, whether an input is saved, and what a run will do. The discovery concerns the farm relationship, not the button's function. Experienced players should be able to skip the prediction prompt and inspect the calculation immediately.

This also gives the advisors a stronger role. A short prompt before a reveal could ask where to look. A short explanation afterward could identify the verified constraint. A full conversation remains an explicit player action, attached to the frozen snapshot. Ordinary inspection, predictions, replays and template explanations need no inference calls.

The metaphor is a companion at the table who helps you look again. It does not require an advisor to pretend to be uncertain about a date that is already known, or to withhold an answer after the player asks directly.

**The game needs both visible effects and lasting implications.** Salen and Zimmerman's account of meaningful play connects discernible action–outcome relationships with their integration into the larger game. [*Rules of Play*, “Meaningful Play” excerpt](https://sites.cc.gatech.edu/classes/AY2006/cs4455_spring/documents/sz-unit11.pdf). Our application is concrete: after moving a forecast setting, the player sees which line changes; after saving and running it, they see which planting and delivery consequences follow.

A responsive slider alone is not enough. It can be a pleasurable instrument with no comprehensible stakes. Equally, a deeply calculated consequence buried three panels away may be functionally invisible. Link the movement to the changed result, then link that result to the next feasible action or acknowledged limitation.

This suggests maintaining a stable visual composition across a replay. Keep the camera, crop, date range, scale and policy consistent. Change the affected harvest marker and its connected delivery status. Offer a text-and-table equivalent. If a reveal changes every chart scale and opens a different tab, we make the player reconstruct the scene before they can notice the difference.

**A result can be worse while the player becomes better at the game.** A failed delivery can expose an assumption. A feasible result with a shortfall can show that biological constraints were respected even though every commitment could not be met. An infeasible result can establish which proposed demands exceed the allowed resources. These should be distinct visible states, with reasons.

Jesper Juul's analysis of failure argues that it can lead players to reconsider how they understand a game. It does not imply that arbitrary punishment creates useful learning. [Juul, “Fear of Failing?”, 2009](https://jesperjuul.net/text/fearoffailing/). For FarmTact, the design inference is to make another comparison inexpensive and preserve the evidence from the previous attempt.

An optional notebook could acknowledge a demonstrated action: “You traced this shortfall to its harvest date.” A stronger acknowledgment comes after a new case: “You found a different order with the same timing problem.” Avoid endless points for opening panels, running identical branches, or agreeing with an advisor. Those actions can be logged as activity; they do not establish understanding.

There is a concrete implementation gap here. The current quest progress function marks a quest completed and awards its discovery badge when an inspection flag is recorded. It does not collect a prediction or test an explanation. The proposed notebook would add evidence of understanding; it is not a description of the existing badge. [Current progress function](https://github.com/phuawenpu/FarmTact/blob/e9c3edfe10da162e4f50fd5a69df5a4394aa0812/services/api/scenarios.py#L174).

We should also permit a quiet ending. The player can save a branch, record what remains uncertain and leave. No crop should suffer because they did not return to the browser on a real-world schedule. Repetition should offer another perspective, not impose a daily obligation.

**There is a philosophical difference between uncertainty about a fact and disagreement about a value.** Consider three statements: “This batch arrives on 17 September,” “The model predicts this plan has a lower shortfall,” and “This is the plan I would prefer.” The first is a stored fact within the scenario. The second is a computed claim under declared assumptions. The third involves a person's priorities.

FarmTact should let the player move between those levels without collapsing them. Inspect records to establish the scenario; inspect a calculation to understand the prediction; compare priorities to make a judgment. A forecast can be reproducible without being certain about the real world. A preference can be defensible without being numerically optimal under our chosen objective.

This is where the Hong connection becomes deeper than a visual style. A repeated scene can reveal that my earlier judgment was based on too little attention. The game can let me recognize a similar limitation in my own planning. I may have noticed kilograms and missed dates, noticed revenue and missed cash timing, or trusted a smooth forecast without checking its origin.

There is no need to humiliate the player for that. The satisfying moment is the ability to see a relationship now. The farmer's visible world may look almost unchanged; their capacity to read it has grown.

**Rules also express a point of view.** Ian Bogost describes games as media that communicate through simulated experiences and procedural rhetoric. [Bogost, “Persuasive Games”](https://bogost.com/games/persuasive-games/). FarmTact's model inevitably privileges what it represents and measures. If money is the only celebrated outcome, the interface communicates a value even if the prose claims neutrality.

The remedy is to expose the scope of the model and allow several intelligible goals. Display cash, labour, waste and deliveries together where they materially conflict. Explain how the policy uses them. Let a player name an unmodelled concern without pretending that free text has altered the optimization objective.

Human trust is a useful example. The existing system can show that a delivery was missed. That does not mean it calculates a customer's future trust, business survival, food insecurity or a worker's wellbeing. A scene can make those human questions imaginable while keeping the numerical result limited to what was actually computed.

The same care applies to causal language. A delay experiment illustrates consequences within a specified model. It does not experimentally establish what rain will do to a real crop. Cached weather observations become scenario inputs only through a documented, justified relationship; a rainy picture must not silently apply a yield penalty.

**An independent edition is a new treatment of the game; a branch is another possibility inside one treatment.** This distinction makes our release architecture relevant to the artistic analogy. Returning to familiar material across editions can reveal a changed design intention. Returning to the same saved dataset within an edition can reveal an assumption's consequence.

Those comparisons answer different questions. A v1 versus v2 screenshot can show how navigation or sound changed. It cannot establish that a farming strategy improved if the two editions contain different farm states. Future release evaluations should use equivalent declared reference cases and retain their model versions, while every edition continues to own its separate user progress.

A useful evolution entry would say: “We thought players were confusing total supply with on-time supply. This edition places harvest and delivery dates in the same replay. Here is the original feedback, the implemented change, and the observation that would count as improvement.” It should also show an honest result such as “technically verified; learning effect untested.”

The archive then becomes a record of changing questions. Ten earlier AI-persona reviews remain evidence about their tested builds. A new release is not automatically a better game because it has more features, more enthusiastic prose or higher self-assigned marks. Real-player observation is a separate kind of evidence.

**Calmness can coexist with immediate play.** A proposed scene can be legible in under a minute without being frantic. One order, one bed, one date conflict and one replay are enough. Keep optional details ready for a curious learner or an experienced farmer. Let the same scene offer a visual relation first and exact records second.

Age accessibility should come through comprehension and control, not through calling one mode “for children” and another “serious.” A twelve-year-old might understand two dates before learning EWMA. A farmer may want the units, constraints and forecast settings immediately. Both deserve the same underlying factual account and the ability to control explanation depth.

Research on game motivation has associated experienced autonomy and competence with enjoyment; relatedness also mattered in the multiplayer study in Ryan, Rigby and Przybylski's four-study paper. Those findings motivate tests of comprehensible choices and useful feedback here. They do not prove that our fictional advisors create the same social experience as other players. [Ryan, Rigby and Przybylski, 2006](https://selfdeterminationtheory.org/wp-content/uploads/2020/10/2006_RyanRigbyPrzybylski_MandE.pdf).

Optional music can provide continuity while the same visual scene returns. A soft cue can confirm that a calculation finished or evidence was selected. Use distinct visible states for success, shortfall and infeasibility; a triumphant sound should not declare every completed job a good decision. Silence, reduced motion and equivalent text controls remain complete ways to play.

Native keyboard dictation fits this approach. A short reflection can be spoken through the device's ordinary keyboard if available. It should remain optional and writable. No player should need to compose an essay or activate a microphone to understand a harvest.

**The most valuable next release would test one complete discovery loop.** A practical candidate is the delayed-harvest episode above. It should offer one frozen starting situation, one explicit assumption change, one prediction, one completed result, a clear before/after comparison, linked records and a brief explanation. A second case tests whether the player can recognize the same relationship elsewhere.

| Design hypothesis | What the player actually does | Evidence of improvement | What would challenge the hypothesis |
|---|---|---|---|
| A stable replay makes timing legible | Compares harvest and delivery dates in two branches | Correctly identifies the binding date in a new case | Can repeat the original answer but misses a new timing conflict |
| Evidence links improve causal understanding | Opens contributing records after a result | Selects records that actually support the explanation | Opens many panels but attributes changes to unrelated inputs |
| A short prediction makes feedback useful | Chooses an expected direction or “not sure” | Revises a mistaken expectation and explains why | Treats the prompt as a mandatory quiz and quits |
| Optional explanations serve different experience levels | Expands or skips a concise debrief | Learners and experienced players complete the task without unwanted friction | Experts must click through elementary prompts; novices cannot find help |
| Clear tradeoffs support agency | States a priority and examines a relevant cost | Can defend a choice using a result and name a limitation | Selects a policy only because its name sounds approved |

These are proposed tests, not measured benefits. Technical acceptance checks should verify frozen inputs, same-policy comparison, stale-response rejection, record links and reproducibility. Learning evaluation should separately test recognition on unfamiliar cases and invite players to describe confusion. Engagement time and button counts cannot substitute for either.

Start with formative observation across the intended range of experience, including age-appropriate participation arrangements for young players. Compare discovery-first and explanation-first presentations without changing the underlying numerical case. Record who benefits, who wants to skip, and whether people understand that outcomes are simulated. A small formative study can expose a bad interaction; it cannot establish population-wide educational efficacy.

The proposed guiding sentence is: **“Play the same situation again, notice what changed, and decide what matters.”** It leaves room for calculation, curiosity and judgment. A successful ending might be a player saying, “I thought I needed more vegetables. Now I know which vegetables need to be ready when.”

**Implementation boundaries are part of the proposal.** Current quests apply bounded delay, yield, demand, labour or cash changes and rerun the numerical planner. They do not enact a player-directed day-by-day farming simulation. Comparisons support up to three compatible completed branches with one selected policy. Continuations keep the original comparison baseline. The proposed direct record-to-crate storytelling, prediction prompts, demonstrated-learning rewards and capacity explanations require additional interface or result work.

In particular, the current affected-delivery list does not establish individual buyer fulfilment. A future highlighted customer order must use an explicit, tested allocation mapping or be presented as a timing constraint demonstration like the offline storyboard. We should not let an emotionally attractive scene outrun the system's evidence. [Current consequence generation](https://github.com/phuawenpu/FarmTact/blob/e9c3edfe10da162e4f50fd5a69df5a4394aa0812/services/api/scenarios.py#L147).

**Source inventory.** Direct interviews support claims about Hong's stated process; the film analysis supports claims about temporal construction; the learning studies and game-design texts motivate hypotheses rather than validate FarmTact.

- Francisco Ferreira and Julien Gester. “Repetition and Difference: Hong Sangsoo on Right Now, Wrong Then.” *Cinema Scope* 64, 2015. [Interview](https://cinema-scope.com/cinema-scope-online/tiff-2015-cinema-scope-64-preview-right-now-wrong-then-hong-sangsoo-south-korea-masters/page/2/).
- Christopher Small and Daniel Kasman. “That Day the Snow Fell: Hong Sang-soo Discusses Right Now, Wrong Then.” *MUBI Notebook*, 18 August 2015. [Interview](https://mubi.com/en/notebook/posts/an-interview-with-hong-sang-soo).
- Gabe Klinger. “Catching Up with Hong Sang-soo.” *MUBI Notebook*, 10 May 2011; interview conducted 30 April 2011. [Interview](https://mubi.com/en/notebook/posts/catching-up-with-hong-sang-soo).
- Marshall Deutelbaum. “The Structure of Hong Sangsoo's The Power of Kangwon Province.” *Reconstruction* 8.3, 2008, pp. 1–17. [Repository and abstract](https://digitalcommons.odu.edu/reconstruction/vol8/iss3/3/).
- Daniel L. Schwartz and John D. Bransford. “A Time for Telling.” *Cognition and Instruction* 16.4, 1998, pp. 475–522. [Author-laboratory PDF](https://aaalab.stanford.edu/papers/time_for_telling.pdf).
- Katie Salen and Eric Zimmerman. *Rules of Play: Game Design Fundamentals*. MIT Press, 2004, “Meaningful Play.” [Book excerpt hosted by Georgia Tech](https://sites.cc.gatech.edu/classes/AY2006/cs4455_spring/documents/sz-unit11.pdf).
- Jesper Juul. “Fear of Failing? The Many Meanings of Difficulty in Video Games.” In *The Video Game Theory Reader 2*, 2009, pp. 237–252. [Author's full text](https://jesperjuul.net/text/fearoffailing/).
- Ian Bogost. “Persuasive Games.” Author's account of his studio and design philosophy, undated. [Primary source](https://bogost.com/games/persuasive-games/).
- Richard M. Ryan, C. Scott Rigby and Andrew Przybylski. “The Motivational Pull of Video Games: A Self-Determination Theory Approach.” *Motivation and Emotion* 30, 2006. [Full paper](https://selfdeterminationtheory.org/wp-content/uploads/2020/10/2006_RyanRigbyPrzybylski_MandE.pdf).
- FarmTact source commit `e9c3edfe10da162e4f50fd5a69df5a4394aa0812`: [reference generator](https://github.com/phuawenpu/FarmTact/blob/e9c3edfe10da162e4f50fd5a69df5a4394aa0812/packages/fixtures.py), [scenarios](https://github.com/phuawenpu/FarmTact/blob/e9c3edfe10da162e4f50fd5a69df5a4394aa0812/services/api/scenarios.py), and [advisor definitions](https://github.com/phuawenpu/FarmTact/blob/e9c3edfe10da162e4f50fd5a69df5a4394aa0812/services/api/conversations.py).
