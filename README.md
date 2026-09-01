# Blast-Radius Exposure Analysis for AI Agent Permission Graphs

A quantitative model for measuring how far a single compromised AI agent or
credential can spread through an organization's permission/trust graph —
and a concrete, tested correction to Meta's published "Rule of Two" agent
safety heuristic.

## Motivation

Current AI safety evaluation almost entirely measures *model behavior*
(red-team scores, capability evals). This project targets a different,
largely unmeasured axis: given that something goes wrong anyway, how far
does it spread through the surrounding system?

This is directly motivated by a real incident: an OpenAI red-team agent
running a benchmark escalated from one compromised worker machine to admin
access across a large part of Hugging Face's infrastructure in under 13
hours, using nothing but pre-existing permission misconfigurations.

## What this does

The script models an organization's agent/credential trust graph as a
network subject to a connectivity phase transition (percolation theory),
and computes:

- **S(p)**: the expected "blast radius" — the fraction of the org reachable
  from one randomly compromised node, as a function of connectivity density.
- **Critical density (p_c)**: the connectivity level at which blast radius
  crosses 50% of the organization.
- **Growth sharpness (beta)**: how abruptly the system flips from mostly
  safe to mostly exposed near that threshold.

Four graph structures are compared:

| Structure | Description |
|---|---|
| Random baseline | Uniform random trust edges (control) |
| Hub-based | Scale-free graph with admin/shared-credential hubs, matching real org structure |
| Rule-of-Two, pairwise | Meta's heuristic enforced only on direct edges (as commonly implemented) |
| Rule-of-Two, transitive | Corrected version: enforced across full delegation chains via union-find |

## Key finding

The pairwise version of the Rule of Two performs **statistically
identically to having no rule at all** — both reach ~100% blast radius at
the same critical density. The transitive version structurally caps
exposure at ~34%, with no phase transition observed in the tested range.
This means the heuristic, as typically described, only works if enforced
on entire reachability chains, not individual connections.

## Usage

```bash
pip install networkx numpy matplotlib
python3 blast_radius_percolation.py
```

Outputs:
- `blast_radius_percolation.png` — comparison plot across all four structures
- `blast_radius_report.md` — plain-language engineering summary (critical
  density, max exposure, growth sharpness per structure)

## Files

- `blast_radius_percolation.py` — full simulation, analysis, and plotting code
- `blast_radius_percolation.png` — result plot
- `blast_radius_report.md` — generated summary report

## Status

Validated on synthetic graphs (300 nodes, 40 Monte Carlo trials per density
point). Next step: validation against realistic org-scale permission graphs
(5,000+ nodes) and formal derivation of the critical growth-exponent
behavior.

## Author

Saravana Prakash Thirumuruganandham
[LinkedIn](https://www.linkedin.com/in/sthirumuruganandham/)

## 📜 Licensing & Commercial Options

This project is open-source under the **GNU Affero General Public License v3.0 (AGPLv3)**. 

### Enterprise Commercial Licensing
If you wish to integrate this transitive reachability model, percolation audit algorithms, or guardrail tools into closed-source, proprietary software (such as commercial SaaS products, internal enterprise IAM scanners, or proprietary agent orchestration engines) without AGPLv3 copyleft obligations:

* **Commercial Licenses:** Custom enterprise licensing is available to bypass AGPLv3 restrictions.
* **Security & Permission Audits:** Custom graph-percolation risk analysis, scaling simulations (up to 20,000+ nodes), and CI/CD audit tool integration for enterprise multi-agent networks (AWS IAM, Okta, LangGraph, AutoGen, CrewAI).

For commercial licensing, enterprise pilots, or consulting inquiries, please contact:
* **Contact Email:** `saravprak@googlemail.com`
* **LinkedIn:** [Saravana Prakash Thirumuruganandham](https://www.linkedin.com/in/sthirumuruganandham/)
