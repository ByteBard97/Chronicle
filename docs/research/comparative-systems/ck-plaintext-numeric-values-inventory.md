> Filed 2026-08-22 in `docs/research/comparative-systems/` — external
> research, not code-verified. A fourth independent pass on the CK2/CK3
> mechanics ground already covered by `ck-mechanics-inventory.md` and
> `ck-opinion-decay-and-threshold-tables.md`. **This one's distinguishing
> value: exact numeric values as plain markdown text with inline
> footnote-style citations, not embedded formula images** — it directly
> fills the gap flagged in `ck-mechanics-inventory.md`'s provenance header
> (several of that file's thresholds are only readable as embedded
> images). Cross-check numbers here against that file where both cover the
> same mechanic. Also includes an "Evidence gaps and version caveats"
> section (§11) worth reading before treating any single value as final.
> Feeds the scenario-ladder / reactivity design work, not any accepted ADR.

# CK2/CK3 social-reactivity mechanics inventory

This report inventories the shipped mechanics by which Crusader Kings II and Crusader Kings III convert character-level social state into behavior. It emphasizes typed state, stacking and decay, threshold-to-action conversion, named relationships, and AI scoring. Exact values are included where the consulted official wiki, patch notes, modding documentation, or detailed community documentation expose them; unresolved formulas are labeled explicitly.

## 1. Executive comparison

| Dimension | CK2 | CK3 | Design implication |
|---|---|---|---|
| Core social atom | Directed pairwise opinion, broken into itemized modifiers | Directed pairwise opinion plus named relations, hooks, secrets, memories, stress, and power-sharing state | Store subjective pairwise records; do not reduce social state to one faction-wide reputation score |
| Provenance | Strong: every visible opinion modifier has a reason string in the tooltip; script modifiers support duration, stacking, inheritance, linear decay, and legal predicates | Strong: opinion reasons, relation-formation reasons, secret source, memory participants, and scheme/agent provenance are explicit | Every belief or grudge should record source, witness/target, event type, timestamp, and mutation history |
| Temporal model | Mostly discrete timed expiry; linear decay is opt-in for scripted modifiers after patch 2.5 | Mixed: ordinary opinion modifiers, pooled tyranny decay, cooldowns, discontent growth/decay, stress thresholds, and memory duration | Use several time models, not one universal decay curve |
| Aggregation | Sum of typed pairwise modifiers; faction/council/plot systems read that aggregate | Sum of typed opinion components plus named states and pooled meters | Keep raw evidence separate from derived state so the player can inspect why behavior changed |
| Behavior conversion | Factions, plots, council votes, duels, assassinations, event choices | Factions, schemes, hooks/blackmail, interactions, decisions, council/diarchy/regency, activity and event content | Trigger behavior through deterministic eligibility gates plus probabilistic AI scoring |
| Inspectability | Opinion tooltip, character sheet, opinion map mode, arbitrary A-to-B opinion explorer | Opinion interface, relation labels, secrets/hooks UI, memory and scheme interfaces | Player-facing explanation should be itemized, not a hidden affinity number |

## 2. CK2 opinion ledger

### 2.1 Representation and presentation

CK2 opinion is directional: A's opinion of B is a separate value from B's opinion of A. The game exposes the breakdown directly: each modifier appears in the tooltip with its own reason, and the character sheet shows a character's opinion toward the player plus the ruler-liege pair. An “Explore Character Opinions” interaction supports inspecting arbitrary A-to-B opinion, and the opinion map mode lets rulers compare realm sentiment geographically.[^16^]

The opinion page explicitly connects low opinion to faction and plot behavior, while high opinion produces friendlier behavior and greater acceptance of requests.[^16^]

### 2.2 Core value sources

| Source | Exact value or formula | Target population | Notes |
|---|---:|---|---|
| Liege taxation | Scales from 0 down to **-100 opinion** | Vassals | At **-100**, ordinary vassals pay no tax.[^16^] |
| Liege levy demand | Varies between legal minimum and maximum | Vassals | Positive opinion can increase provided levies above the minimum formula.[^16^] |
| Wrong government type | **-20** | Count-tier and above vassals toward liege | Iqta, Monastic Feudal, Holy Order, ordinary republic, and merchant republic equivalences are documented.[^16^] |
| Prestige | **+1 per 200 prestige**, maximum **+10** | Everyone except clergy | Negative prestige is ten times stronger: **-1 per 20**.[^16^] |
| Piety | **+1 per 50 piety**, maximum **+10** | Same-faith clergy | [^16^] |
| State Diplomacy | **+1 per 4 State Diplomacy** | Characters not using personal diplomacy | [^16^] |
| Personal Diplomacy | **+1.5 × (Personal Diplomacy - 4)** | Courtiers, council members, spouses toward rulers; all characters toward non-rulers | For minors, parent or guardian skill may be checked instead.[^16^] |
| Short Reign | **-2 × (10 - [years reigned rounded up + Majesty])**, capped at **0** | Vassals and below | Tripled for most unreformed pagans; waived for Buddhists and Jains.[^16^] |
| Demesne Too Big | **-10 per step** over limit | Vassals | Newly acquired holdings receive a **2-month grace period**.[^16^] |
| Too Many Held Duchies | **-10 per held duchy over 2** | Vassals of king or emperor | [^16^] |
| Elector Titles Held | **-15 per elector title beyond one duchy and one kingdom** | Direct de jure vassals in feudal elective realms | [^16^] |
| Ambition opinion | Additional **-25** | Toward characters whose titles or positions are desired | Stacks with claimant and desired-title modifiers; also active while plotting to fabricate a liege-title claim.[^16^] |

### 2.3 Gift, title, and transfer modifiers

| Action | Value | Duration | Stacking / mutation rule |
|---|---:|---:|---|
| Grant barony | **+20** | **10 years** | Title-grant bonuses stack with one another.[^16^] |
| Grant county | **+40** | **10 years** | Stacks.[^16^] |
| Grant duchy | **+60** | **10 years** | Stacks.[^16^] |
| Grant kingdom | **+80** | **10 years** | Stacks.[^16^] |
| Grant empire | **+100** | **10 years** | Stacks.[^16^] |
| Transfer vassal | **+10** | **10 years** | Can also remove “desires control” sources by fixing de jure structure.[^16^] |
| Grant independence | **+30** | **10 years** | [^16^] |
| Monetary gift | Opinion value varies by context | **5 years** | Costs **15 × recipient monthly income**, minimum **15 gold**; repeated gifts extend duration rather than stacking additional opinion.[^16^] |
| Artifact gift | **+15 × artifact quality** | **5 years** | Modified by greed-related behavior.[^16^] |

### 2.4 Tyranny as separately tracked entries

CK2 does not pool tyranny into a single fading meter. Each tyrannical act is its own opinion entry, directed at affected observers, with its own expiry. Unjust imprisonment is **-40**, reduced to **-10** for insignificant or decadent characters; execution is **-10**; forced abdication or banishment of a landed vassal is **-10**; acting against a council vote is **-10** and makes the council discontent. Individual tyranny entries expire separately after **30 years**.[^16^]

Concrete example: a **-40** imprisonment in 1100 plus a **-10** execution in 1103 gives **-50 until 1130**, then **-10 until 1133**.[^16^]

### 2.5 Stacking, duration, and decay semantics

Scripted opinion modifiers support explicit durations in days, months, or years; indefinite duration uses `duration = -1`; a `stacking` parameter permits repeated applications; an `inherit` parameter allows heirs to inherit the modifier until its duration expires; and an `add_opinion`-style effect can override a predefined duration or apply multiple stacks through a multiplier.[^14^][^19^]

Patch 2.5 added support for opinion modifiers that decay linearly. This is an opt-in modifier property, not a universal rule for all opinion modifiers.[^24^] The modding syntax exposes `decay = yes`, with the example `common_interests_opinion = { opinion = 20 decay = yes }`.[^19^]

| Modifier field | Behavior |
|---|---|
| `opinion` | Flat pairwise value.[^19^] |
| `months`, `years`, `duration` | Explicit lifetime; indefinite duration is possible for character modifiers via `duration = -1`.[^14^][^19^] |
| `stacking` | Multiple applications coexist and stack.[^14^] |
| `inherit` | Heir inherits the opinion record until its duration expires.[^19^] |
| `decay` | Linear decay over time when enabled.[^19^][^24^] |
| `revoke_reason` | Grants righteous cause to revoke one title.[^19^] |
| `prison_reason` | Grants righteous cause to imprison.[^19^] |
| `execute_reason` | Grants righteous cause to execute.[^19^] |
| `banish_reason` | Grants righteous cause to banish.[^19^] |
| `enemy` | Treats the characters as effectively at war.[^19^] |
| `crime` | Marks a criminal act for foe checks.[^19^] |
| `disable_non_aggression_pacts` | Temporarily disables non-aggression pacts.[^19^] |
| `non_aggression_pact` | Creates a temporary non-aggression pact.[^19^] |
| `obedient` | AI accepts all diplomatic interactions from the other character and the `obedient` trigger returns true.[^19^] |

This means CK2's opinion ledger is not merely cosmetic: a single opinion record can simultaneously affect the pairwise score, grant legal justification, unlock violence, suppress diplomacy, or force obedience.

## 3. CK3 opinion ledger

### 3.1 Representation

CK3 retains directed pairwise opinion: every character holds an opinion of every other character.[^3^] Compared with CK2, the visible total is divided into more explicit categories, including general opinion, attraction, dynasty/family relation, faith hostility, named relation effects, and tyranny. On succession, the primary heir temporarily inherits part of vassal sentiment as “Opinion of Predecessor.”[^3^]

### 3.2 Selected exact components

| Component | Exact value or range | Notes |
|---|---:|---|
| Glory dynasty legacy tier 5 | **+10** general opinion | [^3^] |
| Personal Diplomacy skill | Approximately **-8 to +92** opinion | [^3^] |
| Tyranny | **-1 to -1000** opinion | Pooled tyranny, not CK2-style independently expiring events.[^3^] |
| Sadistic | **-10** | [^3^] |
| Murderer | **-15** | [^3^] |
| Broken Truce | **-50** | [^3^] |
| Same dynasty | **+5** | [^3^] |
| Parent-child | **+50** | [^3^] |
| Sibling | **+25** | [^3^] |
| Spouse | **+25** | [^3^] |
| Faith hostility: Righteous | **0** | [^3^] |
| Faith hostility: Astray | **-10** | [^3^] |
| Faith hostility: Hostile | **-20** | [^3^] |
| Faith hostility: Evil | **-30** | Pluralist halves the malus; Fundamentalist doubles it.[^3^] |

### 3.3 Tyranny pool and decay

CK3 tyranny is a pooled value with maximum **1000**. Successful imprisonment adds **20**; increasing a feudal obligation without concession or hook adds **20 per obligation**; revoking a title without cause adds **20**; retracting a vassal adds **5**; banishing a vassal adds **5**; executing a vassal adds **10**.[^3^]

The current base monthly decay is **-0.25 tyranny**. Thus a single **+20** imprisonment takes approximately **80 months** to decay at base rate.[^3^] Tyranny-loss modifiers include Domestic Affairs scaling of roughly **+1% to +50%**, generic artifacts at **+2% to +16%**, Hereditary Hierarchy reducing loss by **50%**, and the Soon Forgiven perk adding **-0.15 monthly tyranny**.[^3^][^125^]

Artifact and court sources add explicit monthly values: Common artifact Majesty gives about **-0.02 to -0.04**, Masterwork **-0.06 to -0.08**, Famed **-0.10 to -0.12**, and Illustrious **-0.14 to -0.16**; faith-topic books range from **-0.04** at Common to **-0.28** at Illustrious.[^123^]

### 3.4 Named relation opinion effects

| Relation | Opinion | Other mechanical effect | Death stress |
|---|---:|---|---:|
| Friend | **+60** | **+20% councilor efficiency** | **+10 stress** |
| Best Friend | **+120** | **+30% councilor efficiency** | **+10 stress** |
| Lover | **+60** | **+25% fertility** | **+10 stress** |
| Soulmate | **+120** | **+25% fertility** | **+10 stress** |
| Rival | **-60** | **-20% councilor efficiency** | **-35 stress** |
| Nemesis | **-120** | **-30% councilor efficiency** | **-35 stress** |

Friendship and conflict are mutually exclusive categories; love can coexist with either.[^3^]

## 4. CK2 threshold-to-action catalog

### 4.1 Factions

CK2 faction membership and leadership are state-driven but ultimately probabilistic. A character can lead or join up to **two** factions. Faction strength is measured relative to the liege, with a “Dangerous Factions” alert at **70%** strength. AI leaders may issue ultimatums once the faction reaches at least **75%** strength, with major likelihood boosts at **100%** and **150%**; the Antiking faction is an exception that can fire at **50%**. Most AI-led factions suppress ultimatums while the liege is a primary defender or fighting specified major wars.[^34^]

Faction objectives are scriptable. Objective modding exposes warning level, membership logic, success conditions, and abort conditions, so faction state is not merely hardcoded C++ behavior.[^35^]

| Faction/objective | Opinion gate or multiplier | Action consequence |
|---|---|---|
| Succession | Opinion above **75** causes exit; above **50** blocks joining; above **25** applies **0.2×** | Lower opinion increases membership likelihood; exit is state-driven.[^34^] |
| Crown Authority | Above **50** exit; above **25** blocks; above **5** applies **0.2×**; below **-10/-50/-75** applies **1.5×/2×/4×** | Opinion directly modifies joining likelihood.[^34^] |
| Independence | Above **80** exit; above **60** blocks; above **40** applies **0.5×**; below **0/-50/-75** applies **1.5×/2×/4×** | Low opinion strongly increases rebellion likelihood.[^34^] |
| Claimant | Above **25** applies **0.2×** | Supports another claimant.[^34^] |

Trait multipliers include Ambitious **4×**; Envious, Greedy, Deceitful, and Impaler **2×**; Proud, Brave, and Arbitrary **1.5×**; Content or Imbecile **0.01×**; Craven **0.1×**; Kind, Charitable, and Honest **0.5×**.[^34^]

### 4.2 Plots and assassination

A character can lead one plot while backing any number of plots. Military plot power uses relative levy contribution: vassals of the target contribute **2 × available-levy ratio**, equal-rank rulers in the same realm contribute the unmodified ratio, and foreign conspirators contribute **1/3** of the ratio. Council members have double plot power against rulers, and guardians or regents have extra plot power against children.[^42^][^43^]

| Plot/action | State read | Threshold | Outcome |
|---|---|---:|---|
| Revoke vassal title | Plot strength and backers | **80% strength** and **1 backer** | Plot can execute.[^43^] |
| Fabricate Claim | Plot strength and backer count | **75% + 3 backers** | **60% success chance**.[^43^] |
| Fabricate Claim, stronger | Plot strength and backer count | **100% + 5 backers** | **90% success chance**.[^43^] |
| Seize trade post | Plot strength and backer count | **75% + 3 backers** | Plot can execute.[^43^] |
| General opportunity pacing | Plot power | Steps at **50%, 100%, 150%, 200%** | Event-opportunity timing improves.[^43^] |
| Assassination attempt against hiding target | Plot power | Requires **100% plot power** | Base kill chance **18%**, or **27%** with extra investment.[^42^] |

The plot head must contribute at least **2.5%** personally, and backers need at least **50%** total plot power. Successful murder has **25%** discovery chance; failed attempts have **50%** discovery chance.[^42^][^43^]

Discovery consequences are explicit: a discovered attempt gives the target stacking **-200 Attempted Murder**, parents and children **-50**, and siblings **-25**. A discovered successful murder applies non-stacking **-10 Known Murderer with everyone for 50 years**, close kin **-30**, turns parents and children into rivals at **-100** who may seek murder, and gives stacking **-10 Dishonorable for 5 years** with righteous imprisonment cause.[^42^]

### 4.3 Council votes and obstruction

CK2 council behavior combines fixed vote requirements with stance scoring. Counts and dukes need **2 votes**, kings and emperors **3**, a regency under count through king requires **4**, and an imperial regency requires **5**.[^87^]

Loyalist scoring includes Content **+10**, Trusting **+5**, close relative **+10**, dynasty member **+5**, friend **+10**, lover **+5**, leader bloodline **+15**, **+10 at opinion ≥95**, and **+0.4 × opinion**; negative opinion makes Loyalist impossible. Malcontent scoring starts at **15**, adds Ambitious **+5**, Envious **+10**, extra Envious **+5** if neither Ambitious nor Content, Rival **+20**, and **-1.6 × negative opinion**, while Content subtracts **15**, Trusting subtracts **5**, and positive opinion applies **-0.7 × opinion**.[^87^]

Concrete vote thresholds include revocation support when the voter dislikes the target at **-15 or below**, imprisonment support at **-5 or below**, banishment or execution support at **-10 or below**, and grant-title support when the voter likes the recipient at **+25**. Malcontents automatically oppose the liege.[^87^]

### 4.4 Duels and named hostile relationships

Duel score begins with `50 + attacker personal combat skill - defender personal combat skill + modifiers`. Duelists being rivals adds **+5**; defender being a friend or lover subtracts **3**; defender having a budding romance adds **+6**; attacker having a budding romance subtracts **3**; a severe hostile modifier adds **+12** if the attacker is neither Stressed nor Depressed, subtracts **6** if one applies, and subtracts **12** if both apply.[^61^]

### 4.5 Event timing and choice probability

CK2 event behavior is generally probabilistic rather than deterministic. Event modding exposes `trigger`, `mean_time_to_happen`, MTTH modifiers, and option-level `ai_chance`.[^116^] Community reverse engineering documents the conversion:

```text
dailyChance = 1 - exp(log(0.5) / MeanTimeToHappen)
chance = 1 - exp(noOfDays * log(1 - dailyChance))
```

Thus social state often changes a rate or option weight rather than producing an immediate hard trigger.[^112^][^116^]

## 5. CK3 threshold-to-action catalog

### 5.1 Factions and civil war

CK3 faction military power is member strength relative to liege strength. Above **80%**, faction discontent rises; below **80%**, it falls; the rate depends on distance from the threshold. At **100% discontent**, an ultimatum follows shortly. Factions can fire early after unjust imprisonment, while player-led factions can send an ultimatum at any time.[^25^]

Accepting an ultimatum costs the liege **-20 Dread** plus Legitimacy; refusal starts a civil war. A character cannot create or join a faction while landless, underage, a Ceremonial Monarch, under the liege's Strong Hook, bound by relevant alliance/truce/bloc constraints, at opinion of liege **80 or higher**, or terrified unless discontent is rising. AI vassals cannot start or join factions against friends or lovers, although players can. A Strong Hook or **500 Influence** can force membership for **10 years**. AI formation grace periods are **10 years** under an emperor, **5 years** under a king, and **1 year** under a duke or below.[^25^]

### 5.2 Powerful vassals, council expectation, and succession-law obstruction

The number of powerful vassals is **3** for counts, **4** for dukes, and **5** for kings and above. A powerful vassal not on the council has **-40 opinion**, receives more elective votes, and is harder to sway. Succession-law change requires every powerful vassal to have positive opinion, be terrified, or be imprisoned.[^25^]

Council Rights: Guaranteed gives **+5 opinion** with the vassal, **-2 opinion** with all powerful vassals, permits Demand Council Position without a hook, and contributes contract score **+3**. Demand Council Position with a hook is forced, and the character cannot be removed for **25 years**.[^25^]

A feudal contract can be changed once per lifetime of either liege or vassal, shared between them, with up to **4** changes at once. Every point by which the new contract score is lower causes **20 tyranny**. A Weak Hook can compensate for **1** score point when increasing an obligation. Raising obligations adds **20 tyranny**, doubled when raising taxes from Normal to High.[^25^]

### 5.3 Vassal stances

CK3 vassals have seven stances: Belligerent, Courtly, Glory Hound, Parochial, Zealot, Minor Landholder, and Minority. Stance is primarily determined by AI personality. Preferred-heir succession grants temporary **+30 opinion**, while non-preferred-heir succession grants temporary **-20 opinion**.[^25^]

### 5.4 Power sharing, regency, and diarchy

Power sharing prevents the title owner from changing succession law and blocks the ruler from imprisoning, revoking titles from, retracting vassals from, asking conversion of, or requesting excommunication of the diarch. Regency occurs when the ruler is imprisoned by a non-vassal or traveling outside the realm. It ends automatically at Scales of Power level 1 or if the diarch has Selfless loyalty; otherwise it requires Prestige, Piety, Gold, or offering a Weak Hook. During Regency, the liege gets **+10% Stress Loss** and the regent gets **+15% Stress Gain**. Ending a regency grants the diarch **150 Prestige**.[^96^]

Regent selection priority is primary heir, spouse or parent, child or sibling, then councilor family member. Manual designation every **10 years** reduces opinion with higher-priority candidates and Courtly vassals. Scales of Power ranges **0-100**, tends toward **50**, and attempts to swing every **2 years**. Head of Faith intercession requires same head of faith, at least **60 opinion**, and the opponent not having **40 opinion** or a Strong Hook.[^96^]

When Scales favor the diarch, the liege pays Prestige for mundane coercive actions including revoke title, retract vassal, imprison, and execute. Regency levels unlock Level 1 (**0-33**) Siphon Treasury, Level 2 (**34-66**) Regent Imprison, Level 3 (**67-99**) Legal Meddling, and Level 4 (**100**) Modify Vassal Contract / Entrench Regency.[^96^]

Failure at Siphon Treasury produces **15-50 Strife** and **-30 to -75** liege opinion depending on amount. Regent Imprison veto costs **150 Prestige**; success gives **+10 Dread** and **15 Strife**, while failure against a vassal can start a Remove Regent war. Legal Meddling costs **150 Prestige**, or **80 Prestige** for a 50% chance, or uses a Learning challenge; success creates an unpressed claim, **10 Strife**, and **-20** vassal opinion, while failure causes Stress and **-10** vassal opinion. Entrench Regency costs **150 Prestige**. Entrenched Regency or Co-Monarchy can eventually unlock Attempt to Overthrow Liege and Invite Conspirators to Coup.[^96^]

## 6. CK3 schemes and social-state reads

A character can run one scheme of each class simultaneously. Most hostile and political schemes allow up to **5 agents**, and agents must be adult courtiers, guests, or direct vassals of the target who are not imprisoned or already in another scheme. Individual agent contribution caps at **+50**.[^51^]

Agent acceptance reads opinion of schemer, schemer skill, target rank, foreign-realm penalty, relationship, AI personality, and enticements. Relationship acceptance is Best Friend **+100**, Friend **+50**, and Lover **+25**. Terrified characters cannot become agents except through a Strong Hook.[^51^]

Closeness success bonuses include spouse or guardian **+30**, concubine **+20**, close family **+10**, extended family **+5**, diarch **+30**, councilor **+10**, powerful vassal **+5**, vassal **+2**, personal physician/cup-bearer/food taster/bodyguard/chief eunuch **+20**, lady-in-waiting **+5**, best friend **+30**, friend or lover **+20**, nemesis **+10**, and rival **+5**.[^51^]

Enticements include leverage advantages ×3 for **+10**, leverage advantages ×5 for **+30**, bribe **+10**, hefty bribe **+20**, offer hook on self **+20** plus about **20 stress**, use hook on them **+100**, and Prestige/Influence/Piety offers **+20**.[^51^]

### 6.1 Scheme-specific values

| Scheme/action | Exact value or outcome |
|---|---|
| Murder | Maximum secrecy **95%**; being at war gives **-50 success**.[^51^] |
| Abduct | Maximum secrecy **85%**; being at war gives **-500 success**.[^51^] |
| Fabricate Hook | Maximum secrecy **95%**.[^51^] |
| Overthrow Regent | Maximum secrecy **85%**.[^51^] |
| Murder stress | Honest **+40**, Just **+40**, Compassionate **+80**.[^51^] |
| Abduct stress | Honest **+20**, Just **+20**, Compassionate **+40**.[^51^] |
| Sway success | **95%** chance of **+25 opinion**, **5%** chance of **+30 opinion**.[^51^] |
| Seduce success | **+20 opinion**; can create Lover and doctrine-dependent secrets.[^51^] |
| Romance success | Creates Soulmate.[^51^] |
| Befriend success | Friend becomes Best Friend; ends rivalry; disbands target-led faction; removes target from faction.[^51^] |
| Befriend failure | **-20 opinion** with target; if target is Rival, **-15 opinion** with every courtier; if faction leader, **+20 Faction Discontent**; spouse may expose a random secret unless paid **100 Gold** or hooked; direct liege causes **-150 Prestige**.[^51^] |

## 7. CK3 hooks, secrets, stress, and memories

### 7.1 Hooks

Only one hook can be held on a character at a time; a stronger or longer hook replaces the older hook. Weak hooks are single-use, usually provide acceptance bonuses, and often last **10 years**, though a House Head hook is permanent. Strong hooks are reusable with a **5-year cooldown**, usually force acceptance, and passively prevent the target from joining factions, declaring war, imprisoning, or demanding conversion against the holder. A Strong Hook over the Realm Priest forces maximum contribution. Perpetual hooks are permanent, reusable with a **5-year cooldown**, usually provide acceptance bonuses, and cannot be fabricated.[^52^]

Blackmail over a Shunned secret creates a Weak Hook; blackmail over a Criminal secret creates a Strong Hook; refusal exposes the secret.[^52^]

| Interaction | Weak Hook | Strong Hook |
|---|---:|---:|
| Arrange Marriage | **+100 acceptance** | **+200 acceptance** |
| Demand Conversion | **+50 acceptance** | Forced |
| Invite to Scheme | **+100 acceptance** | Forced |
| Force to Join Faction | Not sufficient | Strong Hook required |
| Demand Council Position | Forced when usable | Forced; no removal for **25 years** |
| Modify Vassal Contract | Can avoid tyranny | Forced and avoids liege tyranny |
| Force Vote | Forced when usable | Forced for **100 years** |

### 7.2 Secrets

Secrets record hidden acts whose severity depends on faith doctrine and social context. Public examples include attempted murder, murder, coup plotting, cannibalism, deviancy, sodomy, incest, secret faith, non-believer, witchcraft, illicit lover, illegitimacy, treasury embezzlement, examination cheating, and requested incursion. Discovery enables blackmail or exposure; blackmail converts secret knowledge into a hook, while exposure applies public consequences.[^52^]

### 7.3 Stress

Stress ranges from **0 to 400** and is gained when actions conflict with personality, close characters die, the character is imprisoned or tortured, or a guardian changes a ward's personality. Thresholds are:

- **100-199**: **-10% fertility**, no health penalty.
- **200-299**: **-30% fertility**, major health penalty **-1**.
- **300-399**: **-50% fertility**, severe health penalty **-2**.
- **400**: level-3 mental break, after which Stress drops by **100**.[^8^]

The first breach of 100, 200, or 300 triggers the corresponding mental break. The mental-break cooldown is **5 years**, or **8 years** with Mental Resilience; remaining above 100 after cooldown can cause another break. Coping mechanisms stack **+20% Stress Loss** and unlock related stress-reducing decisions on a **3-year cooldown**. Level-3 breaks can injure or kill the character, cause them to kill a courtier or heir, or force abdication. “Lash Out” can cause **-10 Direct Vassal Opinion** and **-40 opinion** with a vassal.[^8^]

The documented trait-to-stress table includes Ambitious stress for granting independence, granting titles at or below domain limit, or signing White Peace during an offensive war; Compassionate stress for kicking from court, disinheriting, denouncing, breaking up with a lover, dismissing a concubine, fabricating hooks, blackmail, imprisonment, moving to dungeon, execution, murder, abduction, torture, and title revocation; Honest stress for inviting agents to schemes, eloping, fabricating hooks, murder, and abduction; Just stress for elopement, tyrannical contract modification, claiming the throne, fabricating hooks, buying claims, unjust imprisonment or execution, murder, abduction, retracting a vassal from a de jure liege, and joining an independence faction against a de jure liege; Shy stress for negotiating alliances, joining war, recruiting guests, inviting to court, hosting honored guests, befriending, and courting; Greedy stress for granting independence, gifts, titles, inviting agents with gifts, and granting vassals; and Vengeful stress for restoring inheritance, forgiving, and moving to house arrest.[^8^]

### 7.4 Memories

CK3 memories are typed records with tagged participants and optional duration. Script effects support `create_character_memory` and `destroy_character_memory`; iterators include every, ordered, and random memory or memory participant; triggers can test memory type, category, and participant.[^6^][^7^][^97^]

Patch 1.7 describes examples such as children born, battles won, and rivals killed. Memories are used by events and other content; for example, an assassin may cite a grievance. Memories may fade with time and are usually lost on death, though player-controlled rulers and high-tier rulers can preserve memories longer or forever.[^29^]

Patch 1.9 added a memory for becoming nemeses and made war declaration, war end, and war join memories mention the casus belli. Patch 1.13 added stillbirth and premature-pregnancy memories plus memories for changing or adopting state faith, made `nemesis_killed_by_me` private, and fixed several memory durations. Patch 1.18 revised coronation memories and removed some trivial or buggy memory names.[^106^][^107^][^130^]

A complete public taxonomy of every memory type was not found in the consulted public sources; that remains an evidence gap rather than an inferred list.

## 8. Relationship crystallization in CK2 and CK3

### 8.1 CK2 named states

CK2 has explicit friend, rival, and lover states rather than treating all social outcomes as high or low opinion alone. Patch 2.1 added direct `add_friend`, `add_rival`, `remove_friend`, and `remove_rival` effects and corrected `is_friend` and `is_rival`; multiple lovers are supported. The command documentation records `add_rival = FROM`, which starts rivalry and, if applicable, ends friendship but does not end romance.[^14^][^62^]

Event-index evidence shows dedicated social chains: gain friend around event **100112**, gain rival around **100113**, friend war-aid chain **100150-100164**, friend-of-friend chain **100170-100175**, heretic friend or ending friendship **100180-100186**, friend assistance beginning around **100190**, friendship deterioration **100350-100354**, friend reacting to attack by rival **100400-100402**, rival duel request **100410-100415**, rival tournament cheating accusation **100420-100429**, and rival excommunication chain **100440-100445**.

### 8.2 CK3 progression and final states

CK3 uses potential states and progression before final named relations. Childhood Friend, Crush, and Bully-Victim can evolve into adult relations. Lifelong Best Friend, Soulmate, and Nemesis require an existing adult relation and are limited to one each. Patch 1.7 added public formation reasons for Friend, Best Friend, Rival, Nemesis, Lover, and Soulmate. Patch 1.9 clarified that Progress to Friend only makes two characters potential friends if opinion is above **0**. Patch 1.13 changed some content to progress toward rivalry rather than setting it outright, moved activity pulse actions to progress-to-friend and progress-to-lover effects, and generally gave unimportant characters a unilateral grudge instead of a mutual rivalry when targeting important characters. Patch 1.19 corrected soulmate removal in “Too Much of a Good Thing,” counted Betrothed, Soulmates, Best Friends, Blood Brothers, and Nemeses as major-interest relationships, and expanded secret-exposure notifications for friend, lover, rival, and blood-brother relationships.[^29^][^60^][^106^][^107^][^122^]

### 8.3 House-level crystallization

CK3 also aggregates repeated character actions into house relations. If no relevant action occurs for **50 years**, house relations move one level toward Neutral. At **100%** positive or negative progress, the relation changes level. Positive actions include gift to house head **+20%**, release without demands **+20%**, become best friends **+20%**, become friends **+10%**, and exchange hostages **+20%**. Negative actions include abduction, broken betrothal, declare war, or divorce **-10%**; becoming rivals **-10%**; becoming nemeses, cheating discovered, murder discovered, execution, imprisonment, raiding, or title revocation **-20%**; and torturing, blinding, castrating, or disfiguring a prisoner **-20%**.[^11^]

Feuding gives **-30 opinion**, **-25 marriage acceptance**, **+15 hostile scheme success**, increased war likelihood, and unlocks Eradicate Rival House. Faithful gives **+30 opinion**, **+25 marriage acceptance**, **+15 personal scheme success**, decreased war likelihood, and allows house heads to negotiate alliance.[^11^]

## 9. AI decision-making and scoring

### 9.1 CK2

CK2 combines hardcoded diplomatic and faction behavior with scriptable event and objective logic. Event files specify trigger conditions, MTTH, MTTH modifiers, and option-level `ai_chance`; faction objectives specify membership and success logic. The result is usually probabilistic: social state shifts the score, the score shifts event timing or option choice, and only some interactions use hard acceptance thresholds.[^35^][^116^]

### 9.2 CK3 moddable channels

CK3 divides behavior between hardcoded systems and scripted scoring. Army behavior is explicitly hardcoded, while moddable channels include AI defines, chance and trigger blocks, AI personality values, script, story cycles, events, and on-actions.[^72^]

AI defines live in `common/defines/ai`. Event options use `ai_chance`; decisions use `ai_check_interval`, `ai_potential`, and `ai_will_do`; interactions expose fields such as `ai_targets`, `ai_frequency`, and `ai_accept`.[^69^][^71^][^72^]

A documented `ai_chance` pattern is:

```text
ai_chance = {
  base = 10
  modifier = {
    add = 100
    has_trait = chaste
  }
  modifier = {
    factor = 0
    has_trait = deviant
  }
  ai_value_modifier = {
    ai_zeal = 1
  }
}
```

Here `modifier` changes the score when its trigger is true, `add` adds a flat amount, `factor` multiplies the score, and `ai_value_modifier` scales by hidden AI personality values.[^72^]

Decision AI uses `ai_check_interval` in months; interval **0** means the AI never checks the decision. `ai_potential` gates consideration, and `ai_will_do` calculates the percentage chance when considered.[^71^]

### 9.3 AI personality values

Exposed AI personality parameters include `ai_amenity_spending`, `ai_amenity_target_baseline`, `ai_boldness`, `ai_compassion`, `ai_energy`, `ai_greed`, `ai_honor`, `ai_rationality`, `ai_sociability`, `ai_vengefulness`, `ai_war_chance`, `ai_war_cooldown`, and `ai_zeal`. Display bands are very negative **-76 to -100**, negative **-1 to -75**, positive **+1 to +75**, and very positive **+76 to +100**.[^72^]

Personality effects include Boldness affecting Dread resistance, war risk, duels, faction-ultimatum acceptance, and imprisonment risk; Compassion affecting prisoner treatment, murder, execution, torture, cultural acceptance, and friendship; Greed affecting raids, taxes, ransom, gifts, betrayal, title revocation, and white peace; Honor affecting alliances, law-following, blackmail, hostile schemes, Find Secrets, and betrayals; Rationality affecting Disrupt Schemes, ending long wars, debt repair, tyranny, and murdering tyrannical lieges; Sociability controlling how often character interactions are considered; Vengefulness affecting retaliation against rivals and cheating spouses; and Zeal affecting holy war participation, conversion, pilgrimage, piety actions, and theocracy requests.[^72^]

Patch 1.18 adds `ai_will_select` for event options, `ai_check_interval_by_tier`, `ai_frequency_by_tier`, and `ai_will_do` prioritization for Great Projects.[^130^]

## 10. Transferable architecture for the Skyrim mod

| CK pattern | Skyrim-mod analogue | Implementation rule |
|---|---|---|
| Directed pairwise opinion | NPC A's subjective belief about NPC B | Store A→B records separately from B→A |
| Itemized tooltip | Explainable social ledger | Every derived score should decompose into named evidence entries |
| Timed, permanent, inherited, and decaying modifiers | Rumors, witnessed insults, debts, rescued kin, inherited grudges | Give each belief a lifetime model and provenance rather than one global decay |
| CK2 legal predicates on opinion records | Beliefs that unlock dialogue, restraint, service refusal, or violence | Attach behavioral predicates to serious evidence, not just score |
| CK3 named relations | Friend, rival, lover, nemesis equivalents | Crystallize repeated state into named states only after explicit progression |
| CK3 hooks and secrets | Blackmail leverage, embarrassing knowledge, criminal evidence | Separate knowledge, exposure, and leverage states |
| CK3 memories | Witnessed events with participants and optional duration | Store event participants so later dialogue can cite who did what to whom |
| CK3 stress | Social-pressure or trauma meter | Use thresholds and cooldowns rather than instant personality flips |
| Faction/plot power | Group coordination strength | Aggregate member resources and social willingness before NPC coalitions act |
| Council/diarchy constraints | Authority and legitimacy checks | Make social state alter available actions, not only dialogue tone |
| `ai_chance`, `ai_will_do`, `ai_accept` | NPC action scoring | Use deterministic eligibility first, then weighted probabilistic choice |
| House relations | Family/clan-level grudges | Aggregate repeated pairwise events slowly, with reversion toward neutral |

The most defensible architecture is a three-layer model:

1. **Evidence layer**: immutable social events and beliefs with source, observer, target, participants, timestamp, reliability, secrecy, and mutation history.
2. **Derived-state layer**: pairwise affinity, named relations, secrets, hooks, obligations, grudges, house reputation, stress, and group discontent.
3. **Action layer**: deterministic gates plus probabilistic scoring for dialogue, avoidance, schedule changes, gifts, blackmail, duels, faction recruitment, and retaliation.

## 11. Evidence gaps and version caveats

| Area | Status |
|---|---|
| CK3 complete ordinary timed-opinion duration table | Not fully enumerated in consulted public sources; do not invent durations. |
| CK3 exact short-reign and predecessor-opinion durations | Unresolved in the gathered evidence. |
| CK2 generic friend/rival/lover formation thresholds | Scattered across events; no single complete threshold table was verified. |
| CK3 relationship progression beyond the documented opinion-above-0 gate for potential friends | Partly scripted and content-specific; unresolved as a general formula. |
| Hardcoded CK3 AI target-selection formulas | Public modding docs expose weighting channels, not every internal formula. |
| Complete CK3 memory-type taxonomy | Not available in consulted public sources. |
| Version sensitivity | CK3 pages are largely verified against recent PC versions around 1.19 as of August 2026; CK2 pages are largely verified against versions 2.6-2.8. DLC and patch dependencies must be checked before implementation. |

## 12. Bottom line

CK2's shipped model is an inspectable pairwise ledger: typed modifiers, explicit reasons, timed or permanent duration, optional stacking, optional inheritance, optional linear decay, and legal predicates attached to serious offenses. CK3 keeps that ledger but adds persistent social objects: named relationships, hooks, secrets, schemes, stress, memories, vassal stances, house relations, and regency power. Across both games, behavior is rarely a single hard opinion threshold. The reliable pattern is **state read → eligibility gate → score/weight → probabilistic action**, with deterministic effects only where the interaction or scripted objective explicitly forces them.
