# What I Look for When Reviewing a Data Pipeline Design


I’ve been in enough pipeline design reviews to know this pattern by heart:

✅ The demo works
✅ The architecture diagram looks clean
✅ The happy path is perfect

…and yet something in the back of your mind says:

“This is going to page someone.”

Because production doesn’t care how pretty your diagram is.

Production shows up with:

messy payloads

unpredictable traffic

downstream slowness

retries that explode

“unknown unknowns”

So when I review a data pipeline design, I don’t judge it by how it runs…

👉 I judge it by how it fails.

A Day-to-Day Pipeline Everyone Builds

Let’s say a team is building:

External API → NiFi → Kafka → Consumers → Elasticsearch → Kibana

Goal sounds simple:

ingest every few minutes

power dashboards

search + visibility

near real-time results

In the meeting, the team confidently says:

“We’re done. It’s working in staging.”

That’s when my real review starts.

Because working isn’t the same as surviving production traffic.

✅ My Senior Data Engineer Review Checklist
1) Backpressure: Where Does Pressure Go When Things Slow Down?

This is always my first question.

Because something will slow down eventually:

Elasticsearch indexing gets heavy

downstream services start rejecting

partitions go hot

networking gets weird

pods restart mid-load

🚩 Red flags:

ingestion keeps pushing no matter what

consumers retry aggressively

downstream takes the hit

everything collapses together

✅ What I want to see:

NiFi queues with thresholds

consumer throttling (batch + concurrency control)

lag treated as a buffer signal (not a panic number)

If your pipeline can’t slow down safely, it isn’t resilient. It’s just lucky.

2) Replayability: Can You Recover Without Panic?

This is the fastest maturity test:

👉 If you ship a bug today, can you replay yesterday’s data?

🚩 Red flags:

“We’ll re-pull from the source”

“We don’t retain that long”

“We’ll patch it manually”

✅ What I want to see:

intentional Kafka retention

safe offset reset strategy

DLQ exists with a replay path

reprocessing won’t corrupt the sink

Recovery should be a procedure… not a project.

3) Idempotency: What Happens When Retries Happen?

Retries are not an edge case.

They’re normal:

timeouts happen

deploys go wrong

consumers restart

ES mappings reject

“it worked in staging” fails in prod

🚩 Red flags:

retries create duplicates

dashboards drift

ES is insert-only

“exactly-once” is a slogan

✅ What I want to see:

deterministic document IDs

upserts instead of blind inserts

dedupe rules documented

You don’t need exactly-once claims. You need idempotent outcomes.

4) Failure Isolation: Can One Bad Record Block Everything?

One poison message shouldn’t freeze the pipeline.

🚩 Red flags:

consumer crashes on bad payload

one bad message blocks the partition forever

“we’ll restart it” culture

✅ What I want to see:

DLQ strategy

controlled retries → then route away

alerts tied to DLQ rate/trends

replay plan documented

A pipeline is only as strong as its failure lane.

5) Throughput Strategy: How Does This Scale Under Real Load?

Scaling isn’t “add more pods.”

Scaling is:

partitions support concurrency

keys distribute evenly

consumers match partition count

sinks don’t get overloaded

🚩 Red flags:

hot partitions

guesswork partition keys

“we’ll tune later”

✅ What I want to see:

partition strategy documented

good key distribution (avoid low-cardinality keys)

load testing done before go-live

Kafka scaling is limited by partitioning — not hope.

6) Elasticsearch Readiness: Are You Forcing ES to Be a Buffer?

A lot of pipelines fail because Elasticsearch is treated like a database + queue + buffer + compute engine.

🚩 Red flags:

ES used as a buffer

default refresh during heavy ingestion

random shard counts

no ILM

✅ What I want to see:

bulk indexing

refresh interval tuned for ingestion

shard sizing planned

ILM defined early

Search engines should search. Kafka should buffer.

7) Observability: Can You Debug This in 5 Minutes?

When something goes wrong, the worst feeling is:

“Where do we even start looking?”

🚩 Red flags:

“we’ll check logs”

no lag dashboards

no indexing latency visibility

no end-to-end freshness tracking

✅ What I want to see:

consumer lag per partition

ingest rate vs processing rate

DLQ growth trends

ES indexing latency

“How late is the data?” metric (freshness SLA)

If you can’t see it, you can’t own it.

8) Operational Ownership: Who Gets Paged?

This is the leadership check.

🚩 Red flags:

no clear owner team

tribal knowledge

no runbooks

“ask that one guy”

✅ What I want to see:

clear on-call ownership

runbook + rollback plan

replay procedures documented

SLAs agreed and realistic

If nobody owns it… it will own you.

The Real Difference Between “Built” and “Production-Ready”

A pipeline isn’t production-ready because:

it runs in staging

it moves data

dashboards look good today

A pipeline is production-ready when:

✅ it absorbs pressure
✅ it isolates failure
✅ it supports replay
✅ it stays debuggable under load
✅ it recovers predictably

That’s what senior engineers optimize for.

My Favorite Closing Question in Any Design Review

I always ask:

👉 “What breaks first… and how do we recover?”

If the answer is unclear…

the design isn’t done yet.
