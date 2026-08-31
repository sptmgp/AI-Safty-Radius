# Five Additional Applications: Results Summary

| # | Application | Critical threshold | Key result |
|---|---|---|---|
| 1 | Prompt-injection contagion (agent mesh) | density ~0.0083 | Injection reaches 50%+ of a 250-agent mesh once agents read each other's outputs at this density |
| 2 | Poisoned RAG document spread | density ~0.0172 | One poisoned document exposes over half of downstream agents sharing a retrieval index at this overlap level |
| 3 | Faulty rollout propagation | density ~0.0086 | A single bad deployment reaches 50%+ of dependent services at this dependency density |
| 4 | Credential rotation vs. spread race | safe interval ~9 steps | Rotating credentials before this interval keeps expected exposure under 50% |
| 5 | Early-warning for capability jumps | lead time ~137 steps | Rolling variance crosses 2x baseline this many steps before the capability jump itself is visible |

## How each helps AI safety

**1. Prompt-injection contagion.** Multi-agent systems where agents read
each other's tool outputs, summaries, or scratchpads are vulnerable to
injected instructions spreading silently, exactly like the permission-graph
blast radius but through *information* edges rather than *credential*
edges. This gives teams a way to test agent architectures pre-deployment:
compute the injection-contagion threshold for a proposed multi-agent
design and see whether it sits dangerously close to full-mesh contagion.

**2. Poisoned RAG document spread.** Products that share a retrieval
backend (common in platform companies serving many downstream apps from
one knowledge base) inherit each other's poisoning risk. This quantifies
how much retrieval overlap is safe to share across products before one
poisoned document becomes a cross-product incident, informing whether
retrieval indices should be segmented per product.

**3. Faulty rollout propagation.** Internal service dependency graphs
(model A's output feeds model B, which feeds model C) can silently spread
a regressed or unsafe update. This gives a way to compute, before a
rollout, how many services a bad deployment would reach given the current
dependency structure -- turning "how risky is this rollout" into a number
instead of a guess.

**4. Rotation vs. spread race.** Ties the growth-sharpness result from the
base blast-radius model to a concrete operational policy: how often
credentials need to rotate to stay ahead of a compromise's expected
spread rate. This converts "rotate credentials regularly" (vague) into
"rotate within N days for this specific graph structure" (specific,
auditable).

**5. Early-warning for capability jumps.** Applies the well-established
"critical slowing down" signal (rising variance before a system crosses a
tipping point) to a toy capability-metric trajectory. In this
demonstration, the warning signal crosses threshold 137
steps before the capability jump is visible in the metric itself --
suggesting an early-warning monitor could flag an approaching emergent
capability before it fully appears, giving more lead time for evaluation
and safety review than waiting for the capability to show up in
benchmarks directly.
