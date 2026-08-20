# **System Architecture Report: SkyrimNet Platform Risk Sizing and Save-State Timeline Reconciliation for External AI Services**

## **SkyrimNet Ecosystem Health and Platform Risk Assessment**

Evaluating SkyrimNet (github.com/MinLL/SkyrimNet-GamePlugin) as the primary integration substrate for an external social-simulation service requires sizing both its architectural merits and its structural platform risks. SkyrimNet operates as an in-process Skyrim Script Extender (SKSE) C++ plugin that exposes runtime Papyrus script interfaces and public C++ DLL entry points1. While its direct-memory inspection and single-plugin architecture offer performance advantages over multi-process bridges1, its distribution model and governance structure introduce distinct platform liabilities.

### **Financial Sustainability and Velocity Metrics**

SkyrimNet exhibits rapid development velocity alongside structural single-maintainer dependencies. The project maintains an active release trajectory, progressing through major feature iterations—including Beta 20 (NPC thoughts and knowledge authoring)2, Beta 22 (quest journal awareness)3, Beta 23 (native game audio spatialization)3, and hotfix releases such as Beta 23.1-rc23. Development activity remains tightly concentrated around its creator, MinLL1.  
The project relies on community funding via platforms such as Ko-fi1 rather than structured organization-backed sponsorships or formal corporate backing. This creates a high bus-factor risk: while commit frequency is high4, the lack of an institutional maintainer base or formal governance model means project continuity depends almost entirely on a single developer.

### **Community Size, Governance, and Integration APIs**

SkyrimNet has cultivated an active community of modders and contributors who build peripheral extensions and UI tools. Community developers regularly submit pull requests for web dashboard enhancements, chat interfaces, and extended action sets2. However, a fundamental asymmetry exists between SkyrimNet's peripheral modding layer and its core engine:

* **Source Code Access and Licensing**: Public repositories expose Papyrus source scripts (.psc), serialized database definitions, and web dashboard assets, but omit the source code for the core C++ SKSE plugin DLL1. Furthermore, the repository lacks an explicit open-source LICENSE file1.  
* **Legal and Forking Constraints**: Because the compiled C++ core lacks an open-source license, third-party developers have no legal path to fork, fix, or compile the core DLL if development ceases or if unpatched game-update crashes occur.  
* **Exposed Extension Interfaces**: Third parties integrate via Papyrus bindings (RegisterEvent, RegisterPackage, RegisterDecorator)1 or the public C++ header PublicAPI.h (bumped to Public API version v9 in Beta 20\)2. Native entry points such as SendCustomPromptToLLM and PublicGetWorldKnowledgeForActor allow external C++ plugins to interact directly with SkyrimNet's internal context builders2.

### **Technical and API Stability Analysis**

A review of issue trackers, pull requests, and changelogs indicates that SkyrimNet's rapid iteration cycle introduces interface and runtime regressions across beta versions:

| Failure Mechanism | Root Cause & Manifestation | Impact on Integrations |
| :---- | :---- | :---- |
| **Action Cache Stalls** | Expiration timers refreshed on cache hits, locking eligibility states indefinitely3. | NPCs stuck in stale action loops during gameplay3. |
| **Event History Loss** | Events lacking an explicit originator ID were dropped from the event queue4. | Ambient world events vanish from long-term memory4. |
| **Port Resolution Failures** | Hardcoded port 8080 assumptions broke non-standard web configurations3. | Dashboard and tutorial audio tests fail on custom ports3. |
| **Version Drift Breaks** | Public C++ API version bumps break binary compatibility across major beta shifts2. | Requires downstream native C++ plugins to recompile2. |

### **Ecosystem Consolidation vs. Single Point of Failure**

The deprecation of MinAI and its explicit redirect to SkyrimNet7 represents a major consolidation within Skyrim's AI-NPC modding landscape8. While this consolidation concentrates community effort onto a single high-performance runtime, it concentrates platform risk:

| Attribute | Fragmented Ecosystem (Mantella / CHIM / Herika) | Consolidated Substrate (SkyrimNet) |
| :---- | :---- | :---- |
| **Execution Model** | External Python/C\# processes; IPC via HTTP/WebSockets7 | Single SKSE C++ DLL executing in-process1 |
| **Memory Latency** | High; serialization round-trips across process boundaries1 | Low; direct C++ memory pointers to game data1 |
| **Code Access** | Open-source Python/C\# backends (MIT / GPL)9 | Closed-binary SKSE C++ core; no license file1 |
| **Failure Impact** | External service crash leaves game runtime running1 | C++ core exception risks Crash to Desktop (CTD)1 |
| **Ecosystem Dependency** | Distributed across independent projects | High concentration on a single closed binary1 |

### **Comparative Substrate Strategy and Risk Rating**

To insulate an external social-simulation service from platform risk, integration architectures must be evaluated across two deployment models: primary direct coupling versus an abstracted hybrid model.

| Metric / Dimension | SkyrimNet Direct Coupling | Standalone Fallback (PO3 Extender \+ SKSE\_HTTP) |
| :---- | :---- | :---- |
| **Runtime Primitives** | RegisterEvent, RegisterPackage, RegisterDecorator \[cite: 1\] | Papyrus mod events, PO3 script functions, raw HTTP/WS |
| **Latency Profile** | Direct C++ memory reads; zero-serialization1 | IPC payload serialization (JSON over HTTP/WebSocket) |
| **Maintenance Risk** | High; single maintainer (MinLL), closed binary1 | Low; PO3 Extender and standard HTTP bridges are open source |
| **API Drift Resilience** | Low; C++ API v9 bumps break compiled integrations2 | High; standard Papyrus interfaces remain stable across game builds |
| **Licensing / Forkability** | None; no LICENSE file in repo, DLL binary only1 | Fully open-source ecosystem standard |

#### **Risk Rating and Architectural Recommendation**

Building directly against SkyrimNet's internal APIs as the sole dependency carries a **HIGH RISK** rating. Building directly against SkyrimNet without an isolation layer creates an existential dependency on a single maintainer's closed-source DLL1. Any unpatched game update or project abandonment would freeze external service integration without a legal fork path1.  
Conversely, adopting an abstracted hybrid architecture carries a **MEDIUM RISK** rating. Chronicle should construct an internal Substrate Abstraction Layer (SAL) from day one, defining domain events against a generic Python interface. The primary provider can target SkyrimNet's Papyrus/C++ event pipeline to leverage low-latency state access1, while a secondary provider implements the baseline using powerofthree's Papyrus Extender and an open-source SKSE HTTP/WebSocket bridge. This hedges against binary deprecation while preserving performance benefits.

## **State Reconciliation Under Player Save/Load/Reload Dynamics**

Skyrim's core gameplay loop relies on continuous save-scumming, timeline rollbacks, character deaths, and multi-save slot management. External social-simulation engines maintaining state outside the Skyrim engine process face a state reconciliation problem: if a player assassinates an NPC, triggers world rumors, and subsequently reloads an earlier save, the external state store becomes out of sync with the active in-game timeline.

### **Analysis of External State Corruption in Existing AI Frameworks**

Existing AI modding implementations exhibit varying degrees of timeline desynchronization when players reload earlier saves:

| Architecture | Memory Persistence Mechanism | Behavior on Player Save Reload / Rollback | Failure Mode |
| :---- | :---- | :---- | :---- |
| **Mantella / Pantella** | Local CSVs, JSON text logs, and ChromaDB vector stores9 | External files are not rolled back on save reload10. | Summaries retain unhappened events, causing narrative context contamination10. |
| **CHIM / HerikaServer** | Out-of-process relational database server7 | Database records persist independently of .ess saves12. | Requires manual DB purges or administrative resets to align state after rollbacks12. |
| **SkyrimNet** | In-memory buffers & internal SQLite storage1 | Rollbacks leave unhappened events in recent event queues13. | Narrative events persist unless state is manually cleared or reloaded prior to event13. |

### **SKSE Co-Save Serialization Architecture**

The standard mechanism for synchronizing mod data with Skyrim save files is SKSE's co-save system (SKSE::SerializationInterface). SKSE writes custom data blocks directly alongside Skyrim's standard .ess save files, producing a matching .skse co-save file6.  
To maintain atomic tracking between external services and in-game saves, the SKSE C++ plugin implements serialization callbacks that embed timeline metadata directly into the save archive:

C++  
namespace ChronicleSync {  
    constexpr uint32\_t kPluginSignature \= 'CHRN';  
    constexpr uint32\_t kSerializationVersion \= 1;

    struct SaveHeader {  
        uint64\_t timeline\_uuid\_high;  
        uint64\_t timeline\_uuid\_low;  
        uint32\_t save\_epoch;  
        uint64\_t last\_event\_id;  
    };

    void OnGameSave(SKSE::SerializationInterface\* a\_intfc) {  
        if (\!a\_intfc-\>OpenRecord(kPluginSignature, kSerializationVersion)) return;  
          
        SaveHeader header \= GetCurrentTimelineState();  
        a\_intfc-\>WriteRecordData(\&header, sizeof(header));  
    }

    void OnGameLoad(SKSE::SerializationInterface\* a\_intfc) {  
        uint32\_t type, version, length;  
        while (a\_intfc-\>GetNextRecordInfo(type, version, length)) {  
            if (type \== kPluginSignature && version \== kSerializationVersion) {  
                SaveHeader header;  
                a\_intfc-\>ReadRecordData(\&header, sizeof(header));  
                NotifyExternalServiceLoad(header);  
                return;  
            }  
        }  
        InitNewTimelineBranch();  
    }  
}

The co-save interface records raw byte arrays tagged by unique four-character record identifiers6. Co-saves share the exact filename and lifecycle of the parent .ess file; if a player copies, moves, or deletes a save slot, the corresponding .skse co-save moves or vanishes alongside it. By storing a 128-bit Timeline UUID, a monotonically increasing Save Epoch, and the Last Event ID inside the co-save, the external service can determine which timeline branch a save load belongs to before any Papyrus scripts execute or unroll.

### **Event-Sourced Timeline Management and Branch Pruning**

By employing an event-sourced core, the external social-simulation service models the game's state history as a Directed Acyclic Graph (DAG) of immutable world events rather than a single linear timeline.  
Let the global state ![][image1] at any instance be a function of the initial state ![][image2] and a sequence of applied events ![][image3]:  
![][image4]  
When a load operation occurs, the game restores state to a prior checkpoint corresponding to event ![][image5] where ![][image6]. Instead of overwriting event history from ![][image7] to ![][image8], the service creates a new branch identifier ![][image9]:  
![][image10]  
![][image11]  
To prevent unlimited graph expansion from frequent save-loading, the external service implements a three-stage branch pruning pipeline:

> 1. **Epoch Tagging**: Every save action increments the save epoch number ![][image12]. Events generated during gameplay inherit the active ![][image13] tuple.  
> 2. **Orphan Identification**: The service maintains a map of known save files and their corresponding active branch heads. A branch that has no associated save files on disk and has produced no new events for a configurable retention period (such as 48 hours) is designated as an orphan branch.  
> 3. **Pruning Execution**: Orphan branches are pruned by dropping their unreferenced event subtrees from the database, consolidating storage while preserving shared ancestor nodes.

### **Runtime Detection, Race Conditions, and Sequence Ordering**

Detecting game load events at runtime introduces synchronization race conditions between the Skyrim engine thread, SKSE C++ callbacks, Papyrus VM execution, and external IPC transport layers:

* **SKSE Callback vs. Papyrus Execution**: SKSE's load callback fires synchronously while the game reads the .skse co-save file off disk. This occurs before the game world is fully rendered and before Papyrus scripts unpause. Conversely, Papyrus OnPlayerLoadGame events fire seconds later, after script engines initialize.  
* **Event Leakage Hazard**: If an external service accepts incoming game events (such as location changes or actor perception updates) immediately after game engine start but before the load handshake confirms the active Timeline UUID, those events risk being written to the wrong timeline branch.

To resolve these race conditions, the system enforces three execution ordering rules:

> 1. **Data Freeze**: The SKSE plugin must buffer or discard all outbound runtime game events from the moment a save load sequence begins until the external service acknowledges the timeline switch handshake.  
> 2. **Preemption**: Timeline branch resolution must occur during the C++ SKSE load callback phase, prior to releasing the Papyrus VM pause lock.  
> 3. **Handshake Acknowledgment**: The external service must reply with an explicit acknowledgment payload containing the verified Timeline ID before the SKSE plugin opens event transmission pipelines.

### **Recommended Synchronization Protocol Specification**

The formal synchronization protocol specification governs communication between the SKSE native bridge plugin and the external service.

#### **Message Payload Definitions**

##### **Save State Checkpoint (SAVE\_NOTIFY)**

Triggered inside SKSE's save callback execution window:

JSON  
{  
  "protocol\_version": "1.0",  
  "event\_type": "STATE\_SAVE",  
  "payload": {  
    "save\_filename": "Save4\_4A12BC89\_0\_6772656174\_Whiterun\_000812.ess",  
    "timeline\_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",  
    "save\_epoch": 14,  
    "last\_confirmed\_event\_id": 89201,  
    "game\_timestamp": 172.45  
  }  
}

##### **Load State Handshake (LOAD\_REQUEST)**

Triggered inside SKSE's load callback execution window:

JSON  
{  
  "protocol\_version": "1.0",  
  "event\_type": "STATE\_LOAD",  
  "payload": {  
    "save\_filename": "Save2\_4A12BC89\_0\_6772656174\_Whiterun\_000210.ess",  
    "timeline\_uuid": "f81d4fae-7dec-11d0-a765-00a0c91e6bf6",  
    "save\_epoch": 4,  
    "last\_confirmed\_event\_id": 41025  
  }  
}

##### **Service Response Handshake (SYNC\_READY)**

Sent by the external social simulation service back to the SKSE C++ plugin:

JSON  
{  
  "protocol\_version": "1.0",  
  "status": "SUCCESS",  
  "action": "BRANCH\_MUTATED",  
  "payload": {  
    "active\_timeline\_id": "TL\_f81d4fae\_FORK\_002",  
    "parent\_timeline\_id": "TL\_f81d4fae",  
    "restored\_event\_id": 41025,  
    "purged\_uncommitted\_events": 4816  
  }  
}

#### **Protocol Execution Steps**

The synchronization sequence proceeds through five defined phases during game runtime:

> 1. **Save Interception**: When the player triggers a save, the SKSE C++ plugin intercepts the event via SKSE::SerializationInterface6. It writes the current Timeline UUID and Epoch into the .skse co-save file, then transmits a SAVE\_NOTIFY payload to the external service. The service records a checkpoint node in its event DAG.  
> 2. **Load Interception and Event Freeze**: When the player reloads a save, SKSE's load callback reads the embedded .skse co-save header before rendering the world. The C++ plugin mutes the event pipeline, queuing or dropping runtime game events.  
> 3. **State Resolution Request**: The plugin sends a LOAD\_REQUEST payload containing the save file's Timeline UUID and Last Event ID to the external service.  
> 4. **DAG Branching and Pruning**: The external service receives the LOAD\_REQUEST and queries its event graph:  
   * **Exact Head Match**: If the Last Event ID matches the current branch head, the player reloaded the latest state. The service retains the current timeline.  
   * **Ancestor Match**: If the Last Event ID exists in graph history prior to the current head, the service forks a new timeline branch rooted at that historical event. Subsequent state changes are written to the new branch, leaving the abandoned branch intact for background pruning.  
   * **Missing UUID Match**: If the co-save contains no Timeline UUID (such as a vanilla save made without the mod), the service generates a new Timeline UUID and initializes a baseline world state.  
> 5. **Pipeline Unmute**: The external service returns a SYNC\_READY acknowledgment. The C++ plugin unmutes the event pipeline, allows Papyrus OnPlayerLoadGame events to fire, and opens normal runtime social simulation communications.

## **Architectural Implementation Summary**

To reconcile SkyrimNet integration risks with save/load timeline safety, the proposed architecture for the Chronicle simulation service relies on two main structural components:

* **Substrate Abstraction Layer**: Isolate all runtime mod interfaces (RegisterEvent, RegisterPackage, RegisterDecorator) behind an internal API provider. This enables primary deployment against SkyrimNet's C++ / Papyrus bindings to leverage low latency1, while preserving an open-source fallback (PO3 Papyrus Extender \+ SKSE\_HTTP) to insulate against closed-binary deprecation1.  
* **Event-Sourced Co-Save Synchronization Engine**: Implement SKSE::SerializationInterface bindings inside an SKSE bridge wrapper to tag .skse co-save files with atomic Timeline UUIDs6. Pair this with an external event DAG that forks timeline branches upon save rollbacks, enforcing strict message freeze constraints during load windows to eliminate context contamination across all game save slots.

#### **Works cited**

> 1. Public facing files for SkyrimNet \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin](https://github.com/MinLL/SkyrimNet-GamePlugin)  
> 2. Beta20 · MinLL SkyrimNet-GamePlugin · Discussion \#387 \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin/discussions/387](https://github.com/MinLL/SkyrimNet-GamePlugin/discussions/387)  
> 3. Releases · MinLL/SkyrimNet-GamePlugin \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin/releases](https://github.com/MinLL/SkyrimNet-GamePlugin/releases)  
> 4. Activity · MinLL/SkyrimNet-GamePlugin \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin/activity](https://github.com/MinLL/SkyrimNet-GamePlugin/activity)  
> 5. Severause \- GitHub, [https://github.com/Severause](https://github.com/Severause)  
> 6. SkyrimNet-GamePlugin/.gitattributes at main \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin/blob/main/.gitattributes](https://github.com/MinLL/SkyrimNet-GamePlugin/blob/main/.gitattributes)  
> 7. GitHub \- MinLL/MinAI: Bridge between LLMs and various Skyrim Mods, [https://github.com/MinLL/MinAI](https://github.com/MinLL/MinAI)  
> 8. State of Skyrim AI mods : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1ofb1pi/state\_of\_skyrim\_ai\_mods/](https://www.reddit.com/r/skyrimmods/comments/1ofb1pi/state_of_skyrim_ai_mods/)  
> 9. GitHub \- Pathos14489/Pantella, [https://github.com/Pathos14489/Pantella](https://github.com/Pathos14489/Pantella)  
> 10. Skyrim Installation \- Mantella, [https://art-from-the-machine.github.io/Mantella/pages/installation.html](https://art-from-the-machine.github.io/Mantella/pages/installation.html)  
> 11. Issues Q\&A \- Mantella, [https://art-from-the-machine.github.io/Mantella/pages/issues\_qna.html](https://art-from-the-machine.github.io/Mantella/pages/issues_qna.html)  
> 12. Releases · MinLL/MinAI \- GitHub, [https://github.com/MinLL/MinAI/releases](https://github.com/MinLL/MinAI/releases)  
> 13. Skyrimnet AI is great\! But a few issues : r/skyrimvr \- Reddit, [https://www.reddit.com/r/skyrimvr/comments/1s97e2q/skyrimnet\_ai\_is\_great\_but\_a\_few\_issues/](https://www.reddit.com/r/skyrimvr/comments/1s97e2q/skyrimnet_ai_is_great_but_a_few_issues/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAZCAYAAAABmx/yAAAA10lEQVR4Xu2SMQ5BQRCGp0CEQkKjwQEoxBXoNM5AKxIHIFFpVHqicgCFC1ApFBIlvYhCLcK/mR3WvPdE/eJLvmzy/zO7zRKFghgcwDrM2azwrr3k4Q6uYBRmYBdu4cOZ82DKhQ7BEh50KFSJFyu6AH040aFwgjeY0gVowawOhQvxi2Y5rbqvlIgXXc1lHXcoiAhswCN9XlB0h35hT7w41YUw0oGlR7w4U/kLc7MfTeLFsi4MNQr+FXd41qGwhhviV+M2S8IrbMuQH2N7Joh/yBwO3/WfsPIEO8Yq9I6PiAwAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAaCAYAAABYQRdDAAABOElEQVR4Xu2TvUoDQRSFrwhptBDsksJe09ul0RcIpIqFlaUgaQRrsdK8gYVCICGPIAjpUwhaWlgogpBARPAHUc9hZmfvXiPZTGs++Mjcc2cv7OxEZMYfLMIjuAeXfbaZtqeHA9/hs/fL569hx5Sswm8bisuubZiHLXEPJ6+ruYQ1G+bhQ9zQOdsALRvk5VPc0Be4YHrR9MQNpfxQB3A9syOSqqSDE6O/+jgacCRuMG9FQhk+wqGMP//AoQ0UHLrt1204UD2+RVHVGW5toODQil/zrHm9dG9H1YEleGdDz7xk/wxcn5u6r+rAsbhmweQb8A2WVMZ9p6bm2f6C95Pw8LnpXtywJlxJNnnYPzP1laoDJ/6Xx1CHXbiftjNwCPu6vlB1FDfwQdUcuqbqaHZhBz7JhHs647/xA1IQSEt3zf4lAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAbCAYAAAB1NA+iAAAA1ElEQVR4XmNgGAXoIByI9xKJ1aB6sIIVQPwfXRAKPBggcgLoEsgApACXASDwFF0AHYA0v0EXRAL70AXQAciAXDSxV0jsh0hsDBDDADGAEUmsmAHTQJxgNgPEgOlQ9iooXw9ZES4gzYAagExALI7EJwhmMUAUr0UTRzdgHhofDm4xYA/Aw0hsUyC2Q+KjAJjzQU7HBkDh8BddEBngS0AgQ0FyM9AlQKAPiG8yIAyYAMRdQNzPANHwHCp+AKoeA/wG4n8MCAPQMcjZP4HYD6ZhFIwCqgIAXpk+VQ5x1qAAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAABYCAYAAABI4au3AAAET0lEQVR4Xu3dS4ykUxQH8MvEa4aYRAgi8Yqx8Fiws5lgzMKaEBkMiZBI2EwkEoTYGLFg4xFh5bGRiEeCWBtBCIIFwoYVsfF+DfdMVXXdOv11Pbq7ajqZ3y/5p7/vnK/rVvXq5FbXV6UAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAq/ZULAABsHDfX7M1FAAA2hs01/9WcnBsAAGwcMbABALCBPZQLAABsLOfXPJuLAAAAAAAAAAAAAAAAZ9eck4sAABw8z5TevdfGZfvS1QAALNRgIPu99HbWsm1leM2u1AMAYI4Gg1jsrk1rMLgBAMzVWaU3dMSNYX8tvcHllZEr5uuxmj9q3qr5t+admsNHrliM1QxfsQMXv3NNbiSnluVvqba5cHgpAMCoD2ueSLUYIDal2rw8WnNUqs06NK2H52r+zMUpxd8qnvNFuZHcWbpfW1cNAGBJDAtHdtQWpWut13NhAeJ5nJaLM4jf/y0Xkx9L9+v9PBcAAFqDt+R25saCxNpf1ZyQG6v0cM3PNQ/mxhhvl+5BahbXlsmPEf1Xm/Pb+j+PbWoAAMt8W4ZDW+Tl0fZYl5Te23zjMslrZXT9c0fbM7mg5rj+8dYyecdrYLD2Wk16jOh/UfN+/xgAYGZvlOWDxNXpfJ7y4PR3zYs1RzS1cfL/oG1J5yuJNT/JxSQ/ty7j+vEhirZ/e3N8ZnP8dXMMAHBgGMraoeKMmvea8/UWO2KtU8pw/XZIi8FtGnHftNYx6XwlseY3uZisdWDbU/NDc94ObKc3xwAAS44uywecMBg67ii9W2z80/SyHTX3Tcg429P59WW43ktNfdwg1Lq4DAe9+CBF1+vrMs0wNo1xjxG9PKCG+CBCiB24j9sGAMADZfmA8WXNk8157q+nS0vv3mutWG9z//jTVJ9W3PQ2Bs18q5Jx9pXZ1uhyYxn/GF292NX7pX/8fRn+/x0AwAGP939eVfN8zVNNb+DdXFhHg/Uuq3mz5oamF55ujruGnfUWa+T7wc0ifn8wfK3W/lwAAJjkyrK2IWYtjm+OFzGwxduRP+XiDOI5npiLM4odx89yEQBgnHir8O5cXKC4LUd8bdWixND1SC5OIXbW1rq7FuL1HpaLAAAMXVF6Q9sLuTFGXL+IHUAAAPrOK70BLD64EMcr2V2Gw9rB+KJ6AIBD3t4yHMhWynVLVwMAcNDsrvmuDIe0j2puaS8AAAAAAAAAAAAAAAAOHffnQof42q4Pai7PDQAANpb4LlQAABbkntL7aqhN/fN7V0jLDhsAwALdWnNTLk6wIxcAAJiv/bkwwc5cAABgfuLt0H01u3Kjw5aabTV31WxNPQAA5uikXAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAFuV/LcHS0BwQKwkAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAaCAYAAACtv5zzAAABK0lEQVR4XmNgGAWDDVgC8V4i8UyoHrJAHhD/B2JudAkgmMwAkVuFLkEKeMEAMQQXAMllowsSC7IYIAZ8RBNPQGKD5HWQ+CSBVwwQAwqRxJKhYjBgiMQmGYAMAmEDJDFQkN1D4lMEYBZ8A+J/SPxYZEXkAiMGhIHI4BYanxlK8wDxSSDuQpLDC7YwQAxfjibujMRej8QGgadAzI8mhhN8YoBYkI4ugQRAwYYM0H2LF4AUP0cXRAIBQNyJJgazoBaIzwKxBZIcCuBggCjOQJcAAiEgbmDAdK02EJ9mgAQtCIDiIxIhjQC/GVBTDDIGif8B4l9AfBSmAQrWMEDUVKOJUw28BmIpIP4JxKJoclQBsCDrAeJgKNsNSlMFgJIoCPAyQML/EpLcKBgFVAIAHVVM8auQ1YIAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAaCAYAAADIUm6MAAABnUlEQVR4Xu2VTSgEYRjHH/IV+TrJkZSrsyKJs5MDuTkoKSelJIsbxcnBQUkpRQ5qC+Hm4OQiipszpRzI9//p3bHv/Hf3NTO2bJpf/drZ5/9O++w7M8+IxMREphk2cbGQWYWv8BOeU1bwzIlpfICDP+QGjnOReRSzsFDoEbORCapnoIuGuJgnEmI2ZpHqLs7gE6zgwKZcTOM283AS1lM9DJvwFlZykAPtYxiOiunnGI7BEXuRTaf4G++HR/AOLln1oHTAJLyEpZS56BXTB/tgL7I5kXTjM7BBzI5rbc9bFIBBMed0cxCSasm8A7LiXRb9A3qSUiLBbhNdPwFfYCtlUVmQkI3rp87zOn/spB3ui5n/xZRF5Q0ecpHRp9b7d1upY935sGzDa1jGQQS0hykuMtPivyzei0hZhzvpKBDL8B7OchAC/X17A/RBz0Dn64X1fQU+p451qjjnqAMdgToK1zj4gRpJb1ytOF6KuqiNah9i7rN8UARP4QHs8kc5uRJz1TZgFWXfZBtdLbCRi79kF75z0UEfF2JiYmJi/gdfkKFWh5dn3TYAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAZCAYAAACo79dmAAABg0lEQVR4Xu2VzysFURTHDwtJWCgbZaVEUSI7G2VlJfkDSKJsLPwPSiglCTtlYSUlSws2VqQUfwAl+VkWJHyPe6/3dZrxntfUPDWf+vTuOWfuzGnevXdEMjL+N6PwHD7DD3gFj+EJPIO3Pq8e+jmpsyWuoTi0NmOTaXEt+ZudsMk0mBTXzIPJj9BY6y0Up8aNuGamKDfmc4EOGqdK2ECrcAUe+HiNLyoFyiXXbGDAxw2UC1TBbbhsC0VQZhP5mBbXmB5ZzBKNu2EbxRuwn+I49EVEcQHf5fcNHcmuuEmbJt9L4x0aK5ew1uSi6LQJT4+4+X9uNiyBZlsgdAMyhT6kyyYMhd7nm6i3ytzBRop1nb3BajgOh+Es1ZnEmp0X91nVCXtwUdxDF8StSW3IbjxFz+R9yf0T7VRrNQ6ZuCJ36Rf23omjS0JPiRdYb2qWxN5ssYQHzMFBP+7zv5bUm9WTQKmBR/CUapa4Zl/hE7yHj3D9Zzk56mjcBCsptsQ1m5GRUQp8AjAQVZU6TK1WAAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAbCAYAAACTHcTmAAABHklEQVR4XmNgGAW0Bv5AvJdI7AbVQzSYAcT/0QWh4CwDRM4aXYIQ+MeA21AQALmUCV2QEAAZ+BNdEAlMQxcgBoAMbUAT+4vE3onEJgqAIgtkKAeSWAQQ9yLxSQb9DBBDpwPxbCBeAeX7IisiBQgyQLwJiyRGIBZG4pMFJjBADADFLjJANnQyEB9D4v8G4lgkPga4wAAxoA5N/CIS+wcQpyHxQepNkPgYAKQAhNnRJaBAHIgnIfE1gXgTEh8rgBmKCyDLgVx3CIgjgdgMSRwOQMnlGgPCUFDYdjFAUgIoFTyEij+AqocBfA4ABzYsa2LDoBQBymH5MA1QgNdQcsFnKM2NIkoBUGOAZA57ID6FJkcReAPEW4BYFF1iFIxUAAAzyUsOB7A/TgAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACcAAAAaCAYAAAA0R0VGAAABdklEQVR4Xu2WzysFURTHD4msrVihZEMpG7IjvxZ2SgkbZWtBFihbWchKsVBKoZT8DV5khZJYiI2yUH4mGz++1znDmeONXn7MG3U/9WnO/Z43M3du051H5PFkj6UMXIAzwQlxMQKfYZXK5uALLFBZq2Sxku6GLovKY2XRBsST2LIhuLPBX1JkA1BCPLlG2wB1NoibHuLJFdpGEjijLLxbmdBPPLEH20gC58STG7WNJBBsIfW2kQSi9reAfTgAB+EO3Au335iER8QbeY5kh3Dq/RdEs3JchtUqj6SBvp7ckBx1fxx2q/EtrJR6E/bBDRnr84K6DXaq/BNPxBe9hldSPxJ/0iwdcF6NL2G+1OXEN3WrtEofq+YYhmNSF8Ndqd12lSf1j5mm8Erp1WiBJ2qs2YYVUncRX8fRLsdfwa1ygFuZe1gGc2EpTKl+E+yVWj/ECmyWOt07+23s/ncDJ9R4Da7DUwr/o6mBF/AY1hI/1IHqezyef8sr3wxTyn+X6wsAAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAA5CAYAAACLSXdIAAAE7klEQVR4Xu3dW+hvUx4A8IVyCZO7B7c0lEvUkVuUIzPIyAvRvEwzCU8kcnkgSknKNaGhPAyNFA+UiETyIGIGIdfcb+WayxSG9W2v5b/+67//t8PvnN//+Hzq217ru/f+nX3WedirtfZaJyUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAH43Nu4TvyOr+gQAwJjNc2y9QKyJ+M2/5LisPzHi6z6xwmyQ5rbZUtvvnj4BAEzWtjl+bOo/laj+n2P3pj5N9kyzn7X6ok8s09hvtvrzUd+ilP9R6tWlOd5u6tPknDT37xLGcr2lXAMA/EYeSLOn9+JF/HhTf7ApT5v5Omy/1mK/eUJTjrb7V1N/M829/9quPi0+TXOfNYzlei/n+FufBAAm439dPV7WRzb1z5rytOk7bHs15Rg5XFMLdVhuW6Qe937X1PfPcVhTnybxrO1o5KlNfjGr0+yRWQBgLVrKy3pa9B22sc7l2Tk+SkNn7sMcG5Z83BfxXI7rSrmq5XrN2Ln5xPkj+uSUimddVcp/ak8s0WJtAQBMwGk5vu2TExTfdkVnqo0PcryX491yfpdfrp6rdtjGOlZVn/u+Kce5Q3PsnOPjLh9ezXF8kw/97/UWOz9N4lmfzfFOKS/XmtwDAPxK8QI+vE9OsX6E7b6mHE7O8XSXi+tjJWgtj4n8V2l81Gm+e8IZOb7pk2tJrHBdjvNyfNLUn2zKfy7HS3I80eR7C7UFADAhK+0F3HfYdm3K4aw0jJK14vqYJq3lMZGPqdOx82O5KqZcL+qTa0ldpbpU0SE9s09muzXlu3Mc29R7C7UFADAB8fIeewE/nIYpyoNzvJGGj+irl9LMqNYOaWbE5qQcO+X4odQnpe+wjenPt/X+XFU/pr8gzb2mr7fGzh2UhpWjF+d4qskfmOOhNDOaFd+9xYrdW3NcWHJH5ng/x9WlHtOXf8zx3xz/KblYNBLP2071hq1Kfj5jz3pAGm+f83Nc0+Srsd8AACYgRptuSMPLN+KfOa5qzm9U8tuXenTewv3lWMU2D/UFXo+T3GA1tpSof+ZdaVg4MObRNHQs4zu1V3JsV/K3pOHeO9OwV1rYLw2jSpG/KcflpRwdpOiwhvi2rrVJjuvTzLP8O83exuORHFc29dVp2Nfu9VKvbXVvU46/T3isHD9PwwhadITfKrl2JepYx+nvaTx/So7n03Du5jS0W/ybv1hyMY1cRYf7jlKOa1ubpvHfBwDWgW3SzLRifM+0TymPvaxvL8fYbDcs9P3TSrVZjuP65CJqW/0hDatV27Zryzc25SuaclXbNbT39aNrv5VjcrxWjr0XchzSJwGAdSNGi/5ayvN1NLYsxxPL8ZlyjFWn66OxzupC6vV1Q+Jaj2nomAI9qtTrKGZoN6WNBQKh/XNjQUCMjMVIWozg9fvBhbFv1JaqdsyPTsMz9pv/LrcNAIAJim+mqvj/J2MKsNq3KVc7lmN8D7W+igUJX/bJeURn6vQ0ux1D7RDtUY7Rtr3Y0qRd/Vn3kAt7N+X6G722A7hctRMe6jRyFdO+AABTL6ZGl2KhD/9XKlOhAMB65dy07rb6AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABgQn4G3jb074Ew/hoAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAABeCAYAAACeuEiqAAAFN0lEQVR4Xu3dTagd5RkH8DfGgEakCtKoWA1urBpRTBYiIkrVhW3AlbYK4sfChVbxAxdSqinqSgTBUgp2VUGTtiAo0qpYiPjdLlwpJYtghCIifoAftFR9n84ZM+dhzrln7k3OPbn5/eDPmXnemZPJvYv78M5XKQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsELf5gIAAItjXc1ruQgAwOr7V836ml15AACAxdCeBj13rAoAwEI4vjSnQY/LAwAALI7LcwEAgMVx8+jz4rEqAAAL4w+lueHg3jwAAAAAAAAAAAAAAABwQs2FNdvyAAAAq+fx0rzhYFqO/n5rAADmJmbT2obsTzU/Gh/+v+vL/m2eSmMAABxE8fqpaMKezQMTnF+a7fem+oG0qebvuQgArD0bar6qebTm7dK8H7N9ofm8PVnzSWlmpuIY3qlZN7bF6jiyNMcztDmKh+rGfvH/GiqfYs0Jv6s5arQMAKxhn6X1z2vuTLV5iCYkGqNcWwTdJmmoe8ry9439Yv+s/b7lfi8AcAi5oOY3qfZ8zRGpNg99zcczubBK4ti25+IAsf+VuTiD2K/vd9H+rD4eqwIAa9LPS/PH//48sAriOPaV/gv5lyNO9b5W817NmWlsiF/X/DsXBzqp9Dek07TXwLX+0lnua+IAgDWsPd0XievHluO+GbKU7nFEtowPD7a3s/xgZ3mouL7vtlxchqENW9zc8GXNmzV7yvD9AYA16IbSNAU/TPXWE7lwEH1TxhuUuK7upc76UmJ2KtuZCzOK44g7RCf5ZdnfZE4T4yfm4hSxffeGiz+OPmPm0AwbABwmduRC9W7NpZ31tgm5vRyYWaY+8YDZc1MtGptuA/Tnmss660s5LxeqXbkwoziOU3Ox48Yye8O2ORcnaO8u7Wqbvb3dIgCwtuWGIMTMVisakYdHy33bduXTn32ZZHfNJakWD5/9b2e9/feP7dSWEqcRW7/qLA/1fulvboda6mfY9dcyeftr03oc38ZUAwDWiGgI7uqsR1PV3nUYp9ziQvu4WD6agVvbjQ6COI6ve2rdVztF8xanam+p+X2nPk2cOnyrNDcynJXGhnio5tNcHGhzmdyA9embsftxTw0AOEw8VvofnzGv5uCU0efdNX8rzexaFg3db3NxjuJnsTUXB4j9f5qLB8ADZX6/JwBgAb0++rxmrDp/54w+29OaP2kH5qhvxmtWV5fl7ztN2wAejO8GAA4RcffjTbm4CtoXqP+i5uTSXJA/b9EkRmOU38Qwi5U0e7N4MRcAAA5Xp5em8fpHHpigfVjuy3ngAIrmNa7VAwBg5I0y24zZtjLbdit1by4AANC4o+xvyCZl2sN2V+q00jwb77k8AADAuOvKeJMWj0KJ2TUAAAAAAAAAAAAAAGAN25QLE3xQlvf4jp/lAgAAw3yRCxOsq/lPLk5xVWle+/VKHgAAYHZn5MIUz9RcMVr+QXdgiu01u3MRAIBh2tOcO2oe7EnbnLXbnd1ZXko0bGbYAABWYGvNC7k4wf9q/tlZP7ZmZ0+e7mwTDdurnXUAAAZ6tuai0fK+mg97Eq+HCjHbFraUphGbRWwX17EBALBMs57aDBtHnxtqnuwOTLC+5r6aPTXHpDEAAJbQ3mzw0VgVAICFETNrj+QiAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHMq+AyuI8P4SEj09AAAAAElFTkSuQmCC>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADQAAAAaCAYAAAD43n+tAAACGUlEQVR4Xu2WzUtUURjGX11kRpEEQqCICyEM2rpyGf0BRgu/QCxxUdbCWlkLsw9a1KoQVIICQVy0aWNKbsRFFAQVRKEogrRQXEWilvU8vOcw77x9cBczw9y4P/gx73nOuTPncOaee0UyMjIKSSt8mdAH4ZpUcBX+hAd9BxgX7eNnKqiAm6KT/hvs6/ZhuXJFdMJclKXP1OxvMO2yZkt0whddvm/qU6Yue7gYetJkrD+YdqqIC/pmatpmB6WFFsktwPLatStdu5jch7s+TMqM6GKeunzR1HOmLgU8jG77MClfRRfU6zsMfveKzSQ87cOkcLJrPjR0whsuuwRX4QtYE7JX8Dy8Bd/CayGPTMMl+X2iY6KHz4jo85BwTu3wHfwcskQcEr34gu8IcNv97vDHz4Wa//WHos8xYsdyMuSyy/msqw71jui9eVT0EdEYco6Pi+uA10P9T/ZEv8SealHmP0RvzNl4QYD9H+FzyU2MnIFPTJvjDofPUZN/h8fgWdFd9pyAC6bNw6netAsK3/P8jkXuwB7TjuP42fWH/B58ZPJIP7wZ6kbJf7gXhW1TN8GhUHPHI8fhfKi5AI4jzXAq1IOS/27INvvXJfeCzHsx7vSRkBWcYdHJrsJak/OHl+EXeNfkA6In6TPRG9/yCU7ANybjXz3CazfgY5OVBJ50Kz5MKwdEd+U9rHN9qYRHP58/vJmrXF9Gxv/IL576gZAexTV6AAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGYAAAAaCAYAAABFPynYAAAEBklEQVR4Xu2Za+hNWRjGX4xcM265hJiGTy7lFj6gJDMNxnybmhHJPVKUEF/k/llNUZIZJWaUkkvjMjVTQyMld5G/OyMZdzNieJ/etVjnOfvsvc/f2cdR+1dP5+xnrXXWWnvd1xHJycnJqTU+ZaM+fKd6zWbOezFfNYHNcnmuWk/e1hTarNqoWunSZMGhMlRrPGWjHH5XfUXeELERdETV1HnfO++lj6QMEEt/IfCyAnn/y6bSSqxMtTjip6h2sJmWqApdVTUg76xY3DXkt1StJi8LkPcyNh3fSHQ9agGUazebSaxVHWBTqWNDLIP/VM3Jx+jqT16lmSmW/yfkD3Wfw6R2G+ak1KNsSDCGTaU1G2Jxl7OpdGcjA/6W4spNUvV03zGdDQzCaomJYmVvxgFxIAEqlUQ3sbgjOaAK9BbLO2yYz1W3gudaBmVF2UdzQBzcC0uxRdLHrTQ7xfLGAo/F3zfShypPfcCudwmbcaStXJoX8ZANxzSxtGc4ICU+7z6Bh61xXfCMEc3rT1b0E5tax3JADKg7Ondqkl62B/H2s0n0YiMA6b9lMyVRneJX1RfB86ngezXg8iRxQrWdzTjSZoB4i9gsA6TvxGYKGkl0w4SgQ8xiM2PiyhMFjh8b2IwjTQZzxeKVmiqw27ih6ks+zhyX3ecPFAb4nBTFYrG8MXWUguuAxvxDdV510Hk459xWtRDbWd5XNXZhoLPqolg+YT2biI1GvNh2gf9CdVh1U/VT4EeB30MZF3JAHEgwmE3igRRX3oMdE17+cNU25zVUHVcNcs9I38F998yW5JEAnonFmcMBShvVY9WewMMOM/xNf/BdpfpTCm847rpPbCh+C3yfHiMcDQiOqma479PFGhG0leQ6jBOLg/KmBvddP7Op/C9WaSzo/7hPVAC+L1TII3nX0y5JYWGjCo5Rdk91jQMcx1SvxPLzDRgKYdilYbcTgp59R6yXz5PCw3BYDt+A46X4Ogl+e7E8/DkpBKMEtx1ghUTXLwRXVklxipgslTkPcEPwcymWsvGeIK+ubDrCcmBHdV21Sewi1oMGQ2f4UkqXO/TPSeHdYRToPElxIilVgLR8pvpLNco9Y/hjjgeY6k6rFkjxPRdGGEZaJbkihaMEZQNYWzClejADYMrFVY+fogC2tR3FLmf5veAED7jT4Td2BR6DOCPZTAO2sX59qC+YQnBeAV3EGmqfqofY1TcWcQYLKEZsJcHLxu9iO42RgJcM1on9PfGL2AyBhvLUiW1eMEXhlO7BmoBRtVdsjQK4qvrxbQzbLGCDgc1DFDhvheevskFmT9jMGD9PVwOsF9VmhFRoqsY2s6yLto8EdDpMJ+FaUg2+ZiOnEGzNp7rPnJycnJxseQM16gDE8Y52LQAAAABJRU5ErkJggg==>