# Dead Letter Queues (DLQ) Are Not Optional
Ever been in an incident where someone casually says:

“Just re-run the job.”

…and the whole room goes quiet because:

you can’t replay cleanly

you don’t know which records failed

and you’re not even sure what got dropped

That’s the exact moment you realize something:

✅ Dead Letter Queues aren’t a nice-to-have. They’re what makes pipelines survivable.


A Real Day-to-Day Situation You’ve Probably Seen
Your pipeline looks simple:

Apps / APIs → Kafka → Consumers → Elasticsearch → Dashboards

It’s a normal day.

Then slowly, things start looking… off:

dashboards show missing records

one customer report is missing

alerts show consumer error rate went up

lag increases slightly

Nothing is fully “down”… but something is clearly wrong.

So you open the logs.

And there it is:

MapperParsingException Field [amount] cannot be parsed as long

One bad record.

One tiny payload.

And now your whole pipeline is stuck.

At this point most teams face the same painful options:

✅ Stop the consumer and fall behind ✅ Skip the record and lose data ✅ Retry forever and burn everything down

None of these are “production answers”.

This is where DLQ becomes the only sane move.


The Problem DLQ Really Solves
Pipelines rarely fail because everything is broken.

They fail because one message keeps failing repeatedly.

It could be:

schema mismatch

null in a required field

malformed JSON

bad timestamps

downstream timeouts

unexpected payload changes

And the worst part?

That one poison message can block thousands of good events behind it.

Without a DLQ… you’re not engineering. You’re firefighting.


What People Assume (Until It Hurts)
Here’s the common mindset:

“Bad data is rare.” “Retry will fix it.” “We’ll restart the consumer.” “It’s only a few records, just drop them.”

That sounds reasonable… until the business asks:

“Which records were missing?” …and you don’t have an answer.

That’s when trust breaks.


What DLQ Actually Gives You
A DLQ is not just a storage topic.

A DLQ is your recovery lane.

Instead of this:

❌ Fail → Retry → Fail → Retry → Block → Incident → Manual chaos

You get this:

✅ Fail → Retry N times → Move to DLQ → Pipeline continues

So your system stays alive even when data isn’t perfect.


The Rule Senior Engineers Follow
A pipeline without a DLQ is not production-ready.

Because in real systems:

✅ payloads change ✅ schemas evolve ✅ downstream services degrade ✅ “rare” bad data shows up daily ✅ bugs happen at the worst time

DLQ is how you contain failure without taking everything down.


The DLQ Setup That Actually Works
A clean pattern looks like this:

Main Topic → Consumer → Success → Elasticsearch  → Failure → Retry Topic (delay/backoff)  → Still failing → DLQ

What this achieves:

good events keep flowing

bad events get isolated

retries happen with control

your pipeline stays recoverable


A DLQ Without Replay Is Just a Graveyard
This part is important.

Many teams create a DLQ topic… and never touch it again.

That’s not resilience.

That’s avoidance 😄

A real DLQ strategy means:

✅ every message stores full context ✅ failures get categorized ✅ fixes happen first ✅ replay happens safely ✅ replay is idempotent

Because the whole point of DLQ is not “parking problems”.

It’s recovering cleanly.


The Career-Level Lesson
Junior engineers optimize for:

“Keep the pipeline running.”

Senior engineers optimize for:

“Make the pipeline recoverable.”

A DLQ is a design mindset:

✅ failures must be isolatable ✅ recovery must be repeatable ✅ replay must be safe

Because production pipelines don’t need luck.

They need recovery paths.


✅ Question for you:
Do you have a DLQ and a replay plan… or just a DLQ topic quietly collecting dust?

👇 What’s the worst poison-message incident you’ve seen in production?
