# Your Kubernetes Probes Might Be Causing Your Outages.


👉 If you think liveness/readiness probes are “just best practice”… you might be the reason your production pipeline keeps restarting.

Yes — I said it.

Because the fastest way to turn a healthy system into a disaster is:

Kill it repeatedly while it’s recovering.


A very real day-to-day failure
Your pipeline is simple:

Kafka → Consumers (K8s) → Elasticsearch → Dashboards

Elasticsearch slows down for 2 minutes (merges, GC, burst traffic). Your consumer starts taking longer to process.

Then Kubernetes says:

✅ “Probe failed.” 

💥 “Restart pod.” 

♻️ Consumer group rebalances. 

📈 Lag spikes harder. 

💥 More probe failures. 

🔁 Restart storm.

Kafka isn’t down. Your pods are being executed on a schedule.


What we think probes do
❌ What we think
“Probes detect failure and heal the app.”

✅ What they actually do
“Probes decide when to kill your app.”

And if you misconfigure them, Kubernetes becomes your most aggressive attacker.


The intelligence test
If your consumer is slow because the sink is slow…

👉 Should the fix be “restart it”?

Or should the fix be:

backpressure

timeouts

retries with delay

throttling

letting it drain safely

If your answer is “restart”… you’re treating symptoms with a shotgun.


One line you should remember
Readiness = “Don’t send traffic yet.” Liveness = “Kill it.”

If you confuse the two, you don’t have resilience. You have roulette.


👇 Hot take: Have you ever seen a “probe configuration” create a bigger outage than the actual issue?

Experienced engineers — I know you’ve seen this.
