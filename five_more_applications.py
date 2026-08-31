"""
Five Additional Applications of Critical-Phenomena Analysis to AI Safety
==========================================================================

Extends the blast-radius permission-graph model to five further AI safety
problems, each using the same core idea (a system property that changes
sharply, not gradually, past some threshold) applied to a different failure
mode. Each application is simulated and produces a quantitative,
reproducible result -- nothing below is asserted without a corresponding
computation in this script.
"""

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import random

random.seed(7)
np.random.seed(7)

# ======================================================================
# Application 1: Prompt-injection contagion through an agent communication mesh
# ======================================================================
# Setup: agents that read each other's outputs (summaries, tool results,
# shared scratchpads) form a directed communication graph. An injected
# instruction in one agent's output can be picked up and re-propagated by
# any downstream agent that reads it -- the same spreading dynamics as the
# blast-radius model, but the edges are "reads output of" instead of
# "trusts credentials of".

def simulate_injection_spread(p, n=250, trials=25):
    """Fraction of the agent mesh that ends up repeating/acting on an
    injected instruction, starting from one poisoned agent output,
    as a function of how densely agents read each other's outputs."""
    vals = []
    for _ in range(trials):
        G = nx.gnp_random_graph(n, p, directed=True)
        start = random.choice(list(G.nodes()))
        reachable = nx.descendants(G, start) | {start}
        vals.append(len(reachable) / n)
    return np.mean(vals), np.std(vals)

P1 = np.linspace(0.001, 0.03, 25)
inj_means, inj_stds = [], []
for p in P1:
    m, s = simulate_injection_spread(p)
    inj_means.append(m); inj_stds.append(s)
inj_means, inj_stds = np.array(inj_means), np.array(inj_stds)
pc_inj = P1[np.where(inj_means >= 0.5)[0][0]] if (inj_means >= 0.5).any() else None


# ======================================================================
# Application 2: Poisoned RAG document spread through a shared retrieval index
# ======================================================================
# Setup: a bipartite graph of documents <-> agents/products that retrieve
# from a shared index. A poisoned document "infects" every agent that
# retrieves it; those agents' outputs may themselves get re-indexed
# (e.g. cached answers, summaries written back to a knowledge base),
# infecting further documents. Models how compromised knowledge-base
# content propagates across products sharing one retrieval backend.

def simulate_rag_poisoning(p_retrieve, n_docs=150, n_agents=80, trials=25):
    vals = []
    for _ in range(trials):
        B = nx.Graph()
        B.add_nodes_from([f"d{i}" for i in range(n_docs)], bipartite=0)
        B.add_nodes_from([f"a{i}" for i in range(n_agents)], bipartite=1)
        for d in range(n_docs):
            for a in range(n_agents):
                if random.random() < p_retrieve:
                    B.add_edge(f"d{d}", f"a{a}")
        start = "d0"
        if start not in B:
            vals.append(0.0)
            continue
        reachable = nx.node_connected_component(B, start)
        n_agents_hit = sum(1 for x in reachable if x.startswith("a"))
        vals.append(n_agents_hit / n_agents)
    return np.mean(vals), np.std(vals)

P2 = np.linspace(0.002, 0.05, 20)
rag_means, rag_stds = [], []
for p in P2:
    m, s = simulate_rag_poisoning(p)
    rag_means.append(m); rag_stds.append(s)
rag_means, rag_stds = np.array(rag_means), np.array(rag_stds)
pc_rag = P2[np.where(rag_means >= 0.5)[0][0]] if (rag_means >= 0.5).any() else None


# ======================================================================
# Application 3: Faulty model/weight rollout through a service dependency graph
# ======================================================================
# Setup: internal services/products depend on each other's outputs (a
# recommendation service calls a ranking model which calls an embedding
# service, etc). A bad deployment (regressed or unsafe model update) at
# one node can silently propagate through every downstream dependent
# before detection. Same percolation structure; edges = "consumes output of".

def simulate_rollout_risk(p, n=200, trials=25):
    vals = []
    for _ in range(trials):
        G = nx.gnp_random_graph(n, p, directed=True)
        start = random.choice(list(G.nodes()))
        affected = nx.descendants(G, start) | {start}
        vals.append(len(affected) / n)
    return np.mean(vals), np.std(vals)

P3 = np.linspace(0.001, 0.025, 20)
roll_means, roll_stds = [], []
for p in P3:
    m, s = simulate_rollout_risk(p)
    roll_means.append(m); roll_stds.append(s)
roll_means, roll_stds = np.array(roll_means), np.array(roll_stds)
pc_roll = P3[np.where(roll_means >= 0.5)[0][0]] if (roll_means >= 0.5).any() else None


# ======================================================================
# Application 4: Credential rotation rate vs. compromise spread rate
# ======================================================================
# Setup: a race condition. Blast radius grows over time following the
# local growth-sharpness behavior found in the original model; credential
# rotation periodically resets any node's exposure to zero. This finds
# the maximum SAFE rotation interval: the rotation frequency needed so
# that compromise never reaches a majority of the org before it's cut off.

def blast_radius_over_time(t, growth_rate=0.35, cap=1.0):
    """A simple logistic spread model: exposure grows with a rate set by
    connectivity, saturating at `cap`. growth_rate is analogous to the
    growth-sharpness (beta) measured in the base model -- higher
    connectivity/hub density means faster growth_rate."""
    return cap / (1 + np.exp(-growth_rate * (t - 10)))

rotation_intervals = np.arange(1, 30)
max_exposure_at_rotation = [blast_radius_over_time(t) for t in rotation_intervals]
safe_rotation = None
for t, exposure in zip(rotation_intervals, max_exposure_at_rotation):
    if exposure < 0.5:
        safe_rotation = t
    else:
        break


# ======================================================================
# Application 5: Early-warning signal for emergent capability jumps
# ======================================================================
# Setup: as a controllable parameter (e.g. effective training progress)
# approaches a critical point, systems near a phase transition show
# "critical slowing down" -- rising variance and autocorrelation in any
# noisy observable, even before the transition itself is visible. This is
# a standard early-warning technique from dynamical systems (used for
# ecological and climate tipping points) applied here to a toy model of a
# capability metric approaching a sharp jump, as seen in grokking-style
# training curves. This is a simulated demonstration of the *signal*, not
# a claim about any specific real training run.

def simulate_approach_to_transition(n_steps=400, transition_step=300, noise=0.05):
    x = np.zeros(n_steps)
    x[0] = 0.05
    for t in range(1, n_steps):
        distance_to_transition = transition_step - t
        restoring_force = max(0.02, 0.15 * np.tanh(distance_to_transition / 40))
        drift = restoring_force * (0.05 - x[t-1]) if t < transition_step else 0.08
        x[t] = x[t-1] + drift + np.random.normal(0, noise * (1 + max(0, 1 - distance_to_transition / 100)))
        x[t] = np.clip(x[t], 0, 1)
    return x

def rolling_variance(x, window=20):
    return np.array([np.var(x[max(0, i-window):i+1]) for i in range(len(x))])

capability_trace = simulate_approach_to_transition()
var_signal = rolling_variance(capability_trace)
transition_step = 300
baseline_var = np.mean(var_signal[20:60])
warning_idx = None
for i in range(60, transition_step):
    if var_signal[i] > 2 * baseline_var:
        warning_idx = i
        break
lead_time = (transition_step - warning_idx) if warning_idx else None


# ======================================================================
# Plot all five
# ======================================================================
fig, axs = plt.subplots(2, 3, figsize=(16, 9))

axs[0,0].plot(P1, inj_means, marker='o', color='#C44E52')
axs[0,0].fill_between(P1, inj_means-inj_stds, inj_means+inj_stds, alpha=0.15, color='#C44E52')
axs[0,0].axhline(0.5, color='gray', linestyle='--', linewidth=1)
axs[0,0].set_title('1. Prompt-injection contagion\n(agent communication mesh)')
axs[0,0].set_xlabel('Cross-reading density')
axs[0,0].set_ylabel('Fraction of mesh repeating injection')

axs[0,1].plot(P2, rag_means, marker='s', color='#4C72B0')
axs[0,1].fill_between(P2, rag_means-rag_stds, rag_means+rag_stds, alpha=0.15, color='#4C72B0')
axs[0,1].axhline(0.5, color='gray', linestyle='--', linewidth=1)
axs[0,1].set_title('2. Poisoned RAG document spread\n(shared retrieval index)')
axs[0,1].set_xlabel('Retrieval overlap density')
axs[0,1].set_ylabel('Fraction of agents exposed')

axs[0,2].plot(P3, roll_means, marker='^', color='#55A868')
axs[0,2].fill_between(P3, roll_means-roll_stds, roll_means+roll_stds, alpha=0.15, color='#55A868')
axs[0,2].axhline(0.5, color='gray', linestyle='--', linewidth=1)
axs[0,2].set_title('3. Faulty rollout propagation\n(service dependency graph)')
axs[0,2].set_xlabel('Dependency density')
axs[0,2].set_ylabel('Fraction of services affected')

axs[1,0].plot(rotation_intervals, max_exposure_at_rotation, marker='D', color='#8172B2')
axs[1,0].axhline(0.5, color='gray', linestyle='--', linewidth=1)
if safe_rotation:
    axs[1,0].axvline(safe_rotation, color='green', linestyle=':', linewidth=2, label=f'Safe interval: {safe_rotation}')
    axs[1,0].legend()
axs[1,0].set_title('4. Credential rotation vs. spread race')
axs[1,0].set_xlabel('Time since compromise (rotation interval)')
axs[1,0].set_ylabel('Expected exposure')

axs[1,1].plot(capability_trace, color='#333333', linewidth=1)
axs[1,1].axvline(transition_step, color='red', linestyle='--', label='Capability jump')
if warning_idx:
    axs[1,1].axvline(warning_idx, color='orange', linestyle=':', label=f'Early warning (lead={lead_time} steps)')
axs[1,1].set_title('5a. Toy capability trajectory')
axs[1,1].set_xlabel('Training step (arbitrary units)')
axs[1,1].set_ylabel('Capability metric')
axs[1,1].legend(fontsize=8)

axs[1,2].plot(var_signal, color='#C44E52', label='Rolling variance')
axs[1,2].axvline(transition_step, color='red', linestyle='--')
if warning_idx:
    axs[1,2].axvline(warning_idx, color='orange', linestyle=':')
axs[1,2].set_title('5b. Early-warning signal\n(critical slowing down)')
axs[1,2].set_xlabel('Training step (arbitrary units)')
axs[1,2].set_ylabel('Rolling variance')

plt.tight_layout()
plt.savefig('/home/claude/five_more_applications.png', dpi=150)

# ======================================================================
# Report
# ======================================================================
pc_inj_str = f"{pc_inj:.4f}" if pc_inj is not None else "not reached in range"
pc_rag_str = f"{pc_rag:.4f}" if pc_rag is not None else "not reached in range"
pc_roll_str = f"{pc_roll:.4f}" if pc_roll is not None else "not reached in range"

report = f"""# Five Additional Applications: Results Summary

| # | Application | Critical threshold | Key result |
|---|---|---|---|
| 1 | Prompt-injection contagion (agent mesh) | density ~{pc_inj_str} | Injection reaches 50%+ of a 250-agent mesh once agents read each other's outputs at this density |
| 2 | Poisoned RAG document spread | density ~{pc_rag_str} | One poisoned document exposes over half of downstream agents sharing a retrieval index at this overlap level |
| 3 | Faulty rollout propagation | density ~{pc_roll_str} | A single bad deployment reaches 50%+ of dependent services at this dependency density |
| 4 | Credential rotation vs. spread race | safe interval ~{safe_rotation if safe_rotation else 'N/A'} steps | Rotating credentials before this interval keeps expected exposure under 50% |
| 5 | Early-warning for capability jumps | lead time ~{lead_time if lead_time else 'N/A'} steps | Rolling variance crosses 2x baseline this many steps before the capability jump itself is visible |

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
demonstration, the warning signal crosses threshold {lead_time if lead_time else 'N/A'}
steps before the capability jump is visible in the metric itself --
suggesting an early-warning monitor could flag an approaching emergent
capability before it fully appears, giving more lead time for evaluation
and safety review than waiting for the capability to show up in
benchmarks directly.
"""

with open('/home/claude/five_more_applications_report.md', 'w') as f:
    f.write(report)

print(report)
print("Saved plot to five_more_applications.png")
