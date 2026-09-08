# Mod-conflict external research (2026-09-05)

Ten reports from three external tools (Gemini, Kimi, Claude web-research
agents), each answering one of four prompts about which popular Skyrim
mods ChronicleBridge's four game-side write paths are likely to collide
with. The prompts themselves live in
`notes/mod-conflict-research-prompts-2026-09-05.md`. These are raw,
unedited tool output — kept verbatim (including each tool's own citation
style) rather than summarized, because the citation quality varies by
source and a reader may need to check a specific claim's actual sourcing.
**`docs/design/mod-conflict-mitigation-plan.md` is the distilled,
cross-checked synthesis — read that first.** This directory is the
paper trail behind it.

Sourcing quality note: Gemini's reports lean heavily on Reddit/forum
citations with some primary-source (GitHub, official mod pages) mixed
in; Kimi's and Claude's lean much more on primary sources (Nexus mod
pages, GitHub source, UESP, official patch-hub documentation, the CK
wiki). The synthesis document weights claims accordingly and flags where
a report's conclusion was cross-checked against Chronicle's own source
and either confirmed or contradicted.

## Prompt 1 — AI package / schedule conflicts

| File | Source | Notes |
|---|---|---|
| [`gemini-prompt1-ai-package-conflicts.md`](gemini-prompt1-ai-package-conflicts.md) | Gemini | First to propose Quest Alias injection and a native `RE::ExtraPackage` override as alternatives to the Mutagen base-record edit. |
| [`kimi-prompts1-2-ai-package-and-bartermenu.md`](kimi-prompts1-2-ai-package-and-bartermenu.md) | Kimi | Covers prompts 1 and 2 together. First to surface SPID/SkyPatcher runtime distribution as the community's newest conflict-free pattern. |
| [`claude-prompt1-ai-package-conflicts.md`](claude-prompt1-ai-package-conflicts.md) | Claude | Sharpest of the three: names SkyPatcher `packageListAdd` specifically as the preferred fix, with per-NPC citations from AI Overhaul's own changelog. |

## Prompt 2 — Native `BarterMenu` price-hook conflicts

| File | Source | Notes |
|---|---|---|
| [`gemini-prompt2-bartermenu-hook-conflicts.md`](gemini-prompt2-bartermenu-hook-conflicts.md) | Gemini | Flags the UI-vs-transaction-engine desync risk and recommends hooking the native price-calculation routine instead of the vtable slot. |
| `kimi-prompts1-2-ai-package-and-bartermenu.md` (above) | Kimi | Surveys the economy-mod landscape; finds almost no popular mod natively hooks `BarterMenu` for pricing. |
| [`claude-prompt2-bartermenu-hook-conflicts.md`](claude-prompt2-bartermenu-hook-conflicts.md) | Claude | Identifies Dynamic Prices Framework (DPF) and Dynamic Pricing Framework as the two real native analogs; recommends becoming a DPF callback consumer instead of self-hooking. |

## Prompt 3 — Relationship-rank writes vs. dialogue/marriage/follower mods

| File | Source | Notes |
|---|---|---|
| [`gemini-prompt3-relationship-rank-compatibility.md`](gemini-prompt3-relationship-rank-compatibility.md) | Gemini | Weakest sourcing of the ten (mostly Reddit/Quora); core recommendation (decouple from `SetRelationshipRank` entirely) is directionally sound but not strongly evidenced. |
| [`kimi-prompts3-4-relationship-rank-and-evidence-spawning.md`](kimi-prompts3-4-relationship-rank-and-evidence-spawning.md) | Kimi | Covers prompts 3 and 4 together. Identifies vanilla's own favor/quest/marriage writes (not other mods) as the dominant real exposure. |
| [`claude-prompt3-relationship-rank-compatibility.md`](claude-prompt3-relationship-rank-compatibility.md) | Claude | Surfaces `OnStoryRelationshipChange`, a Story Manager event that fires on every rank write regardless of source — the one genuinely new mechanism across all ten reports. |

## Prompt 4 — Persistent object spawning + NPC relocation conflicts

| File | Source | Notes |
|---|---|---|
| [`gemini-prompt4-evidence-spawning-conflicts.md`](gemini-prompt4-evidence-spawning-conflicts.md) | Gemini | Raises the Havok-physics-ejection scenario (weakly sourced) and the reference-handle cap (real, but doesn't size it against Chronicle's actual spawn volume). Recommends abandoning live-position spawning for pre-placed disabled references — **contradicted by Chronicle's own prior research, see the synthesis doc.** |
| `kimi-prompts3-4-relationship-rank-and-evidence-spawning.md` (above) | Kimi | Validates live-position spawning as structurally correct (handles vanilla's own NPC relocations, e.g. Olfina, Ysolda, by construction); identifies the real risks as placement coherence, staleness, and save-bloat lifecycle. |
| [`claude-prompt4-evidence-spawning-conflicts.md`](claude-prompt4-evidence-spawning-conflicts.md) | Claude | Does the reference-handle-cap math explicitly (19-ish objects is negligible); adds the dead/killable-NPC edge case and a documented `Disable()`/`Enable()` physics-hookup workaround. |
