# Scaling from 10K → 10M Events/Day
What We Thought Would Change vs What Actually Did

👉 Ever heard:

“Don’t worry, we’ll handle scale when we get there.”

Then “there” arrived…
and everything behaved differently than expected?

Scaling doesn’t just stress your system.
It exposes wrong assumptions.

A Setup Most Teams Start With

App → Logstash → Elasticsearch → Dashboards

At ~10K events/day:
✔ Dashboards are fast
✔ CPU is low
✔ No alerts

Life is good.

Then the business grows:
• New customers
• New features
• More logs, metrics, events

Soon you’re heading toward 10M events/day.

And that’s when reality hits.

What Teams Think Scaling Requires ❌

• “We just need bigger servers”
• “Elasticsearch handled 10K, it’ll handle 10M”
• “Add more Logstash workers”
• “We’ll tune later”
• “Monitoring can wait”

Sounds reasonable.
Works… until it doesn’t.

What Actually Changes at 10M/Day ✅
1️⃣ Architecture Stops Being Optional

At scale:
• Spikes never stop
• Indexing fights search
• GC pauses kill throughput
• Retries amplify load

This is where teams learn the hard truth:

👉 Search engines are not buffers.

The shift that saves systems

Before:

App → Logstash → Elasticsearch


After:

App → Kafka → Consumers → Elasticsearch


Kafka absorbs spikes.
Elasticsearch focuses on search.
Failures stop cascading.

2️⃣ Backpressure Becomes Critical

At low scale:

“It’ll catch up.”

At high scale:
• Producers keep pushing
• Consumers retry
• Elasticsearch falls further behind
• Latency explodes

Without backpressure, everything slows together.

Suddenly, consumer lag becomes your most important signal.

3️⃣ Retries Stop Being Innocent

At 10M/day:
• One failure becomes 10
• Then 100
• Then a feedback loop

Teams discover:
• Idempotency is mandatory
• Exactly-once isn’t end-to-end
• Duplicate handling is non-negotiable

Retries don’t save systems.
They can drown them.

4️⃣ Observability Beats Raw Throughput

At scale, you don’t debug logs.

You debug:
• Consumer lag
• Ingestion vs indexing rate
• Queue depth
• Processing latency percentiles

Dashboards stop being “nice to have”.
They become survival tools.

5️⃣ Simple Designs Win

At scale:
• Clever code fails
• Tight coupling breaks
• Recovery scripts panic

Teams that survive prefer:
• Queues over direct writes
• Replay over manual recovery
• Isolation over optimization
• Predictability over cleverness

Scaling punishes complexity.

The Real Before vs After

🔴 10K/day mindset
• No buffer
• Tight coupling
• No replay
• Fragile under spikes

🟢 10M/day reality
• Buffered ingestion
• Controlled failure
• Replayable data
• Predictable scaling

Same tools.
Very different outcomes.

The Lesson Teams Learn Too Late

Scaling isn’t about:
• Faster code
• Bigger machines
• More threads

It’s about:
👉 Designing for failure, not success.

At 10K/day, the happy path dominates.
At 10M/day, the failure path is the system.

💡 Scaling doesn’t require new tools.
It requires new mental models.

👉 What broke first the last time your pipeline scaled?
Elasticsearch? Ingestion? Visibility?

👇 Drop your war stories — that’s where real learning lives.
