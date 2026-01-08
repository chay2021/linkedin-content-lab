# Designing Elasticsearch Indexes for High Write Throughput

👉 Ever had Elasticsearch indexing work flawlessly in dev… and then fall apart in production?

Nodes are green. CPU looks okay. Yet indexing slows, dashboards lag, and write rejections start appearing.

This usually isn’t a hardware problem. 👉 It’s an index design problem — made long before scale arrived.

A Setup You’ve Definitely Built
App / Logs → Kafka → Consumer → Elasticsearch → Dashboards

At first: • Traffic is low • Writes are fast • Dashboards feel real-time

Confidence is high.

Then adoption grows: • 10× write volume • Heap pressure spikes • Indexing backs up • Requests get rejected

And someone asks:

“Why is Elasticsearch suddenly slow?”

This is where assumptions break.

The Core Misunderstanding
Most teams assume:

“Elasticsearch write problems mean we need bigger machines.”

In reality: 👉 Most write bottlenecks come from index design choices made months earlier.

And once traffic grows, those choices become very expensive.

What We Think Helps vs What Actually Helps
What we think • More shards = more throughput • Default refresh is fine • Daily indices scale well • Replicas don’t affect writes • We’ll tune later

What actually happens • Too many shards kill throughput • Refreshes steal indexing capacity • Small indices waste heap • Replicas multiply every write • Late tuning causes outages

1️⃣ Shards: The Most Expensive Decision
Each shard is: • A Lucene index • With its own memory, segments, merges

Too many shards means: • High heap usage • More GC • Slower writes

👉 Oversharding hurts more than undersharding at scale.

Rule that actually works: • Target 20–50 GB per shard • Fewer, larger shards > many tiny shards • You can add nodes later — you can’t merge shards

2️⃣ Refresh Interval: The Silent Throughput Killer
Every refresh: • Creates new segments • Triggers background work • Competes with indexing

At high write rates: 👉 Frequent refreshes choke throughput.

What real pipelines do: • Increase refresh to 30–60s • Disable refresh during bulk loads • Accept slightly stale dashboards for stability

Near-real-time ≠ every second.

3️⃣ Replicas: Writes Are Multiplied
Replicas aren’t free.

• 1 replica = 2 writes • 2 replicas = 3 writes

At scale, replicas: • Cut effective write throughput • Increase disk + network pressure

Common production pattern • Heavy ingestion → replicas = 0 • After ingestion → replicas increased • Kafka protects data, not ES replicas

4️⃣ ILM: Performance Over Time
Without ILM: • Old indices stay hot • Heap usage grows • Cluster metadata explodes • Everything slowly degrades

ILM isn’t about storage. 👉 It’s about keeping the cluster healthy as it ages.

Mature setups use: • Hot → warm/cold phases • Rollover by size • Automated deletion

The Real Lesson
Elasticsearch write performance is not about: • Faster CPUs • Bigger nodes • JVM flags alone

It’s about: 👉 Making fewer Lucene indexes do more work.

Once traffic grows, index design becomes destiny.

💡 Elasticsearch doesn’t fail loudly. It fails slowly — because of earlier decisions.

👉 Which index choice hurt you the most: shards, refresh, replicas, or ILM? 

👇 Share your war stories.
