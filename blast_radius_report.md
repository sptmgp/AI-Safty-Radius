# Blast-Radius Exposure Analysis: Summary Report

This report summarizes a quantitative analysis of how far a single compromised credential or agent can spread through an organization's permission graph, under four different graph structures.

## Results

| Graph structure | Critical density p_c | Max blast radius observed | Local growth sharpness (beta) |
|---|---|---|---|
| Random baseline (uniform trust graph) | 0.0068 | 1.000 | 0.14 |
| Hub-based (realistic org structure) | 0.0010 | 1.000 | n/a (no transition to fit) |
| Rule-of-Two, pairwise (as-published) | 0.0068 | 1.000 | 0.16 |
| Rule-of-Two, transitive (fixed) | not reached in tested range | 0.341 | n/a (no transition to fit) |

## Interpretation

- **Critical density (p_c)**: the connectivity level at which the expected blast radius crosses 50% of the organization. A lower p_c means the system becomes fully exposed at a lower level of interconnection -- i.e. less margin for error.
- **Max blast radius observed**: the worst-case expected exposure seen anywhere in the tested density range. A structure that caps this well below 100% is providing a structural (not just probabilistic) limit on damage.
- **Growth sharpness (beta)**: how abruptly the system moves from 'mostly safe' to 'mostly exposed' as connectivity increases. A small beta indicates a brittle system where routine changes in connectivity (e.g. adding a new integration or shared credential) can cross the safe/unsafe boundary with little warning.
