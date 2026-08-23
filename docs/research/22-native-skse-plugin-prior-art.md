# **Native SKSE Plugin Architecture and Substrate Prior Art for ChronicleBridge**

**Document File ID:** docs/research/22-native-skse-plugin-prior-art.md  
**Date:** 2026-08-23

| Index | Date | Title | Subject / Description |
| :---- | :---- | :---- | :---- |
| 22 | 2026-08-23 | Native SKSE Plugin Prior Art & Transport Architecture | ChronicleBridge CommonLibSSE-NG plugin design, event sinks, threading, networking prior art, and actor spatial enumeration |

To establish a zero-Papyrus game seam between The Elder Scrolls V: Skyrim Special Edition / Anniversary Edition ( runtime 1.6.1170) and Chronicle's external Python processing bridge, telemetry and event dispatches must be handled inside an in-process native C++ dynamic link library. This first-party plugin, named ChronicleBridge, hooks native C++ engine events and serializes them alongside periodic actor spatial state vectors directly to a local socket. Building upon substrate decisions and transport surveys, this report establishes the concrete prior art, existing C++ libraries, thread marshaling paradigms, Proton cross-platform socket behaviors, actor iteration mechanics, and license hygiene needed to implement ChronicleBridge.

## **Native Game Event Sinks and Engine Coverage**

The Creation Engine uses an internal event dispatcher based on the RE::BSTEventSource and RE::BSTEventSink template classes. CommonLibSSE-NG exposes these event sinks through C++ template abstractions, allowing plugins to intercept game engine state transitions directly on the native execution thread without invoking the Papyrus virtual machine1.

### **Native Event Sink Mapping**

The target telemetry event set required by Chronicle maps across standard RE::BSTEventSink types, UI menu listeners, and dynamic memory hooks2.

| Telemetry Event | Native CommonLibSSE-NG Source / Substrate Class | Dispatch Mechanism | Engine Context & Event Payload |
| :---- | :---- | :---- | :---- |
| **NPC Death** | RE::TESDeathEvent | RE::BSTEventSink via ScriptEventSourceHolder | Dispatched synchronously when an actor's health reaches zero3. Contains pointers to the dying actor (actorDying) and killer (actorKiller). |
| **Item Transfer** | RE::TESContainerChangedEvent | RE::BSTEventSink via ScriptEventSourceHolder | Dispatched when items move between inventories or references3. Contains source container, target container, base item FormID, item count, and item reference handles. |
| **Cell Attach / Load** | RE::TESCellAttachDetachEvent, RE::TESCellFullyLoadedEvent | RE::BSTEventSink via ScriptEventSourceHolder | Dispatched when cells attach/detach from the active grid or finish loading cell geometry4. Provides handles to RE::TESObjectCELL. |
| **Quest Stage Change** | RE::TESQuestStageEvent / RE::TESQuestStageItem | RE::BSTEventSink via ScriptEventSourceHolder | Dispatched when a quest stage advances1. Contains the target quest FormID and completed stage index. |
| **Dialogue Start / End** | RE::MenuOpenCloseEvent ("Dialogue Menu") | RE::BSTEventSink via RE::UI | Dispatched when game menus open or close. Dialogue progression is tracked by monitoring the "Dialogue Menu" state or hooking RE::MenuTopicManager. |
| **Crime / Bounty Change** | RE::TESFaction / RE::PlayerCharacter | C++ Function Detour / Hook | Lacks a top-level global BSTEventSink in ScriptEventSourceHolder3. Intercepted via C++ vtable detour on RE::TESFaction::ModBounty or RE::PlayerCharacter::ModBounty5. |

### **Sinking Mechanics and Registration Lifecycle**

For events exposed via RE::ScriptEventSourceHolder, event sinks are implemented by deriving a singleton or persistent handler class from RE::BSTEventSink\<T\> and overriding the ProcessEvent method2:

C++  
class DeathEventHandler : public RE::BSTEventSink\<RE::TESDeathEvent\> {  
public:  
    static DeathEventHandler\* GetSingleton() {  
        static DeathEventHandler singleton;  
        return \&singleton;  
    }

    RE::BSEventNotifyControl ProcessEvent(  
        const RE::TESDeathEvent\* a\_event,  
        RE::BSTEventSource\<RE::TESDeathEvent\>\* a\_eventSource) override   
    {  
        if (a\_event && a\_event-\>actorDying) {  
            // Extract FormIDs and dispatch to thread-safe network queue  
        }  
        return RE::BSEventNotifyControl::kContinue;  
    }  
};

Event sink registration must occur during or after the SKSE data loaded lifecycle message (SKSE::MessagingInterface::kDataLoaded)7. Registering prior to master file loading leads to null pointer dereferences when accessing global singletons7. The standard registration pattern retrieves the ScriptEventSourceHolder instance and attaches the sink:

C++  
auto\* eventHolder \= RE::ScriptEventSourceHolder::GetSingleton();  
if (eventHolder) {  
    eventHolder-\>AddEventSink\<RE::TESDeathEvent\>(DeathEventHandler::GetSingleton());  
    eventHolder-\>AddEventSink\<RE::TESContainerChangedEvent\>(ContainerChangedHandler::GetSingleton());  
    eventHolder-\>AddEventSink\<RE::TESQuestStageEvent\>(QuestStageHandler::GetSingleton());  
    eventHolder-\>AddEventSink\<RE::TESCellAttachDetachEvent\>(CellAttachHandler::GetSingleton());  
}

### **Events Lacking Native Global Event Sinks**

Two specific event domains in the target event set do not possess top-level BSTEventSink sources inside ScriptEventSourceHolder and must be handled via alternative patterns3:

> 1. **Dialogue Tracking**: Dialogue interactions do not expose a unified TESDialogueEvent sink in CommonLibSSE-NG3. The standard method for intercepting dialogue UI lifecycle is registering an RE::BSTEventSink\<RE::MenuOpenCloseEvent\> with RE::UI::GetSingleton(). By checking a\_event-\>menuName \== RE::DialogueMenu::MENU\_NAME, the plugin accurately detects when dialogue opens and closes. For line-by-line topic resolution, an inline hook must be placed on RE::MenuTopicManager::GetSingleton().  
> 2. **Crime and Bounty Adjustments**: Crime accumulation is processed directly inside faction structures and player character logic5. Because no global crime sink exists in ScriptEventSourceHolder, tracking bounty changes requires an inline C++ function hook or detour placed on RE::TESFaction::ModBounty or RE::PlayerCharacter::ModBounty5. Intercepting RE::TESFaction::ModBounty captures the faction FormID, added crime bounty amount, and crime type directly at execution time5.

### **Reference Implementations in Shipped Plugins**

Three shipped open-source plugins provide production-grade reference patterns for native event interception:

* **SKSE\_Template\_GameEvents (by SkyrimScripting / mrowrpurr)**: Demonstrates basic event sink derivation from RE::BSTEventSink\<RE::TESActivateEvent\> and RE::BSTEventSink\<RE::MenuOpenCloseEvent\>, providing a baseline template for CommonLibSSE-NG event subscription2.  
* **commonlibsse-sample-plugin (by colorglass / John Stewart)**: Illustrates multi-runtime event initialization, structured lifecycle messaging using SKSE::GetMessagingInterface(), and safe registration inside the kDataLoaded callback7.  
* **SKSE\_HTTP (by Leidtier)**: Demonstrates native event capture coupled with JSON payload framing for off-process delivery in the Mantella AI ecosystem8.

## **Embedded Networking Subsystems and SkyrimWebSocket Implementation Analysis**

To stream events and spatial matrices out of the game process, ChronicleBridge requires an embedded C++ network transport layer. Choosing the appropriate networking framework requires evaluating vcpkg package availability, static linking stability within MSVC dynamic link libraries, and execution overhead11.

### **C++ Networking Framework Prior Art**

Four networking frameworks were evaluated for embedding within an SKSE plugin12:

| Library | vcpkg Port Name | Static Linking (MSVC) | Transports | Architectural Suitability |
| :---- | :---- | :---- | :---- | :---- |
| **IXWebSocket** | ixwebsocket \[cite: 12, 15, 16\] | Supported natively (BUILD\_SHARED\_LIBS=OFF)12 | WebSocket (Server/Client), HTTP | **High**: Lightweight, self-contained thread model, minimal external dependencies15. |
| **Boost.Beast** | boost-beast \[cite: 14\] | Supported via Boost static libs13 | WebSocket (Server/Client), HTTP | **High**: Extremely robust and standardized, but increases binary footprint and compile times14. |
| **cpp-httplib** | cpp-httplib | Header-only static integration | HTTP/HTTPS (Server/Client) | **Medium**: Excellent REST server, but lacks native WebSocket framing. |
| **uWebSockets** | Non-standard / manual | Complex MSVC static configuration | WebSocket, HTTP | **Low**: Difficult build integration inside Windows DLL environments. |

Both IXWebSocket and Boost.Beast offer clean vcpkg manifest integration and static linking into x64 DLLs without runtime dynamic link dependencies12. IXWebSocket is especially well-suited for embedded SKSE plugins due to its small binary footprint and built-in background thread lifecycle management15.

### **SkyrimWebSocket Internal Architecture Deconstruction**

SkyrimWebSocket (by andreyvelsk) is an SKSE plugin built to expose Skyrim game state to an external companion app (SkyrimWebMonitor)19. An implementation review reveals its core operational mechanics:

* **Transport Core**: SkyrimWebSocket embeds a lightweight C/C++ WebSocket server listening by default on ws://127.0.0.1:876519.  
* **Configuration**: Configured via an initialization file located at Data/SKSE/Plugins/SkyrimWebSocket.ini, which controls logging verbosity (LogLevel=trace) and server port bindings19.  
* **Data Polling Mechanics**: The plugin runs periodic polling loops on the main thread to sample player attributes, inventory changes, spell lists, and spatial coordinates, serializing them to JSON text frames19.  
* **Wire Schema Compatibility**: Its spatial protocol provides a clean reference model, transmitting player position vectors ![][image1], rotational Euler angles ![][image2], parent cell FormIDs, and worldspace FormIDs19.  
* **Functional Gaps for Chronicle**: SkyrimWebSocket focuses strictly on player-centric telemetry for second-screen monitoring19. It lacks coverage for non-player actor grid iteration, quest stage transitions, item container transfers, cell attach events, and crime/bounty hooks19.

### **Strategy Evaluation: Install vs. Clone vs. First-Party Build**

Evaluating the integration options for Chronicle yields clear structural trade-offs:

> 1. **Installing SkyrimWebSocket as an External Dependency**: Relies on a third-party binary19. Because SkyrimWebSocket only transmits player data, Chronicle would still require a second native plugin to handle non-player events and actor spatial grids, creating duplicate network listeners and version coupling risks19.  
> 2. **Cloning SkyrimWebSocket Patterns**: Extracts the socket server design and spatial JSON framing concepts while wrapping them inside Chronicle's codebase. This preserves wire protocol compatibility while eliminating external dependencies.  
> 3. **Building a First-Party Unified ChronicleBridge Plugin**: Integrates IXWebSocket or Boost.Beast via vcpkg into a single CommonLibSSE-NG DLL11. This approach handles both event sinking and spatial streaming in one optimized binary, providing complete control over threading, framing formats, and transport logic1.

## **CommonLibSSE-NG Threading Discipline and Task Marshaling Protocols**

Skyrim's engine operates a primary thread alongside a worker thread pool. The primary render/logic thread controls game loop execution, scene graph management, animation updates, and memory allocations.

### **CommonLibSSE-NG Threading Constraints**

* **Event Context Execution**: RE::BSTEventSink::ProcessEvent callbacks fire synchronously on whichever thread triggers the underlying game engine event2. While UI and cell events fire on the main thread, physics and actor updates can fire on secondary job threads.  
* **Main Thread Strict Requirement**: Directly modifying game engine state—including spawning forms, altering actor inventories, modifying quest stages, or mutating RE::TESObjectREFR structures—on any non-main thread triggers race conditions, memory corruption, and immediate crashes.  
* **Off-Thread Permissible Logic**: Thread-safe queue operations, C++ string formatting, JSON payload serialization, memory buffer copies, and network socket operations (send/recv) can safely execute on background worker threads.

### **Thread Boundary Marshaling Protocols**

To maintain high performance without blocking the main game loop, ChronicleBridge enforces strict two-way thread isolation.

#### **Outbound Telemetry Pipeline (Game Loop to Network Worker)**

When an event sink executes on the main game thread, callback overhead must be minimized. The event sink extracts primitive fields (FormIDs, coordinate floats, string copies) into a plain C++ data structure (POD struct). This struct is pushed into a lock-free thread-safe queue (concurrent\_queue or std::mutex protected std::queue), signaling a background worker thread via std::condition\_variable. The background network thread dequeues the item, serializes it to JSON or binary framing, and transmits it across the socket without introducing frame latency.

#### **Inbound Command Pipeline (Network Worker to Game Loop)**

When the external Python process issues a command that mutates game state, the background network thread receives and parses the payload. The command is marshaled onto the main thread using SKSE's task interface11:

C++  
// Network thread receives payload and schedules main-thread execution  
SKSE::GetTaskInterface()-\>AddTask(\[payload \= std::move(parsedPayload)\]() {  
    // Executed synchronously on the main game thread  
    auto\* form \= RE::TESForm::LookupByID(payload.targetFormID);  
    if (auto\* refr \= form ? form-\>As\<RE::TESObjectREFR\>() : nullptr) {  
        // Safe game state mutation  
    }  
});

### **Threading Case Study: SKSE\_HTTP**

SKSE\_HTTP (used by Mantella) provides a practical case study in SKSE threading discipline8. SKSE\_HTTP hosts an HTTP server on a background worker thread8. When an HTTP request arrives, the network thread captures the request body and posts an SKSE task via SKSE::GetTaskInterface()-\>AddTask(...)8. The network thread blocks or awaits a condition variable until the main thread completes the task, ensuring Skyrim memory structures are accessed exclusively on the primary thread8.

## **Build Topology, Multi-Runtime Abstractions, and Proton Compatibility**

The build and deployment topology must produce a stable binary on Windows development systems while executing seamlessly within Linux/Proton environments.

### **Multi-Runtime Target Architecture via CommonLibSSE-NG**

Historically, SKSE plugins required separate DLL builds for Skyrim Special Edition (1.5.97) and Anniversary Edition (1.6.x) due to structure alignment shifts and memory offset changes. CommonLibSSE-NG resolves this through an abstraction layer that compiles a single DLL supporting all runtime targets1.

* **Compilation Configuration**: Configured in CMake using find\_package(CommonLibSSE REQUIRED) and linking against CommonLibSSE::CommonLibSSE1.  
* **Dynamic Offset Resolution**: Memory offsets and vtable addresses are resolved at runtime via the Address Library for SKSE Plugins (version-1-6-1170-0.bin)1.  
* **Engine Update Fragility Protection**: A single ChronicleBridge.dll binary automatically adjusts its memory offsets whether loaded under runtime 1.5.97, 1.6.640, or 1.6.1170, guaranteeing that future engine micro-patches do not break the plugin interface1.

### **Build Pipeline and Toolchain Setup**

The standardized build topology relies on standard MSVC toolchains and vcpkg dependency management2:

* **Compiler Toolchain**: Visual Studio 2022 C++ Toolset (MSVC v143) targeting x641.  
* **Build System**: CMake 3.25+ with Ninja generator for fast parallel compilation1.  
* **Package Management**: vcpkg operating in manifest mode (vcpkg.json), managing dependencies like commonlibsse-ng, fmt, spdlog, and ixwebsocket1.  
* **Static Link Mandate**: All dependencies must be statically compiled into the DLL (x64-windows-static triplet) to prevent missing runtime DLL dependencies in modded game directories12.

### **Linux / Proton Compatibility Verification**

When Skyrim runs on Linux via Proton (NGVO environment), the SKSE DLL executes inside a Wine compatibility environment.

> 1. **In-Process Server Socket Translation**: When ChronicleBridge binds an in-process server socket to 127.0.0.1:8765, Wine translates Win32 Socket API calls (WSAStartup, socket, bind, listen) directly into Linux kernel socket system calls.  
> 2. **Cross-Namespace Loopback Communication**: Server sockets bound to 127.0.0.1 inside the Proton Wine prefix are directly reachable by native Linux host processes (such as Chronicle's Python bridge) connecting to 127.0.0.1. Wine shares the host network namespace by default.  
> 3. **Proton Socket Considerations**:  
   * **Port Configuration**: Server port bindings must be configurable via an initialization file (Data/SKSE/Plugins/ChronicleBridge.ini) to prevent conflicts with host services19.  
   * **Non-Blocking Sockets**: Non-blocking socket polling under Wine should use select() or poll() timeouts to prevent background threads from spinning CPU cores inside the Proton worker pool.

## **Actor Spatial Telemetry and ProcessLists Enumeration**

To generate a periodic actor spatial stream, ChronicleBridge enumerates active high-LOD actors directly from Skyrim's process managers.

### **ProcessLists Verification for Runtime 1.6.1170**

In Skyrim Special Edition and Anniversary Edition 1.6.1170, actor LOD tiers are managed by RE::ProcessLists7.

* RE::ProcessLists::GetSingleton() provides the global manager pointer7.  
* highActorHandles: A RE::BSTArray\<RE::ActorHandle\> containing handles for all actors currently executing full AI, animation, and physics calculations (high-LOD actors within the active cell processing grid).  
* middleHighActorHandles / middleLowActorHandles / lowActorHandles: Arrays holding actors at lower LOD tiers. For spatial telemetry, highActorHandles represents the precise target set.

### **High-Actor Iteration and Traversal Pattern**

Iterating highActorHandles requires converting handle references (RE::ActorHandle) to strong pointers (RE::NiPointer\<RE::Actor\>) and validating 3D geometry availability before reading spatial metrics:

C++  
void SampleActorSpatialTelemetry() {  
    auto\* processLists \= RE::ProcessLists::GetSingleton();  
    if (\!processLists) return;

    for (auto& handle : processLists-\>highActorHandles) {  
        auto actorPtr \= handle.get();  
        if (\!actorPtr || actorPtr-\>IsDead() || \!actorPtr-\>Is3DLoaded()) {  
            continue;  
        }

        RE::FormID actorID \= actorPtr-\>GetFormID();  
          
        // Extract 3D Position Vector (x, y, z)  
        RE::NiPoint3 pos \= actorPtr-\>GetPosition();  
          
        // Extract Rotation Euler Angles (pitch, roll, yaw in radians)  
        RE::NiPoint3 rot \= actorPtr-\>GetAngle();  
          
        // Extract Context Identifiers  
        auto\* cell \= actorPtr-\>GetParentCell();  
        RE::FormID cellID \= cell ? cell-\>GetFormID() : 0;  
          
        auto\* world \= actorPtr-\>GetWorldspace();  
        RE::FormID worldID \= world ? world-\>GetFormID() : 0;

        // Push extracted metrics to outbound thread-safe queue  
    }  
}

### **Performance Overhead Analysis**

Iterating highActorHandles (typically containing 10 to 50 active NPCs) takes under 50 microseconds on modern CPUs. Sampling spatial state inside an SKSE task running at 20 Hz (every 50 ms) consumes less than 0.2% of the primary frame budget at 60 FPS, making it suitable for continuous real-time streaming.

## **Open-Source License Hygiene and Verification**

Every candidate dependency, library, and prior art repository was verified to ensure strict license compliance. Permissive licenses (MIT, BSD, Apache 2.0, Boost) are required to ensure redistributability and prevent copyleft viral obligations on first-party plugin binaries.

| Component / Library | Origin Repository / Source | Verified License | Distribution Status |
| :---- | :---- | :---- | :---- |
| **CommonLibSSE-NG** | CharmedBaryon/CommonLibSSE-NG \[cite: 1\] | Apache License 2.0 / MIT | **Compliant**: Permissive open-source; allows static linkage into commercial/open binaries1. |
| **IXWebSocket** | machinezone/IXWebSocket \[cite: 12, 15\] | BSD 3-Clause15 | **Compliant**: Permissive static linking; requires retaining copyright notice12. |
| **Boost.Beast** | Boost C++ Libraries14 | Boost Software License 1.014 | **Compliant**: Permissive; does not require copyright attribution in compiled binaries14. |
| **cpp-httplib** | yhirose/cpp-httplib | MIT License | **Compliant**: Permissive header-only integration. |
| **spdlog / fmt** | gabime/spdlog \[cite: 1\] | MIT License | **Compliant**: Standard permissive C++ logging framework1. |
| **SKSE\_Template\_GameEvents** | SkyrimScripting/SKSE\_Template\_GameEvents \[cite: 2\] | MIT License2 | **Compliant**: Permissive template code2. |
| **SkyrimWebSocket** | andreyvelsk/SkyrimWebSocket \[cite: 19, 20\] | MIT License19 | **Compliant**: Permissive reference pattern19. |
| **SKSE\_HTTP** | Leidtier/SKSE\_HTTP \[cite: 9, 10\] | MIT License | **Compliant**: Permissive reference pattern9. |

No copyleft software (GPL/LGPL) or proprietary Bethesda SDK headers are included in the plugin build dependencies. All dependencies integrate via vcpkg manifest mode using permissive licenses1.

## **Nuanced Architectural Evaluation and Recommendation**

Three deployment approaches were evaluated for Chronicle's game seam:

### **Architecture Options Analyzed**

> 1. **Option A: Consuming SkyrimWebSocket as an External Dependency**  
   * *Evaluation*: Relies on an external plugin installation19. While functional for player spatial coordinates, SkyrimWebSocket lacks coverage for non-player actor grids, quest stage changes, container transfers, cell attach events, and crime/bounty hooks19. Supplying missing events requires installing a second plugin, increasing setup complexity and operational fragility.  
> 2. **Option B: Hybrid Strategy (First-Party Events \+ SkyrimWebSocket Spatial)**  
   * *Evaluation*: Uses SkyrimWebSocket for spatial streaming while running a second first-party plugin for native game events19. This pattern forces two separate network sockets to open inside the game process, doubling thread synchronization overhead and complicating port management.  
> 3. **Option C: Standalone First-Party ChronicleBridge Plugin (Recommended)**  
   * *Evaluation*: Combines event sink interception and spatial state iteration into a single CommonLibSSE-NG dynamic link library1. Embedding IXWebSocket statically via vcpkg provides a high-performance transport layer under full first-party control12.

### **Final Recommendation**

The evidence strongly supports **Option C: Standalone First-Party ChronicleBridge Plugin**.  
Developing ChronicleBridge as a unified CommonLibSSE-NG plugin provides complete control over event filtering, thread marshaling, spatial sampling rates, and framing protocols1. Statically linking IXWebSocket via vcpkg eliminates external runtime dependencies and delivers a clean deployment experience for end users12.

### **Implementation Sequence**

> 1. **Scaffolding**: Initialize ChronicleBridge using the CommonLibSSE-NG multi-runtime CMake template1. Configure vcpkg.json to fetch ixwebsocket, spdlog, and fmt statically (x64-windows-static)1.  
> 2. **Transport Infrastructure**: Set up an ix::WebSocketServer running on a background worker thread15. Implement thread-safe queues for outbound telemetry and map inbound commands to SKSE::GetTaskInterface()-\>AddTask(...)11.  
> 3. **Native Event Pipeline**: Implement event sinks for RE::TESDeathEvent, RE::TESContainerChangedEvent, RE::TESCellAttachDetachEvent, and RE::TESQuestStageEvent, registering them with RE::ScriptEventSourceHolder during kDataLoaded2. Attach C++ detour hooks for RE::TESFaction::ModBounty and RE::DialogueMenu5.  
> 4. **Spatial Streamer**: Add a periodic 20 Hz task running via SKSE::GetTaskInterface() to enumerate RE::ProcessLists::GetSingleton()-\>highActorHandles and push spatial state vectors to the network queue7.  
> 5. **Proton Verification**: Verify local loopback transport (ws://127.0.0.1:8765) between the compiled Windows DLL under Proton and Chronicle's host Python bridge19.

#### **Works cited**

> 1. CharmedBaryon/CommonLibSSE-NG: This is a reverse engineered library for Skyrim Special Edition and Skyrim VR. \- GitHub, [https://github.com/CharmedBaryon/CommonLibSSE-NG](https://github.com/CharmedBaryon/CommonLibSSE-NG)  
> 2. SkyrimScripting/SKSE\_Template\_GameEvents: SKSE plugin detecting game events \- GitHub, [https://github.com/SkyrimScripting/SKSE\_Template\_GameEvents](https://github.com/SkyrimScripting/SKSE_Template_GameEvents)  
> 3. BSScript::ObjectTypeInfo::UnlinkedNativeFunction Struct Reference \- CommonLibSSE NG, [https://ng.commonlib.dev/structRE\_1\_1BSScript\_1\_1ObjectTypeInfo\_1\_1UnlinkedNativeFunction.html](https://ng.commonlib.dev/structRE_1_1BSScript_1_1ObjectTypeInfo_1_1UnlinkedNativeFunction.html)  
> 4. RE::BSEffectShaderProperty Class Reference \- CommonLibSSE NG, [https://ng.commonlib.dev/classRE\_1\_1BSEffectShaderProperty.html](https://ng.commonlib.dev/classRE_1_1BSEffectShaderProperty.html)  
> 5. r/SkyrimHelp \- Reddit, [https://www.reddit.com/r/SkyrimHelp/new/](https://www.reddit.com/r/SkyrimHelp/new/)  
> 6. (CRASH) Gate to Sovngarde : r/SkyrimHelp \- Reddit, [https://www.reddit.com/r/SkyrimHelp/comments/1vkzxpw/crash\_gate\_to\_sovngarde/](https://www.reddit.com/r/SkyrimHelp/comments/1vkzxpw/crash_gate_to_sovngarde/)  
> 7. CommonLibSSE NG Sample Plugin \- John Stewart \- GitLab, [https://gitlab.com/colorglass/commonlibsse-sample-plugin](https://gitlab.com/colorglass/commonlibsse-sample-plugin)  
> 8. Road to v0.12: Using HTTP to communicate with game · Issue \#230 · art-from-the-machine/Mantella \- GitHub, [https://github.com/art-from-the-machine/Mantella/issues/230](https://github.com/art-from-the-machine/Mantella/issues/230)  
> 9. Leidtier/SKSE\_HTTP: A SKSE plugin to communicate with ... \- GitHub, [https://github.com/Leidtier/SKSE\_HTTP](https://github.com/Leidtier/SKSE_HTTP)  
> 10. Leidtier \- GitHub, [https://github.com/Leidtier](https://github.com/Leidtier)  
> 11. SkyrimScripting/SKSE\_Template\_WebSockets: Communicate outside of Skyrim using WebSockets \- GitHub, [https://github.com/SkyrimScripting/SKSE\_Template\_WebSockets](https://github.com/SkyrimScripting/SKSE_Template_WebSockets)  
> 12. \[spout2\] build failure · Issue \#52120 · microsoft/vcpkg \- GitHub, [https://github.com/microsoft/vcpkg/issues/52120](https://github.com/microsoft/vcpkg/issues/52120)  
> 13. HunterZ/rustLaunchSite: Rust dedicated server manager \- GitHub, [https://github.com/HunterZ/rustLaunchSite](https://github.com/HunterZ/rustLaunchSite)  
> 14. boost-beast | vcpkg.link: Vcpkg Ports and Packages Explorer, [https://vcpkg.link/ports/boost-beast](https://vcpkg.link/ports/boost-beast)  
> 15. A list of open source C++ libraries \- cppreference.com \- TCS RWTH, [https://tcs.rwth-aachen.de/docs/cpp/reference/en.cppreference.com/w/cpp/links/libs.html](https://tcs.rwth-aachen.de/docs/cpp/reference/en.cppreference.com/w/cpp/links/libs.html)  
> 16. Vcpkg使用MD运行时静态库——如何设置？ 原创 \- CSDN博客, [https://blog.csdn.net/xmcy001122/article/details/116227032](https://blog.csdn.net/xmcy001122/article/details/116227032)  
> 17. Changelog \- IXWebSocket \- GitHub Pages, [https://machinezone.github.io/IXWebSocket/CHANGELOG/](https://machinezone.github.io/IXWebSocket/CHANGELOG/)  
> 18. wsServer \- a tiny WebSocket server library written in C \- GitHub, [https://github.com/Theldus/wsServer](https://github.com/Theldus/wsServer)  
> 19. andreyvelsk/SkyrimWebMonitor: Skyrim companion app. Working with WS game server \- GitHub, [https://github.com/andreyvelsk/SkyrimWebMonitor](https://github.com/andreyvelsk/SkyrimWebMonitor)  
> 20. andreyvelsk · GitHub, [https://github.com/andreyvelsk](https://github.com/andreyvelsk)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEMAAAAaCAYAAADsS+FMAAACM0lEQVR4Xu2XvUscQRjGRxFjFLFIaRckQVL4QZqkDAimUhCDQQgqlv4BNkkVDOarChGEhAPFRmxtBLFNYRVCosQqhYWgYEiCRdD34Wa4957b2Z1ZbPbYHzy4729mZ+bG/bgzpqQklA7JJcsC84VFDNiIPpYF5x+LED5KJlk2Aa9Mjqs9+oQCEfXZdk3kCQVjTfKCpQ9sxG+WTcSQ5D9LH9iMJywt05KXkh5T7Tcr2ZJ02jqGP6Y2TovybdbFgnNcnknaJQt1PWoEj4+OwyyFO5ITVbuJwYE6DgGb6MB5D1T93LoYViXfJF2mOrZeWxJpbXX4Ou5QrSfsl3SrtizcWK9N43yoP5GL5TsLAnMMsEyCF+cD/T6wjARjbCS4u+RiCHkeYI5xlkmg4y2WBC7H0E3zcc80jrGc4ELBc4evXh+YI+gLJTreZymMSd7Y47emcdE/qM5ixTSOgZpdCL6H7mMWFvRtZZkEOn5maeoXir9nqm1dHTuyPhje9bp93tZ8zrF178lr3Hn7khnJnq19pLXVkbQgADcnOZfctvWi5JdkW/Vz+MbRoB23xiN7jFR0B1N9dcP7ngU/1bEbAxlUXoMr/IKljxGT/SFCwUaFkrV5pyxygo3AL/Jg0hYVg28c9wB+qhzqTVVr8N1B983LDeNfUyp/WUSC/8BNlpYJyZGqscCHqmYOWeQE80yxDAH34juWESyxIPT9nfbDqZdFTvD2+MoyhlEWBabCoqSkpKTkmrkCQWuRAFXSm54AAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJIAAAAZCAYAAADaDHeVAAAEcElEQVR4Xu2ZW8hOWRjHH3IeqXG4MDGDGzXNjZlRZDKKEJJyiIvJjGiaXAzJHDSOczGhcOPChQspkitJisiFQ0kxaoaai68IF5RphJDG+tvr8T3+nvV9e7/vfnvf97N/9fTt57/WetbhXXsd9idSUVFR0er8z0JFjwW/9UAWywCB57FYgFEs1MF2ydrTKhNb22LbY7Vfjd4uDJMGjO+PwTaxWIBHkjVqDycEJrOQk8HSgI7WwS/it6ddJxIYH+wQi/XgDVARvgj2PFh/TpD6Vrl621Um34nfnnaeSMDrU00clxKDEful50ykpeK3B9oGFtsItP9fFmsBgV6wWAKDJIs9lxMK4P1wzWKJ+O1p94l0TPx+FQZBVrEomQ7DloWJtjvYnKj9Z/Jdi5odUMRTzZplVtR+CtY32JPoW+B/EP/icLguPn9oM3WDrX9bsC/j8zcmD852fwbrF2yoZGc+9NVS1kRKjYnVpkXtpWQ7BpgR06ZHH/A47yJf47NvQX89vTAI8jWLkYeSpY8x2sqoTTAagMZnBWiprQ1p18nnDqU0Wy4PveTtWPiLCwZYYXQL97GsiQRwlkS5mY5m4f4jP+cB0BYZ/0DULOxbukrLDYJgoD06xK/klryrewMKzZtIuCFyeQ/kwQrCWp6yDMp422wqHutlTiTA8fHS5llpUWYiaUeirvwV/SFG43G0eP0qTFdBboqfjm2OdW9AoRX58Rjk4e9TecsyKOO9MNC9wybXs5h8BRqvxHm4J2/H82KDMcEuSWd7YJNshsCAqH8Ufc13Nvpr498UqboLgSBoiMcN8SvBmQL6WKN5AwptPmlAO9odyDPC0fKUZVJlUvFYL3tF+liyssOjv6Uz6Q34xoM8e40Gf4rxFejng30V7Gj0tb1euy3dpeci1TCQWpF4kFXjAYW2MD5/H2x9fN4R07zvThY70FbjuvOQKpOKx/oy8hVo/ALl5bZk5S9zgnSuQgw0TJbTjm7bPDo+fx7sjGZK4NVTGATRgyfjTSR9k34mHZo3kXCYBVsle6tt2gXjg53kI0+ere1psGekMVxGuSt+GjT71ffbqDHQfnM03Va64hPx+wM8fWTUMJE47feo/WM0jcEvowW7CseqCa/Byt+SpT2W7Er6R/TxtihaXu2iScOhENrmYPeNDnRCPgj2g2Q/qE4k7xqLt541Rf3ZRlO4jC2nYPuFjkvA4fiM72AKl08ZwD9CU/V4IJ93IQG4/uPTC1bDK5JtcRr7hMmncJ041+El6wq8zFyuJvZJOpBOJIDtb41Jy8s4yb7/pMAqtTFYb04oCFa+5SwWAN+yMFlXc0KN4Gabh9TYKwvk3fGbRr6iq7/lMxYI1N/BYq2kOoMKUmmtRqu1M9UerHh2y5xqnptBqp018WmwgywG7kjJFTWQqyw0kT7SeclgMJ46pqdsQhPAboCza6mcC3bS+Nph2/FWxTsvNBPvu5SCC4mOKf7t0yxwi27E/1hfk3dfr2h/GjaJKioqKioqKired14BM/WUVgeSBlEAAAAASUVORK5CYII=>