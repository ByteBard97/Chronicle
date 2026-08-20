# **Architectures for Hybrid Symbolic-LLM Social Simulations: Multi-Tier Agent Frameworks, Latency Budgets, and State Interoperability**

Simulating game-scale agent societies requires balancing computational feasibility with narrative expressive capacity1. While pure agent-based models scale efficiently to large populations using low-cost mathematical propagation rules, they lack semantic richness, dynamic rumor mutation, and context-aware reasoning1. Conversely, pure Large Language Model agent architectures suffer from exponential inference costs, latency bottlenecks, memory hallucination, and systemic homogenization when executed across hundreds or thousands of nodes4.  
To reconcile these constraints, state-of-the-art computational social systems utilize hybrid multi-tier architectures2. These frameworks partition the agent population across distinct operational layers: deterministic rule engines handle global background propagation, specialized small-parameter local models modulate high-centrality semantic hubs, and high-parameter models drive direct contextual interactions with the player2.

## **1\. Hybrid Multi-Agent Architectural Frameworks**

### **Tiered Decoupling and Structural Partitioning**

Modern hybrid agent architectures decouple high-frequency numerical state updates from low-frequency, semantics-heavy reasoning2. In a three-tier design, the bottom layer manages thousands of background agents using deterministic agent-based modeling rules, differential propagation equations, or graph-based structural models2. The middle layer delegates semantic processing—such as rumor distortion, motivated reasoning, and social polarization—to a small subset of high-centrality hub nodes driven by local, small-footprint language models2. The top layer invokes large foundation models on demand when an agent interacts directly with a human player or triggers a critical game event1.

| Framework | Architecture Topology | Tier Interface Protocol | LLM Tier Backbone | State Update Mechanism | Target Scale |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **RumorSphere** \[cite: 2, 3\] | Hierarchical Resonance Network & Adaptive Roles | Information Confusion Index to Prompts or Opinion Scores | gpt-4o-mini / Qwen2.5-3B \[cite: 4, 8\] | Formulaic Agent-Based Modeling vs. Memory Reflection3 | ![][image1] agents2 |
| **SAPIENT** \[cite: 7\] | Sentinel Layer & Orchestrated Focus Groups | Versioned Signal State ![][image2] via Structured Tool-Use | Claude Sonnet 4 / GPT-4o \[cite: 7\] | Citation-Verified Evidence Ledger & Moderated Panels7 | Population-scale streams7 |
| **TRUST Agents** \[cite: 10, 11\] | Modular Multi-Agent Verification Pipeline | Atomic Claim Decomposition to Structured Logic | Supervised Encoders \+ LLM Verifiers11 | Trust-Weighted Voting ![][image3] & Logic Aggregation11 | Enterprise claim graphs10 |
| **Self-Excited Simulator** \[cite: 4\] | Decoupled Hawkes Channel \+ LLM Task Selection | Self-Excitation Activation Gate to Contextual Query | Open-Source LLMs4 | Point Process Activation \+ Discrete Decision Capture4 | City-scale populations4 |
| **AgentSociety** \[cite: 12, 13\] | Mind-Behavior Layered Urban Simulator | Social Graph API \+ Environment Hooks | Multi-LLM Swarms12 | Theory of Planned Behavior / Maslow Hierarchy12 | Urban-scale agent societies12 |

### **Dynamic Role Switching and Information Cocoon Theory**

A primary breakthrough in scaling hybrid systems is the dynamic assignment of language model compute based on social topology and information state2. In the RumorSphere architecture, the simulation initializes a Hierarchical Resonance Network combining priority connections for opinion leaders with triangular connections for local community clustering2. To optimize compute allocation, RumorSphere implements a Dynamic Interaction Strategy grounded in information cocoon theory2.  
Rather than permanently assigning specific non-player characters (NPCs) as generative language agents, the system dynamically calculates an Information Confusion Index across the social graph at each tick2. Nodes trapped within homogeneous information cocoons exhibit stable, predictable belief states that are processed purely via deterministic mathematical update formulas2.  
When an agent is situated at an information conflict boundary—where incoming messages from neighboring nodes conflict beyond a threshold value—the Dynamic Interaction Strategy dynamically converts the agent from a rule-based regular node into a language-driven core node2. The core agent then queries its episodic memory, reflects on the conflicting information, generates a natural language stance, and emits an updated numeric opinion score to its adjacent regular nodes3. Once the local conflict resolves, the agent reverts to deterministic processing2. This dynamic reallocation maintains macro-level propagation accuracy while reducing generative inference costs substantially2.

### **Inter-Tier Communication Interfaces**

Interoperability across architectural tiers relies on standardizing translation protocols between symbolic mathematical matrices and natural language prompts:

* **Symbolic-to-Semantic Mapping (Tier 1 to Tier 2/3)**: Quantitative state values (such as belief strength vectors, target trust scores, and decay coefficients) are converted into structured natural language context blocks2. The interface formats numerical vectors into narrative premises detailing dynamic trust, past grievances, and personal motivations1.  
* **Semantic Mutation and Reflection (Tier 2 Processing)**: Local language models process the narrative premise alongside retrieved episodic memory units ranked by recency, relevance, and importance3. The model performs semantic mutation—altering details, exaggerating threats, or introducing character-driven biases—before re-quantifying the output1.  
* **Semantic-to-Symbolic Write-Back (Tier 2/3 to Tier 1\)**: Natural language outputs are forced into validated schema formats containing both conversational dialogue and discrete state deltas, updating the underlying symbolic graph7.

### **Temporal Realism and Action Gating**

A common failure mode in multi-agent generative simulations is temporal unreality4. Standard simulators rely on fixed turn-based or synchronous polling schedules4. Under synchronous execution, agent actions follow a near-Poisson distribution, resulting in artificially uniform activity timing (![][image4] on Burlai's burstiness scale) that fails to reflect real-world social dynamics4.  
To achieve temporal realism, the timing mechanism must be decoupled from the content generation mechanism4:

* **Timing Layer (Deterministic Gate)**: A data-calibrated self-excitation channel, such as a Hawkes point process, models background activity bursts, crisis-driven triggers, and circadian rhythms4. Agents remain idle until their mathematical activation probability crosses a stochastic threshold4.  
* **Execution Layer (LLM Query)**: The system queries the language model *only* when the timing gate fires, delegating the decision of *what* action to take and *how* to frame it to the model4.

Integrating a self-excitation gate elevates agent burstiness to human-like levels (![][image5]) without altering prompt structures or degrading narrative performance4.

## **2\. Structured Output Patterns and Symbolic State Reconciliation**

### **Converting Language Model Reasoning to Deterministic State Updates**

To keep dialogue generation aligned with game-world mechanics, language model outputs must cleanly write back into the game engine's state graph7. Unstructured text parsing or post-hoc regex extraction introduces high failure rates due to malformed syntax, missing keys, or context drift7. Modern architectures employ constrained decoding engines directly integrated into the inference runtime14.

### **Constrained Decoding Mechanization**

Constrained decoding restricts model output at the token-generation level14. Inference engines such as vLLM leverage backend libraries—including xGrammar, Outlines, and LM Format Enforcer—to enforce context-free grammars or JSON Schemas14:

* **Schema Definition**: State update payloads are defined using JSON Schema models, specifying exact data types, numerical ranges, and allowed enum values14.  
* **Logit Masking**: During the decode phase of inference, the grammar engine computes a bitmask over the vocabulary logits for every generated token14. Tokens that violate the schema's structural rules are assigned a probability weight of zero before sampling occurs14.  
* **Zero-Parser Guarantees**: Logit-level masking guarantees that the output string is syntactically valid JSON, eliminating the need for post-hoc error recovery or retry loops14.

JSON  
{  
  "$schema": "http://json-schema.org/draft-07/schema\#",  
  "title": "NPC\_State\_Update",  
  "type": "object",  
  "properties": {  
    "dialogue\_line": { "type": "string" },  
    "belief\_updates": {  
      "type": "array",  
      "items": {  
        "type": "object",  
        "properties": {  
          "target\_npc\_id": { "type": "string" },  
          "belief\_topic": { "type": "string" },  
          "delta\_strength": { "type": "number", "minimum": \-1.0, "maximum": 1.0 },  
          "evidence\_source": { "type": "string" }  
        },  
        "required": \["target\_npc\_id", "belief\_topic", "delta\_strength", "evidence\_source"\]  
      }  
    },  
    "emotional\_state\_shift": {  
      "type": "string",  
      "enum": \["anger", "fear", "trust", "neutral", "contempt"\]  
    }  
  },  
  "required": \["dialogue\_line", "belief\_updates", "emotional\_state\_shift"\]  
}

### **Performance Overhead and Latency Trade-offs**

While constrained decoding guarantees schema compliance, it introduces specific runtime trade-offs14:

* **Index Compilation Overhead**: Compiling a complex JSON schema into a finite-state machine or pushdown automaton introduces an initial latency penalty (typically 10–50 ms) during prompt prefill14.  
* **Decode Speed Impact**: Token-level logit masking adds a small per-token overhead (![][image6])14. However, overall end-to-end latency often *decreases* because the schema prevents the model from generating verbose, unstructured conversational filler7.  
* **Expressive Penalties**: Overly restrictive schemas can constrain model reasoning, occasionally producing truncated or awkward dialogue if token allocations for logical justification are omitted7. To mitigate this, schemas should include a dedicated reasoning scratchpad field *prior* to the structured JSON payload11.

### **Input Isolation and State Validation Pipelines**

To prevent unverified or malicious input from corrupting the simulation state (such as prompt injection embedded in player dialogue or external text streams), robust defense-in-depth pipelines are required7:

* **Input Isolation Layer**: All untrusted inputs are sanitized and wrapped in strict structural delimiters within system prompts, ensuring they are processed strictly as data rather than executable instructions7.  
* **Citation Verification**: Extracted semantic claims are evaluated against an active memory baseline7. State updates referencing non-existent entity identifiers or unobserved game events are discarded by an automated state validator7.  
* **Trust-Weighted Logic Aggregation**: As established in multi-agent verification frameworks, conflicting claims received from multiple sources are aggregated using explicit mathematical voting logic10:

![][image7]  
Where ![][image8] represents the source's historical reliability score, ![][image9] denotes the confidence level of the persona, and ![][image10] is an indicator function verifying logical completion11.

## **3\. Local Small-Model Practicality and Game GPU Co-Execution**

### **Model Selection for Persona-Conditioned Rewriting (1B to 9B Parameter Scale)**

Deploying a local hybrid simulation alongside a modern, GPU-intensive 3D game engine requires using parameter-efficient models (1B to 9B parameters)4. These small models act as local hub processors, handling persona-conditioned rewriting, rumor mutation, and social intent extraction1.

| Model Variant | Parameters | Native Precision / Quantization | VRAM Footprint (Weights \+ 8k KV) | Prefill / Decode Throughput | Primary Fitness for Social Simulation |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Qwen2.5-3B-Instruct** \[cite: 4, 8\] | 3.09B | INT4 (GGUF / EXL2) / FP8 | \~2.2 GB / \~3.1 GB | \~180 tok/s (Decode) | **High**: Excellent structured JSON execution, low footprint, strong roleplay fidelity4. |
| **Gemma-2-9B-It** \[cite: 8\] | 9.24B | FP8 / Q4\_K\_M | \~5.8 GB / \~7.2 GB | \~65 tok/s (Decode) | **Moderate-High**: Superior narrative quality and nuance; higher VRAM overhead8. |
| **Llama-3.1-8B-Instruct** \[cite: 5\] | 8.03B | INT4 / FP8 | \~5.1 GB / \~6.4 GB | \~85 tok/s (Decode) | **High**: High instruction-following accuracy and robust multi-turn stability5. |
| **Qwen2.5-7B-Instruct** \[cite: 4\] | 7.61B | FP8 / INT4 | \~4.8 GB / \~6.1 GB | \~95 tok/s (Decode) | **High**: Ideal balance of semantic mutation depth, JSON reliability, and speed4. |

### **Quantization Precision and Memory Budgeting**

Running local inference concurrently with a rendering engine requires strict VRAM budgeting16. Total memory consumption is defined by three main components: static model weights, the dynamic Key-Value (KV) cache, and operational scratchpad memory16.  
![][image11]  
In a standard 16 GB VRAM budget allocation on a consumer GPU, the primary 3D game engine and framebuffer consume between 8.0 GB and 10.0 GB. A quantized 7B parameter model in FP8 precision requires approximately 4.8 GB for static weights. Paged KV cache allocation absorbs 1.2 GB to 2.0 GB, while CUDA runtime scratchpad memory occupies the remaining 0.5 GB.  
Quantization precision fundamentally determines single-GPU viability16:

* **FP16 Baseline**: An 8B parameter model requires \~16 GB VRAM for weights alone, rendering single-GPU co-execution with a game engine impossible on consumer hardware16.  
* **FP8 Quantization**: On modern hardware architectures, FP8 maintains native-like model accuracy while reducing the weight footprint of a 7B or 8B model to \~4.8 GB–5.1 GB16. FP8 optimizes tensor core usage without requiring the decompression overhead associated with integer formats16.  
* **INT4 / GGUF (Q4\_K\_M)**: Quantizing weights down to 4 bits reduces the footprint of a 7B or 8B model to \~3.8 GB–4.2 GB, enabling co-execution on 12 GB or 16 GB GPUs16.

### **KV Cache Sizing and Paged Memory Allocation**

The KV cache scales dynamically based on sequence context length and concurrent request batch size16. For an 8B model operating with FP16 KV cache at an 8,192 token context length, each active context sequence requires approximately 1.0 GB of dedicated VRAM16.  
To prevent out-of-memory crashes during peak game processing, engines must implement paged memory management (such as vLLM's PagedAttention) combined with FP8 KV cache quantization16. Quantizing the KV cache to FP8 reduces its memory footprint by 50%, enabling up to 8 parallel agent background inference requests within a 1.5 GB VRAM cache allocation16.

### **Co-Execution and GPU Resource Partitioning**

Concurrent execution of a 3D game engine and an asynchronous background inference engine on a single GPU can introduce rendering stutter or frame-rate drops if hardware resources are managed naively. To ensure smooth frame pacing, the graphics pipeline executes on a high-priority CUDA stream, while background language model tasks are dispatched to a low-priority compute queue.  
Resource partitioning strategies prevent performance degradation:

* **CUDA Stream Prioritization**: The inference runtime executes on a low-priority CUDA stream, allowing the primary rendering and game engine streams to pre-empt background generative operations.  
* **Chunked Prefill Execution**: Large prompt prefill phases saturate GPU compute units, causing severe frame spikes16. Enforcing a maximum prefill chunk size (such as max\_num\_batched\_tokens \= 512\) splits long prompt processing across multiple frame cycles, keeping GPU compute utilization stable16.  
* **Asynchronous Queue Management**: Tier 2 hub updates execute asynchronously in a background worker pool4. The game engine reads the most recent committed state from a read-copy-update buffer, ensuring that dialogue or belief queries are never blocked by pending language model inference calls4.

## **4\. Empirical Evaluation and Plausibility Validation**

Evaluating hybrid social simulations requires validating both individual behavioral plausibility at the micro level and emergent population dynamics at the macro level1.

| Validation Level | Primary Targets | Key Evaluation Metrics | Evaluation Frameworks & Benchmarks |
| :---- | :---- | :---- | :---- |
| **Micro-Level Evaluation** \[cite: 1, 4\] | Individual Agent Plausibility | Persona Alignment, Instruction Following, JSON Schema Compliance5 | LLM-as-a-Judge, Schema Parsing Validators14 |
| **Macro-Level Evaluation** \[cite: 2, 4\] | Population-Scale Dynamics | Cascade Velocity, Polarization Drift, Temporal Burstiness (![][image12])2 | Hawkes Process Fitting, Counterfactual Auditing3 |
| **Social Susceptibility** \[cite: 19, 20\] | Group Influence & Trust | Conformity Rate (![][image13]), Independence Rate (![][image14]), Resistance19 | BenchForm Protocol, Kairos Benchmark20 |

### **Survey Calibration and Social Impact Alignment**

To measure how effectively an artificial population mirrors human social responses, systems utilize standardized psychometric surveys and social influence frameworks7. Synthetic agent populations are administered survey instruments pre- and post-intervention7.  
Recent empirical evaluations utilize Asch-conformity variants and Social Impact Theory to measure agent susceptibility to majority pressure, source authority, and temporal proximity19. By calculating the system's overall Conformity Rate and Independence Rate, developers can tune model prompts and structural weights to match empirical human baseline distributions, avoiding artificial polarization or absolute compliance19.

### **Automated Judging and Counterfactual Benchmarking**

Evaluating long-horizon social simulations using human raters is costly and difficult to scale6. Consequently, modern pipelines incorporate automated evaluation frameworks18:

* **Kairos Benchmark Suite**: Kairos evaluates multi-agent social behavior by testing how agents balance historical trust against peer influence when presented with conflicting signals21. Models are scored across four metrics: overall task accuracy, error-correction utility, resistance to unreliable misinformation, and overall social robustness21.  
* **BenchForm Multi-Agent Protocol**: BenchForm measures conformity bias across multi-round interactions, evaluating how agent reasoning degrades under group influence20.  
* **Counterfactual Intervention Audits**: As demonstrated in RumorSphere, developers run parallel counterfactual runs where specific variables—such as opinion leader stances, debunking frequency, or network topology—are altered2. Comparing these counterfactual paths against baseline trajectories exposes causal relationships, validating that the simulation's emergent phenomena stem from modeled agent interactions rather than stochastic noise1.

## **5\. Architectural Failure Modes and Mitigation Strategies**

Sustained multi-agent simulations are subject to specific structural failure modes that emerge over extended execution runs4.

| Failure Mode | Structural Mechanism | Empirical Manifestation | Architectural Mitigation Strategy |
| :---- | :---- | :---- | :---- |
| **Persona Decay** \[cite: 17, 22, 23\] | Context window dilution; instruction fading over extended turns17. | Agents abandon unique dialect, character constraints, and background biases17. | **History-Carried State**: Store relational state in symbolic memory rather than system prompts22. |
| **Formality Collapse** \[cite: 17\] | Alignment bias towards polite, neutral assistant registers6. | Antagonistic NPCs shift to generic, helpful, or formal tones over time6. | **Negative Prompting & Style Anchors**: Inject dialect-anchoring context blocks into turn prompts5. |
| **Systemic Homogenization** \[cite: 5, 6\] | Convergence toward a WEIRD average persona5. | Population loses behavioral variance; agents respond uniformly despite distinct prompts5. | **GRPO Fine-Tuning & Multi-Model Ensembles**: Train via Group Relative Policy Optimization6. |
| **Conformity Cascades** \[cite: 19, 20\] | High sensitivity to peer signals; vulnerability to groupthink19. | Agents abandon correct beliefs when exposed to inaccurate majority consensus19. | **Reflection Loops & Independent Voting**: Force isolated private evaluation before public exchange1. |
| **Temporal Rigidity** \[cite: 4\] | Synchronous turn-based polling loops without stochastic activation4. | Agent activity schedules show near-Poisson distribution (![][image4]) lacking bursts4. | **Self-Excited Hawkes Gating**: Decouple action timing from action content generation4. |

### **Persona Decay and Formality Collapse**

Persona Decay occurs as the context window fills with multi-turn conversation history17. Over time, initial system prompt instructions exert less relative attention weight during inference, causing agents to drift toward generic baseline personalities17. A related failure mode, Formality Collapse, describes the tendency of agents to drift into polite, formal registers due to safety alignment and reinforcement learning training biases6.  
To mitigate these issues, systems must distinguish between prompt-assigned establishing personas and history-carried relational state22. Relying solely on long system prompts leads to persona decay22. Instead, relational state must be extracted after each turn and maintained as structured symbolic records22.  
When invoking an agent, the system dynamically reconstructs a concise context window containing only the core personality attributes, key style anchors, and active relational state variables5. This structured injection stabilizes agent identity over long execution horizons22.

### **Systemic Homogenization and the Replicant Effect**

Systemic Homogenization—frequently referred to as the Replicant Effect—is an architectural risk in large-scale social simulations5. Because language models are trained to maximize token likelihood across massive human corpora, their default output distribution tends toward a safe, average persona5. When hundreds of unique agents are deployed, their individual reasoning logic often collapses into a uniform decision pattern, erasing extreme viewpoints, minority perspectives, and subcultural variance5.  
Overcoming the Replicant Effect requires structural interventions:

* **Reinforcement Learning via Group Relative Policy Optimization (GRPO)**: Fine-tuning local small models using GRPO with multi-agent contextual rewards significantly improves social reasoning diversity and resistance to homogenization21. System-level rewards incentivize behavioral variance aligned with explicit persona parameters6.  
* **Multi-Model Ensembles**: Rather than serving all agents from a single model checkpoint, populations should be partitioned across distinct model families (such as mixing Qwen2.5, Gemma-2, and Llama-3.1 instances)4. Diversity in base model pre-training distributions prevents structural convergence6.  
* **Explicit Memory Reflection Loops**: Integrating reflection mechanisms—where agents periodically synthesize recent memories into high-level subjective generalizations—maintains individualized belief divergence over time1.

### **Conformity Cascades and Social Groupthink**

Language model agents exhibit a high degree of implicit conformity bias, matching patterns described by Asch's conformity experiments and Social Impact Theory19. When placed in multi-agent group discussions, agents frequently abandon correct internal beliefs or established persona traits to agree with an inaccurate majority consensus19. In a social simulation, this produces artificial groupthink cascades, where misinformation propagates unchecked across local subgraphs19.  
To counter unintended conformity cascades, frameworks must enforce two structural safeguards:

* **Isolated Private Evaluation**: Before an agent processes peer messages in a public forum, it must first execute an isolated generation turn to document its private stance based solely on its internal state and memory1. This private stance is then passed as an explicit context constraint during public generation turns, increasing the model's resistance to group pressure20.  
* **Source-Weighted Trust Filtering**: Agents must evaluate incoming claims through a trust filter that weights peer input based on historical affinity and source credibility, preventing uncalibrated consensus shifts11.

## **6\. Synthesis and Architectural Blueprint**

Building a scalable hybrid social simulation requires decoupling deterministic graph operations from semantic generation2. The overall system operates across three integrated execution tiers:

> 1. **Tier 1 (Deterministic Agent Engine)**: Evaluates background transmission, exponential memory decay, spatial interactions, and relationship graph topology across the full agent population2. Activation timing is governed by a data-calibrated self-excitation process (Hawkes process) to ensure realistic bursty timing (![][image5])4.  
> 2. **Tier 2 (Local Small-LLM Hub Layer)**: Processes high-centrality opinion leaders and local conflict nodes2. Utilizing dynamic interaction strategies based on local confusion indices, nodes at information conflict boundaries dynamically switch to local 3B to 8B models (such as Qwen2.5-3B or Qwen2.5-7B) operating in FP8 or INT4 precision2. Structured output grammars guarantee valid JSON state write-backs into the primary graph14.  
> 3. **Tier 3 (Large LLM Conversation Layer)**: Triggers high-capacity foundation models on demand during direct player interactions or critical world events1. The layer sanitizes external text inputs, applies citation checks, and logs conversational updates to persistent memory storage3.

By combining deterministic propagation, dynamic role switching, constrained grammar decoding, and low-priority CUDA stream execution, this hybrid architecture enables rich, persistent social dynamics while maintaining real-time frame rates on consumer GPU hardware2.

#### **Works cited**

> 1. From Skepticism to Acceptance: Simulating the Attitude Dynamics Toward Fake News | Request PDF \- ResearchGate, [https://www.researchgate.net/publication/382788673\_From\_Skepticism\_to\_Acceptance\_Simulating\_the\_Attitude\_Dynamics\_Toward\_Fake\_News](https://www.researchgate.net/publication/382788673_From_Skepticism_to_Acceptance_Simulating_the_Attitude_Dynamics_Toward_Fake_News)  
> 2. RumorSphere: A Framework for Million-scale Agent-based Dynamic Simulation of Rumor Propagation \- arXiv, [https://arxiv.org/html/2509.02172v2](https://arxiv.org/html/2509.02172v2)  
> 3. RumorSphere: A Framework for Million-scale Agent-based Dynamic Simulation of Rumor Propagation \- arXiv, [https://arxiv.org/html/2509.02172v1](https://arxiv.org/html/2509.02172v1)  
> 4. Unveiling the Truth and Facilitating Change: Towards Agent-based Large-scale Social Movement Simulation | Request PDF \- ResearchGate, [https://www.researchgate.net/publication/384209675\_Unveiling\_the\_Truth\_and\_Facilitating\_Change\_Towards\_Agent-based\_Large-scale\_Social\_Movement\_Simulation](https://www.researchgate.net/publication/384209675_Unveiling_the_Truth_and_Facilitating_Change_Towards_Agent-based_Large-scale_Social_Movement_Simulation)  
> 5. Abstract \- arXiv, [https://arxiv.org/html/2507.19364v2](https://arxiv.org/html/2507.19364v2)  
> 6. LLM-Based Social Simulations Require a Boundary \- arXiv, [https://arxiv.org/html/2506.19806v3](https://arxiv.org/html/2506.19806v3)  
> 7. SAPIENT: A Multi-Agent Framework for Corporate Reputation Intelligence Through Sentinel Monitoring and LLM-Based Synthetic Population Simulation \- MDPI, [https://www.mdpi.com/2079-8954/14/4/425](https://www.mdpi.com/2079-8954/14/4/425)  
> 8. Large language models for spreading dynamics in complex systems \- ResearchGate, [https://www.researchgate.net/publication/400603980\_Large\_language\_models\_for\_spreading\_dynamics\_in\_complex\_systems](https://www.researchgate.net/publication/400603980_Large_language_models_for_spreading_dynamics_in_complex_systems)  
> 9. \[2509.02172\] RumorSphere: A Framework for Million-scale Agent-based Dynamic Simulation of Rumor Propagation \- arXiv, [https://arxiv.org/abs/2509.02172](https://arxiv.org/abs/2509.02172)  
> 10. A Collaborative Multi-Agent Framework for Fake News Detection, Explainable Verification, and Logic-Aware Claim Rea \- arXiv, [https://arxiv.org/pdf/2604.12184](https://arxiv.org/pdf/2604.12184)  
> 11. (PDF) TRUST Agents: A Collaborative Multi-Agent Framework for Fake News Detection, Explainable Verification, and Logic-Aware Claim Reasoning \- ResearchGate, [https://www.researchgate.net/publication/403823501\_TRUST\_Agents\_A\_Collaborative\_Multi-Agent\_Framework\_for\_Fake\_News\_Detection\_Explainable\_Verification\_and\_Logic-Aware\_Claim\_Reasoning](https://www.researchgate.net/publication/403823501_TRUST_Agents_A_Collaborative_Multi-Agent_Framework_for_Fake_News_Detection_Explainable_Verification_and_Logic-Aware_Claim_Reasoning)  
> 12. agentsociety \- PyPI, [https://pypi.org/project/agentsociety/](https://pypi.org/project/agentsociety/)  
> 13. GitHub \- Nicolas99-9/llm-agent-simulation-papers, [https://github.com/Nicolas99-9/llm-agent-simulation-papers](https://github.com/Nicolas99-9/llm-agent-simulation-papers)  
> 14. LLM Structured Output: JSON Schema, Pydantic, and Schema, [https://www.openlegion.ai/en/learn/llm-structured-output](https://www.openlegion.ai/en/learn/llm-structured-output)  
> 15. Guided Decoding and Its Critical Role in Retrieval-Augmented Generation \- arXiv, [https://arxiv.org/html/2509.06631v1](https://arxiv.org/html/2509.06631v1)  
> 16. vLLM GPU Sizing Guide for LLM Inference, [https://www.centron.de/en/tutorial/vllm-gpu-sizing-guide-for-llm-inference/](https://www.centron.de/en/tutorial/vllm-gpu-sizing-guide-for-llm-inference/)  
> 17. arXiv:2501.15283v1 \[cs.CL\] 25 Jan 2025, [https://arxiv.org/pdf/2501.15283](https://arxiv.org/pdf/2501.15283)  
> 18. GA-S3: Comprehensive Social Network Simulation with Group Agents \- ResearchGate, [https://www.researchgate.net/publication/394273616\_GA-S3\_Comprehensive\_Social\_Network\_Simulation\_with\_Group\_Agents](https://www.researchgate.net/publication/394273616_GA-S3_Comprehensive_Social_Network_Simulation_with_Group_Agents)  
> 19. Conformity and Social Impact on AI Agents \- arXiv, [https://arxiv.org/html/2601.05384v1](https://arxiv.org/html/2601.05384v1)  
> 20. Do as We Do, Not as You Think: the Conformity of Large Language Models \- arXiv, [https://arxiv.org/html/2501.13381v1](https://arxiv.org/html/2501.13381v1)  
> 21. LLMs Can't Handle Peer Pressure: Crumbling under Multi-Agent Social Interactions \- arXiv, [https://arxiv.org/html/2508.18321v1](https://arxiv.org/html/2508.18321v1)  
> 22. Pole-Anchored Measurement of Relational Positioning: History-Carried Lock-in and Self-Confabulation in Multi-Turn Human–AI Dialogue \- arXiv, [https://arxiv.org/html/2607.11437v1](https://arxiv.org/html/2607.11437v1)  
> 23. Pole-Anchored Measurement of Relational Positioning: History-Carried Lock-in and Self-Confabulation in Multi-Turn Human–AI Dialogue \- arXiv, [https://arxiv.org/pdf/2607.11437](https://arxiv.org/pdf/2607.11437)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAAAWCAYAAABJ2StvAAADMElEQVR4Xu2Yy6tOURjGl1uEEmIsJXKJXKMoEykDAxOJkWTATES5TIT8BS4DkTLCQEkiAwMyMJCUiIm7SK4J8T7nfdfp/Z6z1lnrfF8nX+xfvfW9z37Ws/de59t7re+E0NDQ0NDwv7GEhTZYITWcRWKs1CwWE9RklcD4hVKj+QABz2IWCWTBU8oqMlJqrdRlqd9W7bJP6l7Qizso9VpqTotDPTjHUqlJUr9CXw+Ah7Pa4bPU+qATtVHqe+vhHlZLvQvqGSP1QWpTi0OJWfDksqoZLzXXPncy8ZgYHvuRtBHW73UaJh/aAachy3sAsrynhgtS10i7JXWDNL5uwFptVor3LDCdTHxq7AnTplt/3fpxvQ6Fx6Y8nFUD/HiaPRtMj8QnkIG2lfpSVg58afqFJ6CWeUHHfSJ9v+knrU95gD9vzGI4qwb4F5CGNcPn47WSOh+0R9SXsnJ8YYFpd+LxTcA4vCc9e0w/b33KA/x5YxbDWSXwxMDP6wfWFp+fu2d/rbVZOb6ywOQuosSWoONekb7DdCySIOUB/rwxi+GsEtOC+meQjm8t9AnW5+7Z67VZOQZt4tcFHfeG9J2m37Y+5QH+vDGL4awSE4P6Z5K+yPRR1ufu2eu1WUOC7ni4MPG+70PuIkpgP45xvIjE9/Ip61Me4M8bsxjOqgH++aTxe/kt9RFoT6kvZWGHuCZR2Hb6vg9+AgbC5KDjfpJ+xPSj1kcPvhkef96YxR7OqgH+5aRhz+7v8QH1EWh3qC9l5Ri0Vw1Ijb1iWnwUD1k/u9ehQPNPQsqDLHhiFuA/DoOc7aTtNj2yivoItGXUl7JydDTx/R0DN4Me9z/v0eOXqQfafddvDurBDiGCLHg4y3uGmdbfNeEX7zfSfkjtIg0ZU1yPRZRza7NSJCd+aNC9LHYbL6zwy5H3nljcHgddaHJgu4ULPhb0Ire1Hu4BnidBdycXQ+aignpKWXelngVdkHNclXoudVrqpdTx1sM94N2Mc8Fzxj6n/hcTs+DJZaXI3WM1mPxuAzuLqSx2GR1P/CUWugDs77udwywMBOw/z7L4lzkn9ZDFfw3eZXQDK1loaMjyB3EsI0ipcMs7AAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAXCAYAAADtNKTnAAAA/0lEQVR4XmNgGDFAD4g3AvEcILaDiiUhpAmDL0DcjsTPBuKLQPwPSQwvsALiP+iCQPAfiC+jC2IDaQwQxQLoEkCwCYhD0QWxgd8MEENY0SWAYD66AC7wkwFiCMg78mhyRIPNDBBDYHgqEAeiqCAS2DOgGgTCf1FUkAjigPgFA8QgUzQ5rGASugASABmSikUMAxxDF0ACIA3sSHxGIH6PxAcDQSB+gi4IBUwMmLbqAPF6NDGGXgZM20DAGYh/ALEMkpgaEO8DYh80cXgyf8YAMQxEgzRPYMBML9oMmC4jGaxkoIIhoCj/DGWDkgBZAOQKUBkDSpQcaHIkAUl0gcEBAMd3NnpWxsWtAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD0AAAAXCAYAAAC4VUe5AAACrklEQVR4Xu2WS+hNURTGF/IoJI+EQgZKQpE8xuYUKZEMlGQgE0TIAAMKI49koDxGMhCKdCWFmCiSVylFyWNAlPf67L3ctb+zz3XO/Zfuzf9XX+eu7zuPvc85e50r0ksvncxoNiowio1u4jsbFbmrGmnFTNUh1c+oM6r9Fkb6qJ5JyF+oVqXxP+OhahibNcD4Ez7mTMcgCfkADipygY02aDW+KjxQzfXGAgknXe1NxyTVUTZr0NMB71AdYLMm9uASYPxQTeRAecRGDUZI5mI1WC7heCyznlIYx+1o5iaIm1HGEQnHvVNtomxRzKBdUVuTPUQGqq6ovqpOUQbQRwqDjQxWXVQtJP8O1QZ6U8I6aQ7Q01/VIM84qLqnmq9aIuHYqS6383m9cfkY1U3VNdWcmK90OciNybiqWi9pPiPWuJnMaTaAXcA3rLOqIa42Nkh+MPD6unpL9HLA/+Zq3AR4+IoYZZOeIOFG41qco8bkmW1sgNcSDjgXa3v6OeDjSTPwL7u6bNIbJfhYHh6eJH5/crWxJm4PS/H8DaqNFWyAWZJeFNvdzTgBGdYoY8ePjXXZpK9L8I+r5mVkYJ8PrmaQ7yUP/SHHMjYMewLTJKy3MrDPCTYl+HhjjM3RMx7H7c7on2xGWfxDyIGsH3l7qDa4if5hnIQT3VKtpcyDfW6wKcHHK2ego/tBP4lba1xPXQawRpe6utWk0WQ5myJpM/XsY8PT6kLGdAn7+KaFLs7H4V+Q9/znz3rIZOe9lHTtvZXiOT2cfabac58NzzEJF/8bWLf4BNlNwjczR0Oa++BN8gxXvY/ZF9XQNP79tvHEPNZssY6fp1GBVufpOC6ptrNZE7yRrf5kdRyzVa/YrMliST+lXQHWKhpXu3TVq+1pd+DnpdhLuorxbFSg7BP2f/ALXHW6EEaCmwQAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFUAAAAXCAYAAAB6ZQM9AAABiklEQVR4Xu2XOUsEQRCFywNRQUWQBQNNNBQjTf0BipiYLAaCJoKpoYE/wCMRzA08/oOCmAgKIh5gLoKhIILiWUV16/Rjmm002qY+eDDzXs9C13bX9BAZhmEENBRk/JNh1gbrgPXF2mGts1ZZm6wX5/f5B4x05kmLhwyR+iesZsiMGtxSeVEF8UXLGBhxpkmLdoaBQ7I3VicGEQadatGKRk5ckRZuHAPmjjRrxKCENdYr65R1SPpcNRgRMoFGTnySFgBX4qLzZ8GPIWN7C/crzpOXIDLF6kczJ3zP3CN9+++663fSU0AKHaxuNB0jpL9/zTp21+fBiMyokE5SCliGZI9o/hHpoSm9tu7ZIi2c9MMynkjzVB7od+VvQ4bMoJELMvkPim9dX6AUZFxb4X7OeTcFz7PAakczF2TSF2g6ukjzI/BjLKFB6j2TngZanCe7IvWPqjvkO18mN4kBM0qaXWIQoQcNYIx1T3rSkFXaFMZ5IOdJ2fZ+e3uJJ31xnzXwM9owDMMwDMMo8A10slhcUKsowwAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFEAAAAaCAYAAADPELCZAAAC8klEQVR4Xu2XS6hOURiGP7fcBshxjY4MiEIxwEgykEwIAzMMkUsZuHU6UnIrIszEDJmQJFIoiUJyzcAhBgyImLj73r61zln7ba397/0Xp7Seeuvf77e+tfda/7qKZDKZTCbFdNUT1dNAeH6oeqC6rprdWbr76KtqZbMiM9gIWKzqz2azLFf9ZlOZL+ZfVPWg2L8C75+jGud+dxSiaTAA9qvGqO6J5baHBZRHzo/pdVCuEncl3onAV9pO/t+mj+qdamvgtaq+qtYEXoyeYt+MweG54TzPePd8QnVQtU+1V7XH+bVYKJaEaRzDd+JoDiQYoOrHZgQ0tIyrYu9FfSGnVL/Ii4HctcEzlqqwczaq3gfPniOqqWw24o5Y5Us5ILYuIlZl3dgkVvaNdH3w3EKJIsvYIPyfx2CKxvwyFojlfOMAMUp1ms0q/BB7wbDA66Va5PztgV/GT9WU4PmYWP7IwPPMUk1mk0h14i6J+2XcF8tZQT5zSTWYzSr4j8X0uay6Ija10blbgnJlYMoNZ9PxXKz+a6qz7veLsECCVCfukLgfw8+kj9J45GMjQZtrM0TsJak1BrHYutEMGOkz2Swh1Yk7Je6XgWmKP/M7Bxw4eaDONg5U4ZBY8mEOOD5IvQ/ukK7GY4EuYyUbRKoTsYvG/EbME8s7yQHlvFhsIgeq4M9JSzjgSDUkxnHVJ7F15YxY3rpCiSKpd3pS7z4qcZ/BGTcEyw3yYqcQzDZsOtgLaoNKH7PpGCgWv82BBNvYEDvjYanAYb2387CmYRNqhD+v8ei4qXpLXgjOl1/EcscG/iTnIZ+Bj+neFEjG1Yfxu9kzDiRoYYPAUQcNR50bxBpahVtitw3PerE6wnPcNOcdCDycDLCphPgpi8HBwMeFoxY49WM0IDkUPNwSVqsmdJbuXl6K/annVJ9VqwpR45VqBHm+03D9821LHV8Qj62V/w0YtVgHcSUbRLFGYIm5oNosds1LsVs1lM1MJpPJZDKZTKYOfwAz+cpBLVAB6AAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD4AAAAZCAYAAABpaJ3KAAABuElEQVR4Xu2WSytFURTHl7cBKUoxoJQSyswHMCUjBjIwMMA3MFTkUQYSMyVfgZKMJUopmRiJgWdC8iqv/2rtU8vS4WzHwL3tX/26d//XOqfW3efsLlEgEAikp9AG2UwVHITb8N3UshoeuhS2U4YPXg7P4Iwt/EBGDz4L7+GIyZOQkYOvwX1YYAse+AzOfZG18BouufWA69l12SvcgSUuZ4bgE8kG9ZBcN6/q39IPD+CKLfwSn8GZOZL+Z5VF99D3yXfrY5XxelGtcyjB4KMkj3ONLaTEd/Apkn7evYgml22pjLE/RrRegHUqj4UPLr6gwhb+AN/BJ0j6e1XW4LJVlTF28D2VsZOqFksuyfuzDttMLQ2+g/OTx/3dKqt32bLKGDt4xDC8JKnxOZWYVpLDg9/3tPgOPk7S36WypIOfkrz7Ec0k9T6VJYL/fd3CMVhpaknxHXyapF8/6o0us7tnB+fvG2pdDB9hmcq8KCLZ/RfYYmpx8EF5TrILJyR/fm4+dXyFT/Lomgt4Bzfdd8649kBy8PGjzJm+7xHsJPkBruChy1PTAd9s+I+oVp98TuWpWiAQCAQC2cYHdc96v4+rOhUAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADQAAAAZCAYAAAB+Sg0DAAAB7klEQVR4Xu2WTShuURSGlytuSKEkfwMGkoSJkjLwMyITpW7KQBkIAzNMMJE7u3XviJSBzExNjEyNMfM3UEg3mUgI622vnWU55yPH36nz1Nu31/ues89Z39lnfx9RQkJCQgilrFxrfjK91ojCNKvcmp/MtTWicEVf39C9NaKAyb6yoWZ6p4YGyU1kBfKMt8vaYZ2zalgr5njQpbw65Q+zNlkzrD7J/0p2JLVVJDBB2BOaIpcXsyZYl6xayYoks9iG7DE/6LEh0ETPj4lEqobGKPxi2RScBTV0wVpkVSrf820a+knBmW1oSzyvOZWBD2moQtVpapyqISydoMw2BBpYk6wzcvmaymxD6Wr8JjBZlYzxrrSoLFVDICiDhwY8x2oM6unpeY2mnldjbCa/yK2GbdaQykLBZNh9wCgrR2XjFHzTHmR4Up4/4uEmPKizVI0xNhdPBj1eA0/nRMYj8omsW8ZYvi/SSu4kaFW8AtZ/1im5bxhL5Z9kGlwU592y7si9i34uf5OHrHWpMee++JoFcjmu0678DtayqnHMq/6mYRlUW/OVYHl1ssqkxu8RlnCh1CXqs43C3xE0Ym92ljWg6lSrJRbcqDF+9zZUHUvwRPbIvQq/TRY78lkH1owzPawla8YVbO395DaETJMlxJIH6dCAZbvfvFkAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAaCAYAAABRqrc5AAAA3ElEQVR4Xu2TzwpBQRSHh0ewZUmxk70XkLDwBFKUspC1rdh4Axs2omTBA3gCKdnbyANYWPjzTXfUzFHcaylffXXO73TP1DRXqT9/viONSxzIgV8WeMcRrrHnjj9zwa7V62VXjFrZWybK+8gmhyGRvUUvmMkwKHpJQ4ZB0UtiMrTQd7XHJO6ML5yxKbIKTjGMWeUdFDGzDHZM7bDFEx7xgAl37Fx8C8dW75DHsgwNN6vW76lt9b4o4tDUdfX6HHyxwT6usCBmvvnq5CcpnCtvSeD/6Ekca1jFkpj9Kg80Rig+U5NzPgAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAAzElEQVR4XmNgGAU0AMJA3AXESUCsjyYHA94MEPmT6BIgoAjEh4H4OBCfgGIQezuSGpAljkh8fACrJTBwH4lth8QGAapZ8gKJbYHEBgGqWfIaiW2OxAYBqlnyBolNF0vMkNggMLwtmQ/Ev9DEQICqlvwF4v9oYiBAtCXERLwsEGejiYEAXkvokk8eIbFtkNggQLElOkD8jwESvjAM4v9AUkOxJcSAUUtIAiBLXICYBYgZ0eRggJkBIk+RJbBEUY0mBwNHGCDyZFsyCsAAAF0KNhfRg4EKAAAAAElFTkSuQmCC>

[image11]: <data:image/png;base64,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>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAXCAYAAADUUxW8AAAA1UlEQVR4Xu2RzQpBURRGP0oxlfI8zJSJB5GnEIoyNTAlE3kAL2CiDJWhGcpEUf6+bZ/LtZ0rMyWr1sBe+1zXAfwUsZAfU6ANuqAXuqRt2qQdOnfzXHDAxxC6VDbzlJtvzPwJWVjB/9ozaI9EYsUOHdIiD2egMW4D6UJb1oaAEvxPHkHnLRvCTKFLfdpzygXKJQ1Cey8UoQfHNkB/zhH+t7oxgca8DQ75zyMPv7vJJF0jur89XIe2rQ1CGhpPNpAqtO1sEA70jMc3i/JZ3NMaTdy3/3yBKy1FPAG9KWXeAAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAXCAYAAAD6FjQuAAABZklEQVR4Xu2UPyuFYRjGb5FIWWRlULIomw9gsBj4AFIMyuADUGZCWWxSyiCbxWJUksGEbEoGpfyNyb/r8tzHec517lPnLCznV7/Oea/7ud/nOc953teszh8wCFfhHpyT2phckwa3JhbgF1yHTZ51wA84CT9hp+dkEa5Z6mGN31fgJnz3rOV3dEa3paYjLYAJSzUawfxUsl7PDyW3Ey/MaiGj0mTcPuYjWgA3Jj1bHpznYUClMTMWL4KULZAX17AxDwM4LjoctxZP1mUpnyoEAx7oiYvgQdET12epn4dB4Q94zYNLi1dVLTtW3Cq1Jxv3Q9me1kihv13yN3gvWdWTXWngVOrftyA/jkKhGW5rCPot9fKBV8JFTHuof3zOkpW+NQrwmWSvPswknIxwf+/gsOStcNni406eLN1wVAtWOtlQXiC7Vhxw5p/zsC0f5BzAF/gAH+GzpXdgzrile2zAC6nVqfOPfAOXTWfVgQ7RzgAAAABJRU5ErkJggg==>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABcAAAAXCAYAAADgKtSgAAABK0lEQVR4Xu2Uu0oDURiERysRbDSNYmfnU1jkDUSCiCBYWlqlELEMgkHEFAErBR8jXSoLCxEERXwA8YKioKjz778bj+M5MY3dfjDNzJxhl70AJf/EkBoplqgWdUp9Ul2qSS2HJVKntqlneG+P2qH2qcvcq/bawha88NdVPcJ7IcPULfUhfsYI9Yrfh2JY50xNsoDE+U14cKFBBOvNq0mOkRh/gQeLGgirSAzA/Ws1DQtMkxoIh4iPb8D9KQ2MYrwfM/juqWpB7wdzGGz8CN7ZFb+R+1E68LCtgVBcQEX82dyfED+jODStgZC6uwPE/QwLrtQU7MNKjd8g7mMcHqyIr6zDe+cakDfI+Cj8H/FA3cE/aXvX18IS/GE/Ufe5rP8eFsgYfPwkkpWU9OEL+ytYL9Z+Q5cAAAAASUVORK5CYII=>