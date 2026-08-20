# **Architecture of External State Persistence and Timeline Synchronization in Skyrim SE/AE Plugins**

Maintaining a persistent world state—such as non-player character (NPC) dynamic beliefs, unscripted rumors, extended relationship webs, and evolving biographical memories—alongside Skyrim Special Edition / Anniversary Edition (SE/AE) presents a complex architectural challenge. Because Skyrim's native engine (Creation Engine) operates on a discrete save-file state model (.ess binary blobs), offloading state mutations to an external process introduces a dual-database problem. When a player reloads an earlier save, dies, or switches between distinct character profiles, the external database risks diverging from the internal game state.  
This report analyzes how contemporary stateful mods reconcile external data stores with engine state, evaluates Skyrim Script Extender (SKSE) co-save mechanics, explores event-sourcing paradigms for timeline management, diagnoses engine lifecycle race conditions, and proposes a complete synchronization protocol for an external service.

## **Comparative Analysis of External Memory Management in Current Mod Ecosystems**

Stateful Skyrim mods utilizing artificial intelligence or external data engines adopt fundamentally distinct strategies for handling state persistence, ranging from simplistic global stores to complex timeline cleanup protocols.

### **Ecosystem Architectures and Persistence Paradigms**

#### **Mantella and Pantella**

Mantella and its community fork Pantella interface Skyrim with external Large Language Model (LLM) backends, Text-to-Speech (TTS), and Speech-to-Text (STT) engines via local Python runtime applications1. Mantella’s persistence model relies on local SQLite relational databases or structured JSON files stored within the external application directory1.  
The original architecture lacks direct coupling between Skyrim’s save state serialization and the external memory store1. When a player reloads an earlier save game, dies and reloads, or switches to a completely different character, Mantella's external memory store remains unmodified2. It operates on a monotonic, append-only paradigm where conversations and generated memories persist regardless of in-game timeline shifts2. Consequently, the system suffers from timeline bleeding: an NPC killed in a later save who is subsequently "revived" by loading an earlier save will retain memories of their own death or conversations that chronologically have not yet occurred2.

#### **CHIM and HerikaServer**

CHIM relies on an external server architecture known as HerikaServer, implemented predominantly in PHP using MySQL/SQLite and Prisma ORM layers, paired with local vector database instances for Retrieval-Augmented Generation (RAG)3. HerikaServer explicitly decouples temporal metrics into three distinct parameters3:

* **gamets**: Skyrim's internal game time, represented as a double-precision float tracking in-game days elapsed, initialized at ![][image1] upon save game creation3.  
* **localts**: The absolute Unix timestamp of the external host server3.  
* **ts**: Engine frame tick counters or delta metrics passed from SKSE messaging3.

When handling reloads, HerikaServer does not execute database rollbacks to prune memory tables. Instead, it relies on context retrieval algorithms that filter or weigh records by vector semantic relevance and gamets boundaries3. Dynamic character personalities update globally3.  
If a player loads an older save file, localts advances monotonically while gamets jumps backward3. Because the server state is not atomically tied to the .ess file via transaction rollbacks, character personality updates and memories recorded in discarded futures persist in the vector database3. The system mitigates but does not fully eliminate timeline corruption by treating all historical entries as potential "dreams, visions, or intuitive premonitions" during prompt construction, or relying on vector threshold scores to surface only contextually coherent memories5.

#### **SkyrimNet**

SkyrimNet approaches state persistence through an architecture embedded directly within the game process6. Written in C++, SkyrimNet executes memory reads natively, employing thread-isolated worker pools and reference-counted entity wrappers to eliminate IPC latency and process boundary hazards6.  
SkyrimNet utilizes explicit internal mechanisms for timeline tracking and session management7. The framework assigns persistent UUIDs to game entities and virtual speakers (GetEntityUUID, GetVirtualNPCUUID)7. Crucially, SkyrimNet implements a dedicated save/load timeline cleanup protocol7. Upon detecting a save load event, SkyrimNet triggers a timeline purge that reconciles internal event history, drops orphaned execution threads, resets volatile transient states, and recalculates scoped world knowledge7. User-curated world knowledge packs (.sknpack) and static lore facts remain protected, ensuring global truths survive timeline pruning without suffering context pollution6.

| Feature / Dimension | Mantella / Pantella | CHIM / HerikaServer | SkyrimNet Framework |
| :---- | :---- | :---- | :---- |
| **Backend Architecture** | External Python app; SQLite / JSON files1. | External Web Server (PHP/Prisma/SQL \+ Vector DB)3. | Integrated C++ SKSE Plugin \+ Embedded Async Worker Threads6. |
| **Temporal Identifiers** | Sequential transcript indices; unindexed1. | gamets (Skyrim time), localts (Unix epoch), ts3. | Save-scoped UUIDs, Entity UUIDs, Event History Indices7. |
| **Reload Handling** | **Ignore**: External store remains unchanged upon reload2. | **Append/Filter**: Monotonic server log; filters by RAG relevance3. | **Reconcile/Clean**: Purges timeline history while retaining global rules7. |
| **Timeline Branching** | Unhandled; severe cross-character memory contamination2. | Partial; vector retrieval surfaces historical anomalies3. | Isolated via explicit timeline cleanup protocols7. |
| **Key Failure Modes** | Anachronistic NPC knowledge; database growth bloating prompts2. | Dynamic personality drift across save reloads3; cache mismatches. | Warmup property cache race crashes (Issue \#465)9. |

### **Analysis of Bug Reports and Technical Edge Cases**

The architectural decisions of these frameworks introduce specific failure modes documented across issue trackers and community discussions:

> 1. **Cross-Timeline Memory Pollution (Mantella/Pantella)**: Users report that after dying or loading an auto-save following a failed quest, NPCs retain dialogue memories from the failed attempt2. Because the SQLite database is not bound to the save slot, the external state acts as a single, immutable continuum, causing NPCs to reference events that were negated by save restoration2.  
> 2. **Dynamic Personality Drift and Server Timestamp Desynchronization (HerikaServer)**: In HerikaServer, because localts monotonically advances regardless of game loading, loading a save from 20 hours prior results in a mismatch where gamets drops while server-side character biography updates remain intact3. If a character evolved from hostile to friendly in a timeline that was later abandoned, the server's database retains the updated friendly profile, corrupting the historical narrative of the older save slot3.  
> 3. **Property Cache Warmup Crashes (SkyrimNet)**: Issue \#465 in SkyrimNet-GamePlugin highlights a subtle thread race during game loading: Save-load crash in WarmupPapyrusPropertyCache \-\> dynamic\_character\_bio9. This crash occurs when the external state manager attempts to query Papyrus form properties or build dynamic character biographies immediately upon receiving a load signal, before the game engine has fully finished initializing Papyrus property caches for the newly loaded cell9.  
> 4. **Origin Dropping in Event Streams (SkyrimNet)**: Issue fixes in SkyrimNet (PR \#476) reveal bugs where event histories dropped "originator-less" events during quick-save/quick-load timeline rebuilds, causing background world events triggered by environmental systems or virtual actors to be omitted from the reconstructed timeline context8.

## **SKSE Co-Save Serialization and State Identifiers**

To prevent state desynchronization between external backends and the game engine, external services must leverage SKSE's native serialization interface to embed timeline identifiers directly within Skyrim’s save files.

### **Mechanics of the SKSE Serialization Interface**

SKSE provides C++ plugins access to the game engine's save pipeline via SKSE::GetSerializationInterface(). This interface registers three essential callbacks:

* **Save Callback**: Invoked when the game writes an .ess save file10.  
* **Load Callback**: Invoked when the engine parses an .ess save file during loading10.  
* **Revert Callback**: Invoked when the engine resets internal state (e.g., during main menu exits or prior to loading a save)10.

Data serialized through SKSE is written to a distinct co-save file sharing the exact filename prefix of the parent save, bearing the .skse extension (e.g., Save1\_30A1B2C\_0\_466F726765.ess pairs with Save1\_30A1B2C\_0\_466F726765.skse). The file operations are co-dependent and executed sequentially by the engine thread10. When a user deletes or overwrites a save slot through Skyrim's UI, SKSE dispatches kMessage\_DeleteGame, allowing plugins to purge associated co-save artifacts simultaneously10.  
Data is written into the co-save stream using custom 4-byte chunk identifiers (Record Types) structured as Tag-Length-Value (TLV) entries, specifying the record type, format version, and payload byte length10.

### **FormID Translation and Dynamic Load Orders**

A critical vulnerability when persisting game state externally is the instability of Skyrim FormIDs. A FormID is a 32-bit integer where the upper 8 bits (or 12 bits in Light Master .esl plugins) represent the mod's position in the active load order (ModIndex). If a player adds, removes, or reorders mods, FormIDs stored in external databases become invalid or point to entirely wrong game entities.  
SKSE's serialization interface provides ResolveFormId(UInt32 oldFormId, UInt32\* newFormId), which cross-references the plugin names embedded in the save header against the current active load order (DataHandler). External services must store references using stable composite keys—consisting of the originating plugin name and the static local FormID offset—rather than raw 32-bit FormIDs.

### **Save-Embedded UUID and Timestamp Tagging Pattern**

To achieve absolute atomic correlation between an .ess save file and an external database, the native plugin must generate and embed a unique 128-bit UUID into the co-save stream. This identifier serves as an immutable primary key for the specific engine state snapshot.

| Byte Offset | Field Name | Data Type | Description |
| :---- | :---- | :---- | :---- |
| **0x00 \- 0x0F** | SaveUUID | 128-bit GUID / UUIDv4 | Unique identifier generated for the current save snapshot. |
| **0x10 \- 0x1F** | ParentSaveUUID | 128-bit GUID / UUIDv4 | Identifier of the parent save node from which this save was created. |
| **0x20 \- 0x27** | SaveSequence | UInt64 | Monotonically incrementing save counter within the active playthrough. |
| **0x28 \- 0x2F** | EngineGameTime | Double-precision float | In-game elapsed days (gamets), initialized at ![][image1]3. |
| **0x30 \- 0x37** | RealTimestamp | UInt64 | System Unix epoch time in milliseconds when the save was committed. |

#### **Protocol Flow During Save Creation**

> 1. The player creates a save game (e.g., auto-save, manual save, or quick-save).  
> 2. The SKSE Save callback executes on the engine thread10.  
> 3. The plugin generates a fresh SaveUUID (![][image2]).  
> 4. The plugin reads the previously stored SaveUUID (![][image3]). If no parent exists (e.g., a new game), ![][image3] is set to a null byte array.  
> 5. The plugin writes ![][image2], ![][image3], ![][image4], and engine metadata into the custom record chunk.  
> 6. The plugin transmits a SAVE\_CREATED notification containing ![][image2] and ![][image3] to the external service over IPC/WebSocket.

When the player loads a save game, the SKSE Load callback deserializes ![][image2]10. The external service looks up ![][image2] in its local persistent store. If found, it seamlessly binds the active service session to that timeline state node.

## **Event-Sourcing Paradigms for Multi-Timeline Branching and Garbage Collection**

When state mutations are driven by asynchronous external services, treating the world state as a state machine managed via an append-only Event Store aligns with how Skyrim's save engine actually functions.

### **Directed Acyclic Graph (DAG) State Models**

In traditional server architectures, state is represented linearly (![][image5]). However, because a player can load any historical save file at any time, Skyrim's save topology forms a Directed Acyclic Graph (DAG) of state snapshots:  
![][image6]  
Where ![][image7] represents discrete save nodes (![][image8]), each identified by its save-embedded SaveUUID, and ![][image9] represents directed edges representing sequences of game events (conversations, relationship updates, regional rumors) that transitioned the state from parent node ![][image10] to child node ![][image11].  
To construct the active world state for any given prompt or logic evaluation, the external engine executes a path traversal query from the root node (![][image12]) along the lineage down to ![][image2], aggregating all events along the branch:  
![][image13]  
This model completely prevents cross-timeline memory contamination2. If an NPC died in a parallel branch, that event does not exist on the path to the current node, cleanly isolating the NPC's living state in the newly active branch.

### **Timeline Forking Mechanics**

When a player reloads an older save snapshot (e.g., loading an earlier save Node 1 after progressing to a later save Node 3a), the following state transitions occur:

> 1. The game dispatches the SKSE load event, passing Node 1's SaveUUID to the external backend10.  
> 2. The external backend sets its active context head to Node 1\. It does **not** erase the discarded nodes (Node 2a or Node 3a).  
> 3. The player takes new actions, resulting in a save action. The plugin generates Node 2b, setting its ParentSaveUUID to Node 1\.  
> 4. The event store records a branch split at Node 1\. Node 2a and Node 2b now exist as parallel timeline branches stemming from the same ancestor.

### **Garbage Collection Strategies for Orphaned Branches**

Because players routinely create, overwrite, and delete save games, a multi-timeline event-sourcing engine will accumulate orphaned branches (abandoned timeline nodes that no longer correspond to any viable save file on disk). Left unmanaged, these orphaned branches cause storage bloat and slow down vector database query indexing.  
Garbage collection (GC) is governed by three primary retention and pruning policies:

* **Disk Alignment Mark-and-Sweep**: The native SKSE plugin regularly scans Skyrim's Saves/ folder or captures kMessage\_DeleteGame notifications10. It transmits an active manifest of extant SaveUUID strings to the external Python service. The external engine performs a reachability traversal starting from all active SaveUUID heads up to the root nodes. Any DAG node not present in the reachable set is flagged for garbage collection.  
* **Tombstoning and Soft Deletion**: Flagged nodes transition to a TOMBSTONED status rather than undergoing immediate hard deletion. This protects against transient file read locks or temporary mod-manager isolation environments (such as Mod Organizer 2's Virtual File System) that might obscure save files during startup scans.  
* **Hard Purge Protocol**: If a node remains in TOMBSTONED state past a configured grace period (e.g., 7 real-world days) or if total orphaned storage exceeds a user-defined threshold, a background process executes a cascading purge: pruning event records assigned to the tombstoned node ID, deleting associated vector database embeddings, and re-indexing search spaces.

## **Runtime Event Detection, Lifecycle Messaging, and Race Conditions**

Synchronizing an out-of-process engine with Creation Engine execution requires precise management of the engine startup and save-loading timeline.

### **SKSE Lifecycle Messaging versus Papyrus Event Pipelines**

Game loading triggers sequence events across both native C++ code (SKSE) and interpreted virtual machine code (Papyrus):

> 1. **kMessage\_PreLoadGame**: Dispatched by SKSE immediately before the engine opens and reads the .ess binary file10. The file path to the save file is passed via message data10.  
> 2. **SKSE Load Callback**: The engine reads the .skse co-save file synchronously on the main render/logic thread. Plugin data stored in the co-save is extracted10.  
> 3. **kMessage\_PostLoadGame**: Dispatched immediately after the primary engine save-load routine returns10. The boolean success flag indicates whether the save loaded without catastrophic file corruption10.  
> 4. **Engine World Initialization**: The engine instantiates cell records, places actors, reconciles initial physics states, and updates internal pathfinding meshes.  
> 5. **Papyrus Property Cache Warmup**: Creation Engine populates internal form caches and updates dynamic script property bindings9.  
> 6. **Papyrus OnPlayerLoadGame**: The OnPlayerLoadGame event fires on script instances attached to reference aliases or quest blocks.

### **Analysis of Concurrency and Race Condition Vectors**

Integrating an external Python service across this pipeline introduces three main race conditions:

* **In-Flight Network Payload Leakage (Stale Write Injection)**: Suppose the player initiates a speech action or triggers a world event, causing the external service to spawn a long-running asynchronous AI processing task (e.g., LLM context generation or network API call taking 2,000ms). While this task is processing in Python, the player quickly loads an older save file (Quick-Load). If the Python task completes *after* the reload has occurred and transmits its output back to Skyrim, the response will execute inside the *new* timeline even though it was generated based on context from the *old* abandoned timeline.  
* **Cold-Start Form Cache Queries (Engine Crashes)**: As observed in SkyrimNet issue \#465, querying game engine form properties or requesting complex actor data immediately upon receiving a save-load notification can crash the process9. This occurs because SKSE messaging callbacks (kMessage\_PostLoadGame) execute *before* Creation Engine has fully finished populating Papyrus script property bindings and object state wrappers9. Calling native methods on uninitialized game forms causes null-pointer dereferences or internal memory corruption9.  
* **Rapid Quick-Save / Quick-Load Sequence Starvation**: During intense gameplay, players may execute rapid quick-save and quick-load cycles within short intervals (e.g., 500ms apart). If the native SKSE plugin transmits save notifications to the external service asynchronously over a socket connection, network socket frames can arrive out-of-order or trigger overlapping state reconciliation loops on the server. If a SAVE\_CREATED packet for Save B is processed *before* a LOAD\_GAME packet for Save A, the server's context pointer will point to an invalid head, dropping origin metadata or corrupting event stream ordering8.

## **Recommended State Synchronization Protocol for External Services**

To address these architectural challenges, this section outlines a state synchronization protocol tailored for an external Python service operating alongside an SKSE native C++ plugin.

### **Structural Architecture and Serialization Layout**

The system relies on a dual-layer architecture where an SKSE C++ plugin embedded in Skyrim handles co-save serialization and native lifecycle messaging, communicating over local WebSockets with an external Python backend managing an event-sourced database.  
The SKSE plugin registers record chunk 'TMNL' ('Timeline') within the .skse co-save stream. The payload uses a fixed binary layout:

| Offset | Type | Field Name | Description |
| :---- | :---- | :---- | :---- |
| **0x00** | BYTE\[16\] | SaveUUID | 128-bit UUID identifying the active save snapshot. |
| **0x10** | BYTE\[16\] | ParentSaveUUID | 128-bit UUID of the parent save node. |
| **0x20** | UINT64 | SaveSequence | Monotonically incrementing save counter. |
| **0x28** | DOUBLE | EngineGameTime | Current gamets value (elapsed in-game days)3. |
| **0x30** | UINT64 | UnixTimestamp | Real-world Unix epoch timestamp in milliseconds. |

### **Inter-Process Communication Contract (WebSocket Specification)**

Communication between the SKSE plugin and the Python backend occurs via JSON-encoded frames containing strict fencing metadata.

#### **Protocol Messages and Operational Roles**

> 1. **CLIENT\_INIT (Handshake)**: Transmitted by the SKSE plugin upon establishing a WebSocket connection during game launch. Specifies plugin versions, runtime environment, and load order hashes.  
> 2. **SYNC\_TIMELINE (Reconcile Request)**: Transmitted by the SKSE plugin during kMessage\_PostLoadGame once the co-save chunk 'TMNL' has been parsed10. Passes save\_uuid, parent\_save\_uuid, save\_sequence, gamets, and character identifiers.  
> 3. **TIMELINE\_READY (Reconcile Response)**: Transmitted by the Python backend after verifying or creating the corresponding DAG node in the event store. Returns an **Epoch Fencing Token** (epoch\_id) and active state confirmation.  
> 4. **MUTATION\_EVENT (State Update)**: Transmitted by the SKSE plugin whenever in-game events alter world state. Must include the active epoch\_id, save\_uuid, actor UUIDs, and payload mutation details.

### **Protocol Execution and Synchronization Rules**

* **Rule 1: Epoch Fencing Token Invalidation**: Every time a save is loaded or a new game is started, the Python service increments an internal integer counter, generating a new epoch\_id. The server returns epoch\_id inside TIMELINE\_READY. Every subsequent mutation request sent to the server must attach this active epoch\_id. If the server receives a request containing an epoch\_id that is older than its current active epoch\_id, the request is discarded immediately as a stale payload from an abandoned timeline.  
* **Rule 2: Input Buffering During Reloads**: When kMessage\_PreLoadGame fires in C++, the plugin sets an internal atomic flag g\_isLoading \= true10. While g\_isLoading \== true, all event generation hooks (dialogue events, location transitions, relationship shifts) are suppressed and blocked from transmitting network messages. The flag is reset to false only after kMessage\_PostLoadGame completes, the 'TMNL' co-save chunk is transmitted, and the Python service returns TIMELINE\_READY10.  
* **Rule 3: Deferred Papyrus Initialization Guard**: To avoid the Papyrus cache warmup crashes observed in SkyrimNet Issue \#465, the C++ plugin delays firing external event triggers derived from Papyrus properties until a minimum delay threshold (e.g., 200ms) has passed after kMessage\_PostLoadGame, or until Papyrus explicitly sends an initialization heartbeat from a ReferenceAlias script9.  
* **Rule 4: Transient Volatile Buffering for Unsaved State**: Events occurring during live gameplay between save points belong to an "uncommitted transient edge." The Python service writes these events to a volatile memory cache attached to the current active SaveUUID. If the player creates a save game, the C++ plugin emits a SAVE\_CREATED notification, prompting the Python service to commit the volatile memory buffer to the persistent database. If the player dies or reloads without saving, the C++ plugin emits SYNC\_TIMELINE for the earlier save, causing the Python service to clear the volatile transient buffer and cleanly discard uncommitted mutations.

#### **Works cited**

> 1. GitHub \- Pathos14489/Pantella, [https://github.com/Pathos14489/Pantella](https://github.com/Pathos14489/Pantella)  
> 2. Proteus. How did I miss this mod : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1me7yz6/proteus\_how\_did\_i\_miss\_this\_mod/](https://www.reddit.com/r/skyrimmods/comments/1me7yz6/proteus_how_did_i_miss_this_mod/)  
> 3. abeiro/HerikaServer · GitHub \- CHIM Server, [https://github.com/abeiro/HerikaServer](https://github.com/abeiro/HerikaServer)  
> 4. HerikaServer/AGENTS.md at aiagent \- GitHub, [https://github.com/abeiro/HerikaServer/blob/aiagent/AGENTS.md](https://github.com/abeiro/HerikaServer/blob/aiagent/AGENTS.md)  
> 5. Will KoboldCpp consider adding RAG functionality in the future? · Issue \#1239 \- GitHub, [https://github.com/LostRuins/koboldcpp/issues/1239](https://github.com/LostRuins/koboldcpp/issues/1239)  
> 6. Public facing files for SkyrimNet \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin](https://github.com/MinLL/SkyrimNet-GamePlugin)  
> 7. Beta20 · MinLL SkyrimNet-GamePlugin · Discussion \#387 \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin/discussions/387](https://github.com/MinLL/SkyrimNet-GamePlugin/discussions/387)  
> 8. Activity · MinLL/SkyrimNet-GamePlugin \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin/activity](https://github.com/MinLL/SkyrimNet-GamePlugin/activity)  
> 9. Issues · MinLL/SkyrimNet-GamePlugin \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin/issues](https://github.com/MinLL/SkyrimNet-GamePlugin/issues)  
> 10. SKSE/src/skse/skse/PluginAPI.h at master · NightQuest/SKSE \- GitHub, [https://github.com/NightQuest/SKSE/blob/master/src/skse/skse/PluginAPI.h](https://github.com/NightQuest/SKSE/blob/master/src/skse/skse/PluginAPI.h)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGcAAAAWCAYAAADdP4KdAAADTklEQVR4Xu2Zy6tOYRTGV64RyQBDRQYojFwSRgYyMZD/AIlyKUmkGDChnJJLMpKBDExEIiEDSoqRcityKwm5FWE9+32Xvb5lrb3fdOqcOvtXq/b77Gc/a+1vn+/79v4OUUdHR0dHx8Cy0AqGKVxTrfgfjOOaZUWHZVwjrGgozWoDvdpy0KtkppKsCBxbMZprFdclrt+5PMZS2jeNawbXBa47PY5ykLOIaxLXL643vbsr9nA94BrOdYCSZ3aPI3lslvWUoHs15UgvPZOlNMvjEaXj/174iVxz83bTxYG+2NGWGK2JkVxvuXYpbTLXZ6PBY+eAR2vIwtpmWa0NydFIjsbODezcpVkem7neWVETXRy8lT39CddzKzZwjVLOeKOfyrrgzSGe6XkdZXnHNiE5Ft1L1raXnbs0ywOeQ1bURCe2hXz9Jvl6RJS/j2p9Xt7+VO+uEM+xvPY8IOoR0ZQjvWQmi54blGRFwLPNiproxA6Tr18lX4+I8ndTreP7D9v2LS6es3nteUDUI6IpR3rJTBY9NyjJioBnkxU10YmdIV+Xm4hSovwdVOtr8/breneFeO7ltecBUY+IphzpJTNZ9NygJCsCnvVW1EQndoR8/TL5ekSUv5NqfXXexhewRjy38trzgKhHRFOO9JKZLHpuUJIVAc8GK2qiE9tIvn6DfD0iyt9LtY7bTmx/rHdXiOdkXnseEPWIaMqRXjKTRc8NSrIi4NlqRU10YmvI1++Sr0dE+Qep1uXW80e9u0I8+/Pa84CoR0RTjvSKbof13KAkKwIefIeFNJ2Yp3/numi0YWatwYMbcuxD2RWuD2rtzQEPtFF5HWVB01ltSI5F95K17WXnLs3ywGt5zooa70UR3nMdNRq8E9R6ZtZOK82Cz148QQvrKB0zX2nwQMNTtoD1T7UWzWbBo7NeUvK9UJrF9pIcjZ0b2LlFa8vyHrKXO1oVhKuPnyJe5cLBX7Qpgydi3D5fpxS0tGdvAg+l/zQxPOW6z3We6yv5X4RzKOUc5/pGscdmWVZSujDIiNC9ohwgvdpmastawXXbipQ+JvEan7A7+pNnVhhgFlD7H8yQoc8KA8x2Sn/xQ57HVhgEPOQaY8WhCP6dMJjAr+4dHf3HH6THV0lSSElTAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGsAAAAaCAYAAACwwaJoAAADzklEQVR4Xu2YSciNURjHH/OwUGYKnykhG1lYkDGkRMpcSiKZEhaiDFkgC5IsTPXFxrQwb6iPzPM8ZtookblExuffc4577v9733Ov3XW/91f/7nue5znn3Pec855JJCMjIyMj4/9iiuqG6qLqguqS6lrgn6e6ozqvOuX8d1W33DPyXFZdVdW2LNJXdd35qsTKbut8nt5i5aAulIPy8ds1DFJmq+6pHgRCvpti9R5UNf0bXUP4rXqtqssOx1PVBrIhD5TGHrEOjuHLGMUOIqku/NcBzr6XfGVLQ7EXns6OAG4oANsuNgY8ZEMCSZ3ANJN4XEcxXwuylyWrJL0hPD8oPUgsTzuye8ZL4TJ7SLwTPPiiEXOAHQHwH2ZjOfJV4g3WSrWObKclngfrDNaqGPuluEb+KRbXkx0B8H9kYzlSaHTjKxkRpBtJ4Q6Gby0bCayRiFvEDgIxr9hIIOYJG8sRvOgWNgbcp/RqsTz4etL4pmrMRgJlvJPcLjINxM1iYwB2g4jZwY5yY6jYi7Zkh2OSVP+C0BGwjSO7p41Yh8ZAB6GMBewgUAfXz2CTg5g67ChRmrChWM5IvDEeiZ2VQhAfy7NV1YCNxEKxMmqxg8C5KlYXgP8DG0uYQu+TyhuJZ4ZvZoItlqfQ+gIOSbwMT6G6mov5x7CjhIm9T5Tbkp55sGoaGyXegJgCK9mYQKyMEMSkneXmivlPsMNxVvVYcjcyWJdx0+KpUA1zzxg8z8XWP9y+rHf2yc6OGxjc5PRydjBH9UJ1UmzQANzsYHBjeseNDG5aPJvF1n8cg3gfUBSdxF6YpyO8xHGyefCHkIfXuW5if74YkB9XRTH8OawL2dEwOHBj6htLPoB38QMBRw48d1DVD+wAHYeycCmAaXui2HGjj9iMs0y1VGwqHq06Irk1Fh2H9RysEdvcLHbpsI4VYh3u2akaGaT/GWRGBS9Vz9zz8LyI6nQXi3svuQ3H/LyI6hxTfVF9EsuHX4yyqjBIbEvvjwZeiPvu7PvEjg9pYLaYwUaxzgrPYmGjAnwFrckGOA7Ahk48Kvm7XnTqtiD9VlUvSCeV9c9MEDukVqqG5LtSGSg2RS0X+5OlAg7RSY2OQRlOqWHD4UrrV5AO4QbGV8g2z0axy3EPx3G6xsM7wwr3u13V3z3jHhGHaKw7YJMkNyQ6EVMegy/cg6VkpXvGQPHgePJZ1dk9A39td8X91niwZmH6wU38blX7wIdpEGvuVLEpeYmz4znp2gv+fmwU65wqsTU6/IpRTggGDtYtD/zngnRGRkZGRkZGRkZGAf4AvR8Chg8moYsAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGUAAAAaCAYAAACuCJLbAAAD4ElEQVR4Xu2ZW4hVVRzGP6+pSRlkD5GogWgqBD7WgxoKKiTeCBIfRkRQS0SoHqweChETClJ8EEQHUfCWCKIgBjN41/Ka2UWSQRDNS15ATcXL/+O/lrPmm3P2PualOTP7Bx9nn++/1jp7r73Wf6+9DlBQUFBQUPB0mWw6Ytpv2mc6YDqUxOeafjHtMdWH+FbTsXDMOgdNP4fy5F14G4zVwdt+NYmT6fB2WY/xvfB2lFmmX00nTb8FnTAdNR02bTb1eFS6lfHAdN7UQQOBBtM34rEOVY4fTD+qKcQ28jp2JUr/1jC4v1r8qqcr/MJqxE8p1SH0atVM+EuNEuTdWMJZllWuHyq7sVXF1yh/wZE78v09eJ3XxY8wLea1+TG8zBUNCN/Dy63TQALj69WsZm4juwPZ8bxxKTuRXedPeJksLsLbmKMB4T68XH8NJDD+t5rVTFZqIBz1w8XLu5GMfaWmEH/3bQ0IeedHGOeCoNXAC1qiZsIpNeB1uHoqxy3TC2oKbGOTmiXIuymvweNLNVCtjIBfkC5ZI1PQvEO6BW+i+JFepi/UFIbA2xisAeEDeLkzGkhYCy/TTgMtgDfUqITdaN7pKadN28Wbj+w6K0yd1BS2ILuNyB/wclM1kMD4ZTVbAB+avlWzEi4hu3MYqxFvY/DLwQd4HleR3UaEZag+4kd6wuOjNdACWG56X81KOI7ynTMSnr6UxShfhys1nkwerF/JzWO5WjUTGN8m3jjTOdOL8N2Kf0wdk3g9PB1+ZJqR+D/BB+CqcDww+Hyh3mX63bQjeBPgS3mmTO56cEZzl4Lw+cwdCJ4b6+giKZe+8Mqaj0fBU0wp2sPr6HNoADzd5fESvP5sDQiDUHqW8He5+GBsrMQI0yu3eHgNEe5WkH8T7xPTd+F4XviMgy2eXzzXyMLw+Sl8q2lBEtOBqt8fizHwBs7CO5XHXABk8Ra8HEchXyx5zJGXxQXTDdM1+Ci7Dn8H+TwtZHSBdx7bjLpnuht8PthZJou0Q14O39+BX2OE+2jpLsB4NF/BcUZx1nGlyZvERU4k/Q3ORF5PpDd8YDwRXOVsgKcKvq1XwlD4VP8S/zF3PkPSDuNsaoCn3TWJryOZOweTxGOZciuotD6faen+Ww2azqI2T3c0bt1wIcARHHN/OuDYqZ3R+D7FWas0oOnseDN8voKmL6v8Pc4W7mATZhyeB/flmO7bPNzNXgZfJS5C0069Cd/yr4Fvy/CVII0p7FCmZz7gudTniyr5DP4XRYSzsC75zoUAd8nT51qbhs+fghYCUxGfcUxLKyVW8D/BNDXTNC18FhQUFBQ8Hx4CXDX8meZGvSoAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIIAAAAaCAYAAAB7NoTTAAAFcklEQVR4Xu2ZeahvUxTHl3keMoeMT8aIkExPhoxPxsx5ScicMpMXIYSkzD0ReRJPiUK4yB+UIVMIf1DmWcZM62Pt9c4663fOfb97r3o3b39q9Tv7u/dv//ZZe1p7/0QqlUqlUhmaRdRmqO0ftFXC82Rhc7XL1DYt6YXUTm2yKxNhYbXv1X5T+1vtMbXl1F6LhSYBH4i179PyubHaTLUvYqHK+PhQzKkLBm1btb+KPhlYQKwtDM7IJ0U/I+mVMbKzmCO3zxnK6WoPZXEewWp1QRbFtomvxAZKZQJ8rPan2so5QzlEbaMsziMYrAdlUVlJ7aQsVsbOZ2JO/kPMqcPAoGFfPkVtUbUl2tn/coXafkm7TywWyayhdqvazWqHpjyHNmIb5IxRIJicJdaWLniPM9UeUFtKLDDeIuTfonZcSDvTslBYVm0ftafVTkh5R6rdHdJrl/RtQetiX7Vn1S7NGQXqdd8tmfLGxL3SOJmY4Goxp/TBEswyjZPYn0fEAswIETyNi/GF7/G7Bw0YfPzuiNojar+0chu8jRgxzeHt7AFwHmXZ2l4Q2+Yi/h4EmQxqyjApGJSwm9rrYnWsUDQnvpfDietHsbxr1b5UWz7k/6D2jdpZJU3Zy8VWY9cyTAp8c4Pau2KDInKH2u/S+G7C2/j70nY0dn6rRAN5W4f0VUVzXhVzLKCvGfJIXxjSOxYt7u9bSncssJoMthHj6JhBz9tFbKOn43vcVTSH9wC0uCqcWLTIqkXLgewT5RNf0k78QjkGgXNu0WKMxqBCi5OCdDzBkccKG8ntmhDTpXFyHAwsOwRl+cceTNpN5ZPlM5flpdcpz6w85DN7gMHAkTV/pwtm2qNiZR9PeS8V3WHrYqDHTu96D2aTa3Qsv4Hlcp+rvZM0yrwc0msVzfEOY3bn9j4ptirEVYdZ/pG0T3HHhGf3neO+G/fJyTshw77JDz0ctOeK5h0NmxTt9qA5jNg3k/ZMeOZ72PViA27vkBdZTG39LBb4/ncd2ntiF07niJ2KMvk9XLszabSXTopQ7uiQ9i2PFeUisc7oC7Apx7E8a2wRWZuatAj5P4nFPsRpfb4bGvatLmgEP3Zd0H4uWgzmTi7aUUFz0C9JGgGpQz42N2jLVlks0EmvJI06mTF9+LKbg1K0Y5NG/SNJoxwz3iHgRBstrnIol7cytM1CmhgFjXb2QT4r33/C4tI/EIi035D23t3VcQRErs0IOqDHPZO6mKFOV31dEPTlWeTkTnFtz6RF2OLy77IEZw3Qdg1pXwGBJZ3VzAfW3DhMBssdkbTnxVaTXC5D/pVZHC8cR6iQI09kXRlcDoHIlfJLl/ROJe2Nzo0n7f9T0FlfhzzwwIkB6eDot8QCRqATKBODK4cYgUA1w/79VNIOEBvYTnwP8NUugzY9pHkHL0ec4W1Hwx+R2WrHhzTvlX3wdjHgXfxonf0C90hTH75ja4jgu76JPSoc+ZilfndPEMRx6v5YKMEJgLIEMweqbaP2rVij8oXULtJ04sXSDnycFcXK4FQ6gzN4hNWAOGNDsXK0z/9jODiUy3Dsoz4cg/P5PyLi70HwRuxDvfghw5JNOXzlTv61WLwP4RmfsEJSJ4Mx35dQz15JW6/oHCvjQGKQ4hPqJAZ6UQbvCAjS2Wr5fpfvhubG8snIo6MYcdc02b0QUcdGszT2BUdc6HAeHw0ic/7t7Boo3FWsXp65fyAoZTZsN6dEPwRQe2QxwHt4PTiTM3kXXDDtIM0M5XNqkz0HdG4+44VUhDq64Ni4TBbFJimzPN8dRAiEp0i37yrjgIEQ7zsq8xlcUp0nNhCGvV6v/M8gKOa+hKvn09TObmdXKpVKpVKpVCrzMf8Auhhq+U4mxFkAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFgAAAAaCAYAAAAzBZtTAAACl0lEQVR4Xu2YS6hNURzGP5dyE5EiE0oyMFFKCYNLkRh4jBhhYKDkVUoeSbkpRRkYYCCPiYEMlAElhpSYeOWdjChveXQvvn//de9e+3/2Pmft7ex79q31q6+797fWPue7/733ehwgEolESjGKOkCtokY4b2LSXHvGUYepJZ43xzvuKCOpj9Rv6i91A1rc236nGnMKmv0LNP9Rahb13u/UKZ5DQ0mRB5hN9Tm/7nyn1hlvCzS7tHWUBdAgPbaBbKKuWbNm7KV+WtMh/9ceaw41r6k/1BTjC8upudasAHmDyiJFfGxNxyek38qO8BYasp+abNqGivvWKIBkF22kxqSb6sF5JCHlSZbJYWyqR/XspCZZM5CXSPLLULEPuhqqFU+RhBzQoVSP6vlljQJ8QGP+ZakeNWI9kpC9pm2qOc9DnqDRJSRLrHtI1uBFket2IMlvCc1vWQ0dQgtzzBqOzdCA1z1vLXXcO2/GfGplCcmk9IOajjC2W8NxEY0FbpU/b7WxlJqAxs8L4ps1HPOgH3jS805D72RVyC7sITXTNjThqjUcu9FYkFb58woslCqwvJJ5BT5LPUOyxHkE/YIn7rgKXlijBT3IX6O/os54535+fxvt0/YCH4ReNN7406CrCUvhLyjAOWsEcAvZmRZDJz1LVl+fthdYljQyKciTKhe/g46Bl/xODin6HWu2kayCNGMRNHMX9Rm6pX8AXYlkjbNZ+W8ayXLPP9+WdB0scKHJ94T7203tpy4gf9LbQB2xZhtZaI0WyMSz1R3LDlR+QbtC7RrskSYkf8gTLDe0EuTuyiQ0g7pr2oYDfv68rXNIgfOu/W/WUJepFbZhmBCSP6/AX6FDp/yUK8PRm3RzJBRZJ0cikUgkEmnGPyITnAN3R3GuAAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAA5CAYAAACLSXdIAAADY0lEQVR4Xu3cOYssZRQG4M8FVxRcEETBJXIJDEw0EBTFRISriCCCiKiJS3ADFzTSRANFRMWdy1UwVPAPGGsgCAaCgYpbILiBuFyXc6hupubcr3qme3pUmOeBF6re+qa6Jjt0V1VrAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADwH7m+FgAAO3Vh5KLIxZELIudHjtu0YrG/a1FcEXk58nHk0ln39sbhXTG+pvMip0XOiJxb+vxfz4qcPuoXOWWLpPsit862AQDWpg5dR8+6HOYW+asd/rdzj7fh2BGlz+610q1T73p6Xcr+nFpu4fvIw6U7oW3+jEdH2wAAO3Zm6w80n7R+P/ZU66+5ow1975ur7M+u5RrlNVX5mceU7urI/aXbjjzXUbUMh8r+bg6lAMAe80LrD133tn4/93Tk+NZfk92dtZzprV+X2yJH1rINn3ll6f4s+9uR3xbW689v19J747Idvg4AYGU5WHxVy/BSmx46bojcONuua96N/FS6f0u9lrlP23Af3dwto+1lvNM2f8abo+0q1+V9cwAAO5aDxV21DH+06QHo99F2XZP79R6v7cifGb8t+SbydeTLyBeRz+aLJ9RrmTvQhoce5n4ZbS8jz5/5KPLjbHtKHrumlgAAq5gaOrJ/opZtuPfrw8j7kQ/asG58T1fvfD+3jWGnd3xdps59bds4lg9KrCrPcU/Zn5Kf80gtAQCWla+06A0dp7Z+n+rAk+suKfvHjvbnrmrT51yXqfOf2DaO5f+2qjxHfeo1vVKLNqy9vZYAAMvKnxnvLt2rbXrw6fX58+gDo/28t+270f7cop9Y12XR+fPYr7Usnol8XsuZy1v//HlvXO+9crn2pFoCACzjYBuGijciL7ZhUMsnJ98aL5rZ14ZBJtc/N+oPzLp8yGDcZ5f3n10XOTnyWOTBNrwqZDdt9RBAfbVHlf9/byjLBzB+i/wQeT7ybOT1NryTrbc+TfUAAHvek7VY0v5arCgHVAAAOnb6zdb4CdhVPVQLAAA2W3Vou6wWK8h7Am+qJQAA/x831wIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA9qx/AKS0oUO2bm0sAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAZCAYAAADXPsWXAAAAqElEQVR4XmNgGAW4wCYg/gDE/6F4LxCzo6hgYFgJlQPhj0DsjyoNASYMCEW4AD45MBBhwG+IABCvRxfEBvAZ8hddABfAZUgeEFuhC+ICMEPY0MRfo/HxApghDlA+BxDfgcsSCV4yQAyphvJ/AnErQpo4cJoBYsgsKP8eEHMipIkD/QwQQ64xkBgOyCCIAREu2WhyRANhBogBv9ElSAUgL5EcDqNgFBACAEF/Kduwe5h/AAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAH4AAAAaCAYAAABxRujEAAADoUlEQVR4Xu2ZS6hNURjHP4+SMkGhPG4y8U4pTIwwIpI8S10m8i4DmQgDBgaeSckAGYmRokh5l+T9KkJC5JF35P39z1rLXvt/1z7d665zdbb1q39nf9+3z15n7bX2+r69jkgikUgkEon/gfGq25425sMVbqrOq06qztrPWFwR0+4d1TFVx3xYros557TqjOqiakjujL9nlWRt43NGPlzhhuqc6pT93JIP1z/zVN9VvzhgOazar+rMgQj0l6xtTLAQiPVlZyT2irl+Ud+fqJap2nOgDDxSjRLTeUwC5h47IoIbjwlV7ea/YUckMOnQ5kr7OSAfrlD0m+qe+ZJ1rujmh3yxcNd2T/1qLwZ6qpaTLxb7VLfsMdp+68Ucr9lRFrCUbbfHuOm4AX2ycIWDZMcEeRSMlfDE26lqR75YoK1p9viEtf22MOmWeHapQGen2uMe1l6fhaWXapFnx2ard3xZmg48iq9a8VPV3R5PFtP2hCwsM1WDPbtUXCXbPXWN1t6VhaKzQNXNszuJaXuPtedYu1ZwlY62fkiW6+96sVIxSDWFfNMlv+SGbjxuCJ7EpxxoIc/ZoXyVrM37Yt4mfLAUr5CmtUBLWajqSr4dYtp2uZ773qB6b/14taxbinK3G3jkelT8PhgMn9ZU3Hi6mDFi2p5lP1F5O4apRqi2SesH/gU7LK7vmGB44/C55B0fUL307LriFTssn8V0foNky66DnwK2WwI2Z0Lgmninf8gBS4yBL/rdbuCxIjTmQ7nvzCa7rkBxE2K4ZDeAN064s2yD5lThIyUrKplnYq47lwOWGAN/jR2WpZL1nentHU+U8DnN6fs/BUspF3Y+GJRQx9jHNqpg+HiZ9MHEQn3Ak8qBNwm+rk+1gXeD5qcIBkUd8nkReNOo1j4mLdIUt4FVAt8LbYIBpKqiSeVwq201EOcU3Cw+iSlg3onpAHauQoTyIP8otsFjCfuBaxu1wQfVkXz4D4gVgYFfw07LUTG5dzMHxEyoj2LaRpGGFW907owM/DcQooOYwrYfB8TsQCJ9FqUwgAE7xE4PpBDsKVTjgmocO2sNDyjbjiJ/DDDwa9npcVzMObVgt2Tv/kP9gAf+XCod38guqhM2sSMiGNR17PTA9q+/PxCLxWKWd+T6BgkXx/iHEZtBpQTLJfIglssQD9gRCaQk5ECkCuhLPlwBgzOQnZFw+dkptKRjH+K/JfQvV1sxiR1tTBd2JBKJRCKRSCQSUfkNoVjqIYvsUdcAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAbCAYAAAB1NA+iAAAA1ElEQVR4XmNgGAXoIByI9xKJ1aB6sIIVQPwfXRAKPBggcgLoEsgApACXASDwFF0AHYA0v0EXRAL70AXQAciAXDSxV0jsh0hsDBDDADGAEUmsmAHTQJxgNgPEgOlQ9iooXw9ZES4gzYAagExALI7EJwhmMUAUr0UTRzdgHhofDm4xYA/Aw0hsUyC2Q+KjAJjzQU7HBkDh8BddEBngS0AgQ0FyM9AlQKAPiG8yIAyYAMRdQNzPANHwHCp+AKoeA/wG4n8MCAPQMcjZP4HYD6ZhFIwCqgIAXpk+VQ5x1qAAAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAaCAYAAABCfffNAAABUUlEQVR4Xu2UPUsDQRCGR8FCUILoT7ANRkifVhREgmVioyCkENHOX5BOEEQsxNZCAyFFyjQiqIUhiBZaWtgoWmjj5zvZudzuBMHltkiRBx5udl7I3C6bI+rT6yzBa3gLb+CiG7fZhxewAc/gvBv/n234I+ZUxqThs2768gXXyQz5UBmzALO66cuDPKPdDFkZw8eViBRckZrPnYecxnEb7iViDk5Knad4NzYvau2NPootMkPGZD0CN+PYn1nqfmuGe/dSl+GglXlzCY90E5yTGTQKP1XmDf9ASTdBkcyQNXkm4gkO6KYQXYCq6vPu+cqPwyYsuLEL76CmmxbHZIZkrN6GPPkzNC31O6xL7fBG5lq+Sj3jxh0OdIPiax5hX5Jg7FD3kBNrHYRveCf1FNyzsmDwm+/CCiX8k/7FBGzpZkj4y/wIr+ChyoIxDJfhqtgnDL/OSEoW1ysNaAAAAABJRU5ErkJggg==>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAZCAYAAAArK+5dAAABFklEQVR4XmNgGAWDDfgA8Q4gvgTE/4H4F6o0GOxigMjB5NtRpYkDS4B4OQPEEDY0ORBYAcSv0AVJAU+A2JIBYkEsmhwIPATi1eiCxIJUIP4HZcOCAh2AxDTQBYkFz4B4ApTdwAAxTBIuCwFL0fgkgb9ALIjEB1nwnAERF3FArISQJh30ovFPMEAsOQnlP0KSIxnkADE/mhgrA2pcYIsTosE6dAEogFkgAcS30eRIArhct5ABIvcFiCPQ5GCABYh50AXRASgH4wJHGHA7AJSjmYCYE4i/osmBwTwGRDCAXBuAKg0GIBdiswBkODuUzQ3ECggp6gBsllIVoFvQg8anGCQD8XYgvgrEu9HkqAbUGCDhPwpGIgAA2jQ6ax7wJnEAAAAASUVORK5CYII=>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAaCAYAAABCfffNAAABWUlEQVR4Xu2TTysFYRTGD1IUYeMTsCGxEFnZihI3ZcVCFrKQsvMJ7JSdhY2VhY18ACkpf5ZiY0FZKSJJ+RPPc98zd84c1J3uKIv51a855zzTvPO+945Izn9nGp7BC3gOJ5JxkXV4DPfgIRxNxuWzCj/VQZeRLnjvh2n5gIsSFnlzGRmDvX6Ylhu9RrupNRnhcVVEE5zVmufORQ7iuAhnFTEC27QuSLwby4PrU+OPYlnCIi3aN8ClOE7PsHx/a8LZpdYrsNpkzXAH7sM1M/+VE7jlh+BIwkKN8N1lnPdpPSNlfDd8wLwfgikJD1vQq+UV1mjdATdN9iN3sMoPlegPwKOJ6IbXpudOeU+9mSXgDnb90LAt4QE9ZjYp8W9F6iTc02lmJZ4l/C0ftR5KxiU2XD8Ar0wf7YTXzOD3dGv6Vvhi+szgm7drPQ7nTJYZ/fBJwkd76rKcnD/mC/b/Rq/YAhJ/AAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,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>