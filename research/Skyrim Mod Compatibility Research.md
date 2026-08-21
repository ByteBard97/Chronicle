# **Compatibility Infrastructure Assessment and Target Pin Specification for Skyrim SE/AE Engine Integration**

## **The 1.7.99 Transition State and Architectural Impact Analysis**

The release of Skyrim Special Edition update version 1.7.99 by Bethesda Game Studios on August 20, 2026—following a two-and-a-half-year period of structural engine dormancy—introduced targeted modifications to the compiled game binary1. While surface-level patch notes emphasized console mod storage expansions (increasing PlayStation 5 and Xbox partitions to 15 GB)3 and Creation Store UI alignment with Fallout 4 and Starfield1, the internal executable changes significantly disrupted reverse-engineered C++ plugin infrastructure4.

### **Binary Executable Modifications and ABI Instability**

At the binary level, the 1.7.99 patch altered internal class layouts, member field offsets, and function memory addresses across the core game engine4. Base save game file structures and FormID indexing rules remained backwards-compatible, allowing existing save states to load conceptually1. However, runtime execution introduces severe application binary interface (ABI) instability for native extensions4.  
The critical technical issue during the 1.7.99 transition stems from how native C++ plugins interact with game memory4. Historically, Address Library for SKSE Plugins allowed native binaries to survive executable patches by dynamically re-mapping memory offsets5. For 1.7.99, Address Library was updated same-day with a modernized database format modeled after Bethesda's implementation in Starfield4. Nevertheless, because Bethesda modified underlying C++ class structures—such as internal PlayerCharacter layout definitions and engine state flags—updating Address Library alone is insufficient4.  
Native plugins compiled against standard middleware headers (such as CommonLibSSE or CommonLibNG) reference class structures whose compiled member offsets no longer match the 1.7.99 binary4. When an outdated plugin reads or writes to a class member, it accesses invalid memory addresses, causing instant crash-to-desktop (CTD) events or silent save state corruption1. To achieve 1.7.99 compatibility, plugins require updated C++ header definitions from CommonLib maintainers followed by full recompilation4.

### **Core Infrastructure Component Readiness**

The low-level script extender framework responded immediately to the patch, but high-level scripting extensions and memory hooks experienced widespread breakage2.

| Core Infrastructure Component | Version for 1.7.99 | 1.7.99 Compatibility Status | Maintainer Technical Status & Ecosystem Impact |
| :---- | :---- | :---- | :---- |
| **SKSE64** | 2.3.0 | Compatible | Shipped same-day on August 20, 20262. Updated executable loader and primary entry point memory hooks2. |
| **Address Library for SKSE** | Modernized DB Format | Compatible (Database Only) | Database updated same-day4. Resolves function address lookups but cannot auto-fix C++ class layout offset changes4. |
| **powerofthree's Papyrus Extender** | Pending Recompile | Broken | Native C++ binary crashes on launch due to CommonLib offset mismatches; requires header updates and full recompile4. |
| **PapyrusUtil SE** | Pending Recompile | Broken | C++ SKSE plugin fails offset verification; requires explicit recompilation against 1.7.99 binaries4. |
| **SSE Engine Fixes** | Pending Update | Broken | Native hooks fail to patch memory allocations; crashes process during initial loading sequence4. |

### **Community Consensus and Maintainer Timelines**

The consensus among tool maintainers, mod list authors, and framework developers is to freeze active modding environments on game version 1.6.11704. Because 1.7.99 offers no core engine performance improvements or new scripting capabilities for PC users4, maintainers view the update as an unnecessary maintenance burden5. Re-compiling the entire ecosystem of C++ SKSE plugins is estimated to take between two weeks and several months6. Consequently, community consensus strongly favors downpatching or locking installations to version 1.6.11704.

## **Anchor Target Evaluation and AI-NPC Framework Integration**

Modding environments currently anchor to four main game executable targets7. Selecting a development anchor dictates SKSE version alignment, plugin availability, and downpatching requirements7.

| Version Target | SKSE Version | Address Library Availability | Fraction of Active SKSE Plugins Supported | Steam Depot Manifest Hashes (depot\_489831 / 489832 / 489833\) | AI-NPC Framework Compatibility Status |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **1.5.97** (Legacy "SE") | 2.0.202 | Available (Legacy Format)7 | \~95% (Maximum legacy DLL ecosystem coverage)13 | 489831: 7848722008564294070 489832: 8702665189575304780 489833: 228956101062685367410 | Supported via Backported Extended ESL Support (BEES) and legacy plugins13. |
| **1.6.640** (AE Pre-Creations) | 2.2.37 | Available7 | \~90% (Highly stable legacy target)13 | 489831: 3660787314279169352 489832: 2756691988703496654 489833: 529180195221981573512 | Supported by Mantella and legacy CHIM environments16. |
| **1.6.1170** (AE Post-Creations) | 2.2.62 | Available4 | \~85-90% (Modern ecosystem anchor)18 | 489831: 8442952117333549665 489832: 8042843504692938467 489833: 19145806990736419648 | **Primary Recommendation Target.** Native build environment for SkyrimNet14. |
| **1.7.99** (Current Branch) | 2.3.02 | Available (Database only)4 | \<15% (Broken ecosystem)4 | Current Default Main Branch Download2 | **Unsupported.** Native C++ transport bridges fail on runtime launch4. |

### **AI-NPC Framework System Requirements**

AI-driven non-player character frameworks rely on high-frequency communication between Skyrim's game engine and large language model (LLM) inference endpoints14. The primary frameworks maintain distinct architectural approaches and version recommendations:

* **Mantella**: Operates via a two-tier architecture consisting of an SKSE scripting plugin and an external Python server process17. Mantella polls game events, serializes context strings via Papyrus, and transmits HTTP POST requests to its local Python server17. Mantella officially supports game versions **1.6.1170** and **1.5.97**, relying on Papyrus HTTP Utils or SKSE\_HTTP for transport17.  
* **CHIM / MinAI**: The CHIM framework previously utilized the MinAI plugin as an intermediate middleware layer16. However, MinAI has been formally deprecated by its developers, who advise transitioning entirely to SkyrimNet16.  
* **SkyrimNet**: Represents the primary native target for modern AI-NPC implementations14. Built as an all-in-one native C++ SKSE plugin, SkyrimNet eliminates background Python processes, WSL requirements, and intermediate web servers14. SkyrimNet targets **1.6.1170** as its native runtime, offering backwards compatibility for VR and 1.5.97 via compatibility layers14.

## **HTTP and WebSocket Transport Architecture Survey**

Integrating networked external services into Skyrim's runtime requires offloading network I/O from the single-threaded Papyrus virtual machine14. Because Papyrus script execution is bounded by engine frame-budget limits, executing synchronous network calls on the game thread introduces micro-stutters, thread starvation, and script stack dumps14.

| Plugin Architecture | Repository / Source | License Type | Binary Hook Basis | Transport Protocol | Threading & Memory Execution Model | AI Framework Usage |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Papyrus HTTP Utils** | GitHub / Nexus Mods23 | Open Source (MIT) | Address Library Dynamic Mapped | Asynchronous HTTP (GET / POST) with JSON payloads17 | Offloads HTTP requests to background worker threads; returns responses to Papyrus via event callbacks23. | Used by Mantella and legacy Papyrus script bridges17. |
| **SKSE\_HTTP** | Leidtier GitHub17 | Open Source | Address Library Dynamic Mapped24 | Localhost HTTP REST Interface17 | Native thread pool processes JSON string requests; minimal thread-safety validation on Papyrus memory allocation17. | Secondary transport for Mantella installations17. |
| **SkyrimNet Native Transport Engine** | MinLL GitHub14 | Open Source | Address Library Native C++ Plugin14 | Direct Async C++ HTTP/WebSocket \+ Direct Audio Injection14 | Bypasses Papyrus string serialization14. Reads native memory using thread locks and streams audio directly to XAudio214. | **SkyrimNet Native Engine.** Fully integrated transport layer14. |

### **Architectural Comparison: Script Wrappers vs. Native Memory Engines**

Plugins like Papyrus HTTP Utils and SKSE\_HTTP function as low-level networking adapters for Papyrus scripts17. In these architectures, game context must be gathered by Papyrus scripts, serialized into JSON strings inside the Papyrus VM, and passed across the C++ boundary to libcurl or WinINet wrappers17. Returned responses must then be parsed back into Papyrus script objects, generating significant VM garbage collection overhead and frame-rate variance during active dialogue14.  
Conversely, SkyrimNet bypasses Papyrus script serialization entirely14. Its native SKSE plugin queries engine memory directly via C++ background threads using guarded reference-counted entity wrappers14. Spatial positions, visual perceptions, actor states, and inventory data are extracted natively in sub-20ms cycles14. WebSocket streams and HTTP POST requests execute on dedicated C++ worker threads14.  
When returning dialogue synthesized by local or cloud Text-to-Speech (TTS) endpoints, SkyrimNet routes raw audio streams directly into Skyrim's XAudio2 spatialized sound engine14. This grants AI-generated dialogue full 3D positional audio, environmental reverb, occlusion, and ducking without invoking Papyrus audio functions14.

## **Linux and Steam Proton Execution Dynamics**

Executing modded Skyrim environments containing custom C++ SKSE binaries under Linux via Valve's Proton translation layer introduces platform-specific configuration requirements8.

### **Runtime Compatibility and Environment Setup**

SKSE64 version 2.2.6 (for game version 1.6.1170) operates stably under **Proton Experimental** or **GE-Proton 9-x**. The SKSE loader (skse64\_loader.exe) functions as a proxy process that hooks into SkyrimSE.exe at startup.  
Under Linux, native DLL overrides must be defined within the Wine/Proton environment to ensure custom libraries (such as d3d11.dll or winmm.dll used by SSE Engine Fixes or display plugins) take precedence over Wine's built-in stubs. In Steam's game properties, the launch options must be specified as:  
WINEDLLOVERRIDES="winmm,d3d11=n,b" %command%

### **Linux-Specific Steam Depot Pathing Mechanics**

Downloading specific game version manifests via the Steam console on Linux introduces pathing behavior distinct from Windows environments8. Executing the terminal command:

Bash  
steam steam://open/console

opens Steam's internal console tab8. When download\_depot commands finish downloading, Steam prints a Windows-style target folder path in the console log8. However, POSIX file-system isolation redirects the files to a specific local directory based on the Steam package format8:

* **Standard Native Package (Debian/Arch/RHEL .tar/.deb):**  
  \~/.local/share/Steam/ubuntu12\_32/steamapps/content/app\_489830/  
  \[cite: 8\]  
* **Flatpak Container Package:**  
  \~/.var/app/com.valvesoftware.Steam/.local/share/Steam/ubuntu12\_32/steamapps/content/app\_489830/

Developers must copy the extracted contents of these depot subfolders (depot\_489831, depot\_489832, depot\_489833) directly into the active Skyrim installation directory located at \~/.local/share/Steam/steamapps/common/Skyrim Special Edition/8.

### **Persistent Version-Locking via POSIX Permissions**

To prevent Steam's background update service from overwriting downgraded binaries, setting the update policy inside the Steam UI to "Only update this game when I launch it" is necessary but insufficient on its own18. The app manifest file appmanifest\_489830.acf must be write-protected at the file-system level3.  
On POSIX file systems, GUI-based read-only toggles can be bypassed by Steam during client verification routines3. Absolute file write-locking must be enforced via terminal permissions8:

Bash  
\# Apply standard POSIX read-only flag  
chmod 444 \~/.local/share/Steam/steamapps/appmanifest\_489830.acf

\# Apply advanced ext4/xfs immutable attribute lock  
sudo chattr \+i \~/.local/share/Steam/steamapps/appmanifest\_489830.acf

When appmanifest\_489830.acf is set to read-only or immutable, Steam cannot modify the installation status manifest, effectively preventing automatic client updates3.

## **Data Pipeline and Tooling Engine Compatibility**

Creating custom mods requires parsing game records, editing NPC attributes, and compiling plugin files using external tools.

### **Creation Kit 1.7.99 Disruption and Rollback Requirements**

The 1.7.99 update released an updated Creation Kit executable (CreationKit.exe version 1.7.99) containing several functional enhancements1:

* Integrated native localization export support1.  
* Aligned "Search and Replace" workflows with Starfield editor standards1.  
* Enabled loading multiple master files (bAllowMultipleMasterLoads=1) by default1.  
* Enforced consistent file capitalization on archive (.bsa) generation to prevent Linux case-sensitivity asset resolution errors1.

However, plugins compiled with the 1.7.99 Creation Kit can introduce header version mismatches when loaded into older game builds1. Developers working on a downgraded **1.6.1170** game runtime must downpatch the Creation Kit binary to matching 1.6.1130/1.6.640 depots (app\_1946180), or use *Creation Kit Platform Extended (CKPE)* to ensure master file compatibility12.

### **xEdit (SSEEdit) and Mutagen Pipeline Compatibility**

* **xEdit / SSEEdit (v4.1.5+):** Fully compatible across versions 1.5.97, 1.6.640, 1.6.1170, and 1.7.9928. SSEEdit parses raw record sub-blocks (NPC\_, QUST, CELL, DIAL) directly from .esm/.esp/.esl master files independent of the game executable28.  
* **Mutagen / Synthesis (C\# Framework):** Operates entirely outside runtime memory injection. Mutagen parses Bethesda binary record formats directly, remaining fully functional across all game versions without executable version dependencies.

## **Comprehensive Recommendation and Target Pin Protocol**

For a new mod project starting development, the recommended environment target is **Game Version 1.6.1170** paired with **SKSE64 2.2.6**2. This anchor point provides optimal ecosystem stability, access to modern C++ SKSE extensions, and full integration support for SkyrimNet and advanced AI frameworks7.

### **Recommended Component Pin Specification**

| Component Layer | Software / Plugin Name | Exact Target Version | Compatibility Validation Notes |
| :---- | :---- | :---- | :---- |
| **Base Executable** | Skyrim Special Edition | 1.6.1170.0 | Downgraded via Steam console depot downloads8. |
| **Script Extender** | SKSE64 | 2.2.6 | Compiled specifically for runtime 1.6.11702. |
| **Address Engine** | Address Library for SKSE Plugins | All-in-one AE (v0.10.0+) | Provides dynamic offset mapping for 1.6.11704. |
| **Scripting Utility** | powerofthree's Papyrus Extender | 6.3.0 (or 5.9.0) | Compiled against 1.6.1170 CommonLib headers19. |
| **Scripting Utility** | PapyrusUtil SE | 4.6 | Anniversary Edition build matching 1.6.11707. |
| **Engine Patches** | SSE Engine Fixes | v6.1.1 (1.6.1170 build) | Resolves max handle allocations and save truncations29. |
| **AI Infrastructure** | SkyrimNet Framework | Latest Release | Native target build for game version 1.6.117014. |

### **Execution Protocol for Linux / Steam Proton Environments**

The following terminal procedure establishes a locked 1.6.1170 development environment under Linux.

#### **Step 1: Open Steam Console and Download Depots**

Launch the Steam client via terminal to enable console logging:

Bash  
steam steam://open/console

In the Steam client console tab, execute the three 1.6.1170 depot download commands sequentially8. Wait for the console to print Depot download complete before submitting the next line8:  
download\_depot 489830 489831 8442952117333549665  
download\_depot 489830 489832 8042843504692938467  
download\_depot 489830 489833 1914580699073641964

#### **Step 2: Extract Downloaded Depots to Skyrim Directory**

In your Linux terminal, set environment variables and copy the downloaded depot files into your active Skyrim directory8:

Bash  
\# Define local path variables  
export DEPOT\_DIR="$HOME/.local/share/Steam/ubuntu12\_32/steamapps/content/app\_489830"  
export GAME\_DIR="$HOME/.local/share/Steam/steamapps/common/Skyrim Special Edition"

\# Copy downloaded depots over the game installation  
cp \-rf "$DEPOT\_DIR"/depot\_489831/\* "$GAME\_DIR"/  
cp \-rf "$DEPOT\_DIR"/depot\_489832/\* "$GAME\_DIR"/  
cp \-rf "$DEPOT\_DIR"/depot\_489833/\* "$GAME\_DIR"/

#### **Step 3: Enforce Manifest File Lock**

Lock the Steam app manifest file to prevent background auto-updates3:

Bash  
export MANIFEST\_FILE="$HOME/.local/share/Steam/steamapps/appmanifest\_489830.acf"

\# Apply read-only mode  
chmod 444 "$MANIFEST\_FILE"

\# Apply immutable attribute lock (requires superuser privileges)  
sudo chattr \+i "$MANIFEST\_FILE"

#### **Step 4: Install Extender Binaries and Configure Proton**

> 1. Extract SKSE64 version 2.2.6 directly into $GAME\_DIR/, placing skse64\_loader.exe and skse64\_1\_6\_1170.dll alongside SkyrimSE.exe2.  
> 2. Deploy Address Library AE (v0.10.0+), po3 Papyrus Extender (v6.3.0), and PapyrusUtil SE (v4.6) into $GAME\_DIR/Data/ using your mod manager7.  
> 3. In Steam, right-click *The Elder Scrolls V: Skyrim Special Edition* \-\> **Properties** \-\> **General** \-\> **Launch Options**, and configure the override string:  
>    WINEDLLOVERRIDES="winmm,d3d11=n,b" %command%  
> 4. Configure your mod manager (such as Mod Organizer 2 running under Proton) to launch skse64\_loader.exe directly10.

This setup establishes a stable, update-proof **1.6.1170** development foundation, fully compatible with SkyrimNet, C++ SKSE extensions, and local HTTP bridge frameworks under Linux8.

#### **Works cited**

> 1. Bethesda's New 1.7.99 Skyrim Update May Break Your Modded Save, but You Can Freeze the Game Version \- Here's How \- Wccftech, [https://wccftech.com/skyrim-1-7-99-update-modded-save-freeze-version/](https://wccftech.com/skyrim-1-7-99-update-modded-save-freeze-version/)  
> 2. Skyrim Script Extender (SKSE), [https://skse.silverlock.org/](https://skse.silverlock.org/)  
> 3. The Elder Scrolls V: Skyrim Special Edition \- Steam Community, [https://steamcommunity.com/app/489830](https://steamcommunity.com/app/489830)  
> 4. Skyrim Update \- August 20 : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1vtmtg2/skyrim\_update\_august\_20/](https://www.reddit.com/r/skyrimmods/comments/1vtmtg2/skyrim_update_august_20/)  
> 5. Skyrim Update: What You Need To Know. : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1vto83n/skyrim\_update\_what\_you\_need\_to\_know/](https://www.reddit.com/r/skyrimmods/comments/1vto83n/skyrim_update_what_you_need_to_know/)  
> 6. Anyone else stuck waiting for SSE Engine Fixes to update? Anyone have any fixes? \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1vtpsts/anyone\_else\_stuck\_waiting\_for\_sse\_engine\_fixes\_to/](https://www.reddit.com/r/skyrimmods/comments/1vtpsts/anyone_else_stuck_waiting_for_sse_engine_fixes_to/)  
> 7. SKSE Plugin Status | Modding.wiki, [https://modding.wiki/en/skyrim/users/skse-plugins](https://modding.wiki/en/skyrim/users/skse-plugins)  
> 8. Skyrim newest 1.7.99.0 downgrade back to 1.6.1170 : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1vtnsga/skyrim\_newest\_17990\_downgrade\_back\_to\_161170/](https://www.reddit.com/r/skyrimmods/comments/1vtnsga/skyrim_newest_17990_downgrade_back_to_161170/)  
> 9. It's time to admit that Bethesda doesn't care about free PC modding anymore because it gets in their way. That's why we need a Skyrim equivalent of OpenMW : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1vtw4s8/its\_time\_to\_admit\_that\_bethesda\_doesnt\_care\_about/](https://www.reddit.com/r/skyrimmods/comments/1vtw4s8/its_time_to_admit_that_bethesda_doesnt_care_about/)  
> 10. Guide :: Downgrade To 1.5.97 \- Steam Community, [https://steamcommunity.com/sharedfiles/filedetails/?id=3185468658](https://steamcommunity.com/sharedfiles/filedetails/?id=3185468658)  
> 11. what the F\*ck Bethesda\!\! :: The Elder Scrolls V: Skyrim Special Edition Allgemeine Diskussionen \- Steam Community, [https://steamcommunity.com/app/489830/discussions/0/6495968375635711807/?l=german](https://steamcommunity.com/app/489830/discussions/0/6495968375635711807/?l=german)  
> 12. Skyrim \- Downgrade to Fix Mods\! (Revert To 1.5.97 & 1.6.640) 2026 \- YouTube, [https://www.youtube.com/watch?v=K6EY6Xz2tJ0](https://www.youtube.com/watch?v=K6EY6Xz2tJ0)  
> 13. How to Downgrade Skyrim Anniversary Edition to Special Edition & Disable Steam Updates In 2025 \- YouTube, [https://www.youtube.com/watch?v=S31FXPEcSts](https://www.youtube.com/watch?v=S31FXPEcSts)  
> 14. Public facing files for SkyrimNet \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin](https://github.com/MinLL/SkyrimNet-GamePlugin)  
> 15. Downgraded skyrim to 1.6.640 and now textures and meshes are ruined. :: The Elder Scrolls V: Skyrim Special Edition General Discussions \- Steam Community, [https://steamcommunity.com/app/489830/discussions/0/4211497459237753894/](https://steamcommunity.com/app/489830/discussions/0/4211497459237753894/)  
> 16. GitHub \- MinLL/MinAI: Bridge between LLMs and various Skyrim Mods, [https://github.com/MinLL/MinAI](https://github.com/MinLL/MinAI)  
> 17. Road to v0.12: Using HTTP to communicate with game · Issue \#230 · art-from-the-machine/Mantella \- GitHub, [https://github.com/art-from-the-machine/Mantella/issues/230](https://github.com/art-from-the-machine/Mantella/issues/230)  
> 18. Did you just get auto-updated to SSE 1170 and have all your mods broken? Well boy, do I have the answer for you\! : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/199493e/did\_you\_just\_get\_autoupdated\_to\_sse\_1170\_and\_have/](https://www.reddit.com/r/skyrimmods/comments/199493e/did_you_just_get_autoupdated_to_sse_1170_and_have/)  
> 19. Changelog | Masterstroke \- FG's Modlists, [https://fgsmodlists.com/masterstroke/changelog/](https://fgsmodlists.com/masterstroke/changelog/)  
> 20. Skyrim 1.6.659 (GOG) and essential fixes update : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/yys1ja/skyrim\_16659\_gog\_and\_essential\_fixes\_update/](https://www.reddit.com/r/skyrimmods/comments/yys1ja/skyrim_16659_gog_and_essential_fixes_update/)  
> 21. Skyrim Update Scheduled for August 20 : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1vspe5o/skyrim\_update\_scheduled\_for\_august\_20/](https://www.reddit.com/r/skyrimmods/comments/1vspe5o/skyrim_update_scheduled_for_august_20/)  
> 22. Real-Time AI NPCs in VR | Mantella Update : r/skyrimvr \- Reddit, [https://www.reddit.com/r/skyrimvr/comments/1izmkii/realtime\_ai\_npcs\_in\_vr\_mantella\_update/](https://www.reddit.com/r/skyrimvr/comments/1izmkii/realtime_ai_npcs_in_vr_mantella_update/)  
> 23. \[mod\] Dragon Nexus \- red Dragonborn : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1sn5994/mod\_dragon\_nexus\_dragonborn\_network/?tl=es-419](https://www.reddit.com/r/skyrimmods/comments/1sn5994/mod_dragon_nexus_dragonborn_network/?tl=es-419)  
> 24. Leidtier/SKSE\_HTTP: A SKSE plugin to communicate with ... \- GitHub, [https://github.com/Leidtier/SKSE\_HTTP](https://github.com/Leidtier/SKSE_HTTP)  
> 25. Releases · MinLL/SkyrimNet-GamePlugin \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin/releases](https://github.com/MinLL/SkyrimNet-GamePlugin/releases)  
> 26. SeverActions \- A comprehensive action framework for SkyrimNet. Adds 38+ NPC actions, survival system, travel, arrest, crafting, follow management, and more. \- GitHub, [https://github.com/Severause/SeverActions](https://github.com/Severause/SeverActions)  
> 27. New Update ??? (1.6.1170) : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1990h8h/new\_update\_161170/](https://www.reddit.com/r/skyrimmods/comments/1990h8h/new_update_161170/)  
> 28. Changelog \- Lexy's LOTD SE \- Live, [https://lexyslotd.com/guide/changelog/](https://lexyslotd.com/guide/changelog/)  
> 29. Skyrim AE Mod List and Installation Guide | PDF | Computer File \- Scribd, [https://www.scribd.com/document/702802013/Skyrim-AE-Vortex-Mod-List-23-10-27](https://www.scribd.com/document/702802013/Skyrim-AE-Vortex-Mod-List-23-10-27)  
> 30. CHANGELOG.md \- Geborgen/nordic-souls \- GitHub, [https://github.com/Geborgen/nordic-souls/blob/main/CHANGELOG.md](https://github.com/Geborgen/nordic-souls/blob/main/CHANGELOG.md)  
> 31. I don't know if i have the right SKSE installed? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1digh3j/i\_dont\_know\_if\_i\_have\_the\_right\_skse\_installed/](https://www.reddit.com/r/skyrimmods/comments/1digh3j/i_dont_know_if_i_have_the_right_skse_installed/)  
> 32. Help with Modded Landscape issue :: The Elder Scrolls V: Skyrim Special Edition Загальні обговорення \- Steam Community, [https://steamcommunity.com/app/489830/discussions/0/4339861173658072475/?l=ukrainian](https://steamcommunity.com/app/489830/discussions/0/4339861173658072475/?l=ukrainian)