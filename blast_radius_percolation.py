"""
Blast-Radius Percolation Model for AI Agent Permission Graphs
===============================================================

Method summary
--------------
This module treats an organization's AI-agent permission/trust graph as a
network subject to a connectivity phase transition, and asks a single
quantitative question:

    Given a graph where nodes are services/agents/credentials and edges are
    trust relations, how far does a single compromise spread, and is there
    a sharp threshold in connectivity density above which one bug reliably
    becomes an org-wide breach?

This is a standard application of percolation theory: as the density of
connections in a network increases, the expected size of the connected
region reachable from any one node does not grow smoothly -- it stays
small, then crosses a critical density and jumps to span nearly the whole
network. That critical density and the growth behavior around it are
measurable, reproducible properties of the graph's structure, independent
of which specific node initiates the compromise.

Graph structures compared
--------------------------
1. Erdos-Renyi (ER)        - baseline: uniform random trust edges.
2. Scale-free (BA)         - more realistic for real orgs: a few
                              highly-connected "admin" nodes (hubs), like
                              the shared credentials/admin systems that let
                              the Hugging Face incident escalate from one
                              worker machine to org-wide admin access in
                              under 13 hours.
3. Rule-of-Two constrained  - Meta's heuristic (an agent gets at most 2 of
                              {reads private data, reads outside text, can
                              send data out}) encoded structurally: edges are
                              only allowed between nodes whose combined
                              capability sets stay within the 2-of-3 limit.
4. Rule-of-Two, transitive  - the corrected version: the 2-of-3 cap is
                              enforced on the accumulated capability set of
                              an entire connected chain, not just each
                              direct edge.

Order parameter
----------------
S(p) = expected fraction of the graph reachable from a single randomly
compromised node (the "blast radius"). This is the standard percolation
order parameter (giant-component fraction), reported here as a directly
interpretable engineering quantity: the expected proportion of an
organization's systems exposed by one compromised credential.

Reproducibility note
---------------------
All quantities below (S(p), the critical density p_c, and the local growth
exponent near p_c) are computed directly from the graphs in this script --
nothing is asserted without a corresponding simulation run.
"""

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor
import random

N_NODES = 300          # size of the simulated org's permission graph
N_TRIALS = 40           # Monte Carlo trials per density point
P_VALUES = np.linspace(0.001, 0.05, 35)  # edge density sweep


def giant_component_fraction(G):
    """Order parameter S: fraction of nodes in the largest connected component."""
    if G.number_of_nodes() == 0:
        return 0.0
    largest_cc = max(nx.connected_components(G), key=len)
    return len(largest_cc) / G.number_of_nodes()


def blast_radius_from_random_node(G, n_samples=20):
    """Alternative order parameter: avg. fraction reachable from a RANDOM
    single compromised node (closer to 'one bug becomes how much damage'
    than the giant component alone)."""
    nodes = list(G.nodes())
    if not nodes:
        return 0.0
    sample = random.sample(nodes, min(n_samples, len(nodes)))
    fractions = []
    for start in sample:
        reachable = nx.node_connected_component(G, start)
        fractions.append(len(reachable) / G.number_of_nodes())
    return float(np.mean(fractions))


def simulate_er(p, n=N_NODES, trials=N_TRIALS):
    vals = []
    for _ in range(trials):
        G = nx.erdos_renyi_graph(n, p)
        vals.append(blast_radius_from_random_node(G))
    return np.mean(vals), np.std(vals)


def simulate_ba(p, n=N_NODES, trials=N_TRIALS):
    """Scale-free graph: m (edges per new node) chosen so mean degree
    roughly matches the ER graph at the same nominal density p, so the two
    are comparable on the x-axis. Represents orgs with hub-like admin
    systems / shared credentials."""
    mean_degree_target = p * (n - 1)
    m = max(1, int(round(mean_degree_target / 2)))
    vals = []
    for _ in range(trials):
        G = nx.barabasi_albert_graph(n, m)
        vals.append(blast_radius_from_random_node(G))
    return np.mean(vals), np.std(vals)


def simulate_rule_of_two(p, n=N_NODES, trials=N_TRIALS):
    """Encode the Rule of Two structurally. Each node is randomly assigned
    a subset of capabilities from {reads_private, reads_outside, sends_out}
    with at most 2 (as the rule mandates). An edge (trust relation, i.e. a
    path a compromise can travel along) is only permitted between two nodes
    if the UNION of their capabilities still has size <= 2 -- i.e. connecting
    them would not create a node effectively holding all three capabilities
    through delegation. This is a structural cap on how much the graph is
    ALLOWED to connect, not just a random graph at the same density."""
    caps_options = [
        {"reads_private", "reads_outside"},
        {"reads_private", "sends_out"},
        {"reads_outside", "sends_out"},
        {"reads_private"},
        {"reads_outside"},
        {"sends_out"},
    ]
    vals = []
    for _ in range(trials):
        G = nx.Graph()
        G.add_nodes_from(range(n))
        caps = {i: random.choice(caps_options) for i in range(n)}
        # candidate edges drawn like ER at density p, but rejected if they'd
        # violate the rule-of-two cap on the union of capabilities
        n_candidates = int(p * n * (n - 1) / 2)
        possible_pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        random.shuffle(possible_pairs)
        added = 0
        for (i, j) in possible_pairs:
            if added >= n_candidates:
                break
            if len(caps[i] | caps[j]) <= 2:
                G.add_edge(i, j)
                added += 1
        vals.append(blast_radius_from_random_node(G))
    return np.mean(vals), np.std(vals)


def simulate_rule_of_two_transitive(p, n=N_NODES, trials=N_TRIALS):
    """Transitive version of the Rule of Two. An edge is rejected not just
    if the two endpoints' own capabilities exceed 2-of-3, but if adding it
    would create ANY connected component (reachable set) whose UNION of
    capabilities across all member nodes exceeds 2-of-3. This is the
    'enforce it on paths, not just edges' fix implied by the pairwise
    result: a compromise chain that walks A(reads_private) -> B -> C(sends_out)
    is just as dangerous as a single node holding both capabilities.

    Implementation: maintain each component's accumulated capability union
    via union-find bookkeeping; reject an edge if merging the two
    components' capability unions would exceed size 2.
    """
    caps_options = [
        {"reads_private", "reads_outside"},
        {"reads_private", "sends_out"},
        {"reads_outside", "sends_out"},
        {"reads_private"},
        {"reads_outside"},
        {"sends_out"},
    ]
    vals = []
    for _ in range(trials):
        G = nx.Graph()
        G.add_nodes_from(range(n))
        caps = {i: random.choice(caps_options) for i in range(n)}
        # component_caps[root] = accumulated capability union for that component
        parent = {i: i for i in range(n)}
        component_caps = {i: set(caps[i]) for i in range(n)}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        n_candidates = int(p * n * (n - 1) / 2)
        possible_pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        random.shuffle(possible_pairs)
        added = 0
        for (i, j) in possible_pairs:
            if added >= n_candidates:
                break
            ri, rj = find(i), find(j)
            if ri == rj:
                continue  # already in same component, edge would add no new capability spread
            merged = component_caps[ri] | component_caps[rj]
            if len(merged) <= 2:
                G.add_edge(i, j)
                parent[ri] = rj
                component_caps[rj] = merged
                added += 1
        vals.append(blast_radius_from_random_node(G))
    return np.mean(vals), np.std(vals)


def run_sweep(sim_fn):
    means, stds = [], []
    for p in P_VALUES:
        m, s = sim_fn(p)
        means.append(m)
        stds.append(s)
    return np.array(means), np.array(stds)


def estimate_critical_threshold(p_values, means, target=0.5):
    """Numeric estimate of p_c: first density at which the blast
    radius crosses `target` fraction of the org."""
    above = np.where(means >= target)[0]
    if len(above) == 0:
        return None
    idx = above[0]
    return p_values[idx]


def estimate_growth_exponent(p_values, means, p_c, window=4):
    """Estimate how sharply the order parameter grows near the critical
    density, by fitting S(p) ~ (p - p_c)^beta on a small window of points
    just above p_c using a log-log linear regression.

    This 'beta' is a standard way to characterize the *sharpness* of a
    connectivity transition: a small beta means the system flips from safe
    to fully exposed over a very narrow range of connectivity changes (a
    brittle system), while a larger beta means the transition is more
    gradual (a more forgiving system, easier to catch mid-transition via
    monitoring).

    Returns None if there isn't a clean transition to fit (e.g. the
    transitive Rule-of-Two case, which never reaches the target and has no
    well-defined p_c).
    """
    if p_c is None:
        return None
    idx_c = np.searchsorted(p_values, p_c)
    idx_end = min(idx_c + window, len(p_values))
    p_window = p_values[idx_c:idx_end]
    s_window = means[idx_c:idx_end]

    # only keep points where the order parameter is in (0, 1) and p > p_c,
    # since log-log fitting requires strictly positive values
    mask = (s_window > 1e-6) & (s_window < 0.999) & (p_window > p_c)
    if mask.sum() < 2:
        return None

    log_dp = np.log(p_window[mask] - p_c)
    log_s = np.log(s_window[mask])
    beta, _intercept = np.polyfit(log_dp, log_s, 1)
    return float(beta)


def write_engineering_report(results, path='/home/claude/blast_radius_report.md'):
    """Produce a plain-language, engineering-facing summary of the
    quantitative results, separate from the raw plot, so the findings are
    usable by a security/safety reviewer without needing to read the code
    or re-derive the statistics themselves."""
    lines = []
    lines.append("# Blast-Radius Exposure Analysis: Summary Report\n")
    lines.append(
        "This report summarizes a quantitative analysis of how far a single "
        "compromised credential or agent can spread through an "
        "organization's permission graph, under four different graph "
        "structures.\n"
    )
    lines.append("## Results\n")
    lines.append("| Graph structure | Critical density p_c | Max blast radius observed | Local growth sharpness (beta) |")
    lines.append("|---|---|---|---|")
    for name, (pc, max_s, beta) in results.items():
        pc_str = f"{pc:.4f}" if pc is not None else "not reached in tested range"
        beta_str = f"{beta:.2f}" if beta is not None else "n/a (no transition to fit)"
        lines.append(f"| {name} | {pc_str} | {max_s:.3f} | {beta_str} |")

    lines.append("\n## Interpretation\n")
    lines.append(
        "- **Critical density (p_c)**: the connectivity level at which the "
        "expected blast radius crosses 50% of the organization. A lower "
        "p_c means the system becomes fully exposed at a lower level of "
        "interconnection -- i.e. less margin for error.\n"
        "- **Max blast radius observed**: the worst-case expected exposure "
        "seen anywhere in the tested density range. A structure that caps "
        "this well below 100% is providing a structural (not just "
        "probabilistic) limit on damage.\n"
        "- **Growth sharpness (beta)**: how abruptly the system moves from "
        "'mostly safe' to 'mostly exposed' as connectivity increases. A "
        "small beta indicates a brittle system where routine changes in "
        "connectivity (e.g. adding a new integration or shared credential) "
        "can cross the safe/unsafe boundary with little warning.\n"
    )
    with open(path, 'w') as f:
        f.write('\n'.join(lines))
    return path


if __name__ == "__main__":
    print("Running percolation sweeps (this simulates ~3*35*40 graphs)...")

    er_means, er_stds = run_sweep(simulate_er)
    ba_means, ba_stds = run_sweep(simulate_ba)
    r2_means, r2_stds = run_sweep(simulate_rule_of_two)
    r2t_means, r2t_stds = run_sweep(simulate_rule_of_two_transitive)

    pc_er = estimate_critical_threshold(P_VALUES, er_means)
    pc_ba = estimate_critical_threshold(P_VALUES, ba_means)
    pc_r2 = estimate_critical_threshold(P_VALUES, r2_means)
    pc_r2t = estimate_critical_threshold(P_VALUES, r2t_means)

    beta_er = estimate_growth_exponent(P_VALUES, er_means, pc_er)
    beta_ba = estimate_growth_exponent(P_VALUES, ba_means, pc_ba)
    beta_r2 = estimate_growth_exponent(P_VALUES, r2_means, pc_r2)
    beta_r2t = estimate_growth_exponent(P_VALUES, r2t_means, pc_r2t)

    print("Estimated critical density (50% blast radius) and growth sharpness:")
    print(f"  Random baseline (uniform trust graph):   p_c ~ {pc_er}, beta ~ {beta_er}")
    print(f"  Hub-based (realistic org structure):     p_c ~ {pc_ba}, beta ~ {beta_ba}")
    print(f"  Rule-of-Two, pairwise (as-published):    p_c ~ {pc_r2}, beta ~ {beta_r2}")
    print(f"  Rule-of-Two, transitive (fixed):         p_c ~ {pc_r2t}, beta ~ {beta_r2t}")
    print(f"  Max blast radius reached by transitive version: {r2t_means.max():.3f}")

    report_results = {
        "Random baseline (uniform trust graph)": (pc_er, er_means.max(), beta_er),
        "Hub-based (realistic org structure)": (pc_ba, ba_means.max(), beta_ba),
        "Rule-of-Two, pairwise (as-published)": (pc_r2, r2_means.max(), beta_r2),
        "Rule-of-Two, transitive (fixed)": (pc_r2t, r2t_means.max(), beta_r2t),
    }
    report_path = write_engineering_report(report_results)
    print(f"Saved engineering summary report to {report_path}")

    # ---- Plot ----
    fig, ax = plt.subplots(figsize=(9, 6))

    ax.plot(P_VALUES, er_means, marker='o', label='Random baseline (uniform trust graph)', color='#4C72B0')
    ax.fill_between(P_VALUES, er_means - er_stds, er_means + er_stds, alpha=0.15, color='#4C72B0')

    ax.plot(P_VALUES, ba_means, marker='s', label='Hub-based (realistic org structure)', color='#C44E52')
    ax.fill_between(P_VALUES, ba_means - ba_stds, ba_means + ba_stds, alpha=0.15, color='#C44E52')

    ax.plot(P_VALUES, r2_means, marker='^', label="Rule-of-Two, pairwise (as-published)", color='#55A868')
    ax.fill_between(P_VALUES, r2_means - r2_stds, r2_means + r2_stds, alpha=0.15, color='#55A868')

    ax.plot(P_VALUES, r2t_means, marker='D', label="Rule-of-Two, transitive (fixed)", color='#8172B2')
    ax.fill_between(P_VALUES, r2t_means - r2t_stds, r2t_means + r2t_stds, alpha=0.15, color='#8172B2')

    ax.axhline(0.5, color='gray', linestyle='--', linewidth=1, label='50% blast radius threshold')

    ax.set_xlabel('Connectivity density p (avg. trust connections per node, normalized)')
    ax.set_ylabel('Expected blast radius S(p)\n(fraction of org reachable from 1 compromised node)')
    ax.set_title('Blast-Radius Exposure Across Permission-Graph Structures')
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig('/home/claude/blast_radius_percolation.png', dpi=150)
    print("Saved plot to blast_radius_percolation.png")
