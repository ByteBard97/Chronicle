---
date: 2026-08-20
sources:
  - "research/game-scale-social-simulation-literature.md (originally: Social Simulation Literature for Game-Scale Belief Systems)"
topic: "Social simulation literature v2 — implementable specification"
status: filed
---

# Social simulation literature v2 — implementable specification

A second, deeper pass over the same territory as report 02, going past
survey into an implementable specification. Full citation list (68
references) preserved in the source file at
`research/game-scale-social-simulation-literature.md` — this filing
extracts what's load-bearing for Chronicle's schema and build order rather
than reproducing every citation.

## Findings

- **[DESIGN-INPUT, decisive] Five-layer data-ownership model** — canonical events → claims/variants → subjective beliefs → social state → narrative/query. Only the first layer is objective; everything else is observer-relative. Promoted to ADR-0006.
- **[RISK, decisive] The sparse-graph rule: never maintain or update a complete N×N social matrix.** A full graph over 1,000 NPCs is 999,000 ordered pairs. Evidence: Socialog's reported per-tick cost growing from ~15–25ms at 50 characters to ~600ms at 450 — the trap is easy-to-express pairwise rules evaluated over every pair, not model sophistication. City of Gangsters (~1,200 NPCs, sparse directed graph, logic-programmed inference, no complete matrix) is the closest shipped scale precedent and should be treated as a primary engineering source, not just an anecdote. Promoted to ADR-0006.
- **[DESIGN-INPUT, decisive] Observer-local reputation, never a global score.** Beta-distribution reputation `(alpha, beta)` per `(observer, subject, context)` tuple, with recency decay — cheap, probabilistically meaningful, and prevents the common design bug where one relationship score silently drives contradictory behaviors. Subjective logic `(belief, disbelief, uncertainty, base_rate)` is a stronger alternative where discounting testimony through an untrusted intermediary matters. Promoted to ADR-0006.
- **[DESIGN-INPUT, decisive] Inspectability is a schema-shaping requirement, not a UI afterthought.** Every derived social outcome must answer "who believes this, from what evidence, through whom, since when, and why has it changed" (the report's own worked example: "Mara refused Petyr because..." drills down through a favor record, a belief, its evidence chain, witness corroboration, and a face-threat score). This is exactly what `dashboard/`'s causality timeline (`docs/vision.md`) needs, and it constrains the schema from day one rather than being retrofitted. Promoted to ADR-0007.
- **[BUILD-ON] Deterministic, seeded mutation policy keyed to fuzzy-trace theory's verbatim/gist split.** High verbatim strength → exact retelling, contradiction rejection. High gist/low verbatim → category substitution, exaggeration, actor transfer. Weak source memory → source confusion. This is cheaper than probabilistic inference and produces inspectable explanations — matches and sharpens report 02's ACT-R/Generative-Agents memory-decay finding.
- **[BUILD-ON] Compact rumor state machine**: `unaware → heard → checking → believing → spreading / refuting`, with `dormant`/`reactivated` states (from SIHR's hibernation concept) and `forgotten`. Transition rules can incorporate Daley–Kendall redundancy and Maki–Thompson repeated-contact effects without adopting their differential-equation math — state-machine semantics over epidemic math, for interpretability.
- **[BUILD-ON] Obligations, grudges, and reputation kept as three separate typed record kinds**, never merged into one relationship score — `Obligation` (issuer/debtor/beneficiary/action/deadline/status/sanction), `Grudge` (holder/target/source_event/severity/emotional+evidentiary strength/forgiveness_threshold), `Reputation` (observer/subject/context/beta counts). CK3's hooks (favor/secret/debt/duty) map directly onto obligation records with an associated leverage mechanism.
- **[DESIGN-INPUT] LLM integration comes last, and only renders/summarizes grounded symbolic state — never writes it directly.** Independently confirms the staged plan from the hybrid-architecture reports (03). Paradise (Ensemble + GPT-3) is cited as the concrete cautionary postmortem: when both the symbolic model and the LLM can define social reality, they undermine each other — generated dialogue implies facts the symbolic engine never recorded, or over-constraining the model produces repetitive dialogue. Slice of Life's asymmetric boundary (symbolic state drives generation; generated language changes state only through explicit validated action outcomes) is the fix, and matches `docs/architecture.md`'s existing injection-seam design.
- **[BUILD-ON, new name] Gossamer's witness/reflection/propagation/decay gossip loop** is the strongest direct post-Talk-of-the-Town model and appears nowhere in report 02. Citation checked: Max Kreminski, "Toward Better Gossip Simulation in Emergent Narrative Systems," IEEE Conference on Games 2023 (PDF: mkremins.github.io/publications/Gossamer_CoG2023.pdf) — legitimate, peer-reviewed venue. Listed first in "build first," so it's load-bearing for the build order in `docs/architecture.md`.
- **[RISK] Common failure pattern across every shipped/prototype system surveyed**: failures are rarely a missing mathematical model — they come from poor legibility, unbounded state, irreversible social collapse, too many authored rules, all-pairs recomputation, or unclear ownership of truth. City of Gangsters' own postmortem (a companion paper to the sparse-graph one) adds: keep norms few, make actions reversible enough to avoid social death spirals, and keep individuals fungible so players have more than one path to a social goal.
- **[DEFER] Full norm emergence, general-purpose logic programming (Praxish/RePraxis), autoencoder anomaly detection, prospective drama management** — all explicitly deferred by the source report's own build order, consistent with `docs/decisions/open-questions.md`'s existing economy-tier deferral pattern.

## Data ownership layers (as given in the source report)

1. **Canonical event log** — append-only, objective, what happened. Maps directly onto `chronicle/events.py`'s existing `EventLog`.
2. **Claim and variant store** — typed claims and mutated variants derived from events. Canonical claims never mutate; a mutation creates a new variant linked to its predecessor (same provenance discipline as ADR-0002's event sourcing).
3. **Subjective belief store** — per-NPC belief instances: confidence, verbatim/gist strength, evidence, source, first-learned/last-rehearsed timestamps.
4. **Social state store** — sparse relationships, grudges, obligations, trust, reputation.
5. **Narrative/query layer** — story sifters, quest hooks, explanation views, the dashboard.

Recommended record shapes (condensed from the source report's §5.11 and §6.10):

```text
Claim(id, kind, slots, canonical_event_id, truth_status)
BeliefInstance(holder_id, claim_id, variant_id, confidence, uncertainty,
                verbatim_strength, gist_strength, source_summary,
                first_learned, last_rehearsed)
Evidence(id, belief_id, evidence_type, source_id, predecessor_id,
         location_id, timestamp, strength)
RumorState(npc_id, claim_variant_id, stage, last_heard, last_told,
           exposure_count, distinct_source_count)

Obligation(id, issuer, debtor, beneficiary, action, condition, deadline,
           status, witnesses, sanctions, excuse, created_at, fulfilled_at, violated_at)
Grudge(holder, target, source_event_id, severity, grievance_type,
       emotional_strength, evidentiary_strength, last_rehearsed, forgiveness_threshold)
Reputation(observer, subject, context, beta_alpha, beta_beta,
           direct_count, witness_count, certified_count, uncertainty, last_updated)
```

## Build order (as given in the source report, §9)

**Build first**: (1) canonical events, claims, variants, belief instances, evidence chains; (2) Gossamer's gossip phases; (3) sparse relationship histories (City of Gangsters); (4) bounded memory and mutation (fuzzy-trace theory, source monitoring, simplified ACT-R); (5) obligations and grudges as typed records; (6) observer-local reputation (Beta, subjective logic).

**Add next**: DK/MT/SIHR rumor-state transitions; Deffuant–Weisbuch/Friedkin–Johnsen continuous-attitude updates; face-threat scoring; batch story sifters; Dwarf-Fortress-style long-term memory summarization.

**Defer**: full norm emergence; general-purpose logic programming; autoencoder anomaly detection; prospective drama management; LLM reflection or dialogue integration.

Promoted into `docs/architecture.md`'s build order — see that file.

## Performance budget (as given in the source report, §8.7)

| Workload | Strategy |
|---|---|
| Active scene (10-30 NPCs) | Full belief, gossip, obligation, face evaluation |
| Nearby NPCs | Relationship and rumor eligibility only |
| Offscreen NPCs | Daily/scheduled batch updates |
| Global reputation | No global computation — update only affected observer-local rows |
| Story sifting | Event-triggered, incremental, over a small authored pattern set |

Directly reusable as the fidelity-vs-proximity tier already implied by the
three-tier LLM architecture (`docs/architecture.md`) — this is the same
shape one level down, for the symbolic math tier itself.
