# **Technical Evaluation of Native BarterMenu Hooking, SKSE Virtual Table Chaining, and Engine-Level Price Calculation Compatibility**

In the reverse engineering of Bethesda’s Creation Engine, the modification of transactional mechanics via native dynamic link libraries (DLLs) represents a powerful alternative to traditional record and script edits1. Within the architecture of ChronicleBridge, the proposed price-markup feature intercepts vendor transactions by overwriting a virtual method table (vtable) function pointer in RE::BarterMenu—specifically targeting the slot associated with PostCreate—via CommonLibSSE-NG3.  
Evaluating the engineering feasibility and compatibility profile of this write path requires examining the native binary landscape of Skyrim Special Edition (SE) and Anniversary Edition (AE)4. This includes auditing the implementation mechanisms of prominent trade and economy mods, analyzing community standards for virtual table interception, diagnosing known crash vectors, and detailing the structural divergence between user interface (UI) rendering and the engine's core barter transaction routines.

## **Architectural Survey of Economy Overhauls and Native Barter Plugins**

A prevalent misconception in Skyrim modding is that comprehensive trading and price overhauls operate through low-level binary hooks. In reality, the modding ecosystem displays a clear bifurcation: economy overhauls alter game mechanics via high-level engine data structures, whereas native SKSE plugins interface with the barter menu strictly for interface enhancement, frame unpausing, or arithmetic bug fixes.

| Mod Identifier | Core Technology | Binary / Hook Target | Direct Conflict Vector with Chronicle |
| :---- | :---- | :---- | :---- |
| **Trade and Barter** \[cite: 6\] | Papyrus, Perks, Spells, Actor Values | None (No native DLL)6 | Low; engine pricing formulas diverge from Chronicle's UI override6 |
| **Trade Routes** \[cite: 8, 9\] | Papyrus, Leveled Containers | None (No native DLL)8 | Negligible; alters merchant supply inventories dynamically9 |
| **Better Barter** \[cite: 11\] | ESM/ESP Record Edits | None (No native DLL) | Negligible; rebalances fBarterMin and fBarterMax GMSTs12 |
| **Skyrim Souls RE** \[cite: 13\] | Native C++ SKSE Plugin | RE::BarterMenu Creator / Tasklet13 | Severe; unpauses UI thread, exposing blocking IPC to race conditions13 |
| **moreHUD Inventory** \[cite: 14\] | Native C++ (CommonLibSSE) | RE::BarterMenu::itemList / Scaleform14 | Moderate; concurrent iteration over item structures risks memory faults14 |
| **Barter Limit Fix** \[cite: 15, 16\] | Native C++ (CommonLibSSE) | Assembly patch in SkyrimSE.exe \[cite: 16, 17\] | Moderate; enforces 32-bit math when vendor purse exceeds 32,767 gold15 |
| **Scrambled Bugs** \[cite: 16\] | Native C++ (CommonLibSSE) | Engine Barter Perk Entry Detours16 | Low; fixes vanilla perk calculation logic in native code16 |

### **Implementation Realities of Prominent Economy Overhauls**

Analysis of the codebase and internal record structure of *Trade and Barter* demonstrates that despite requiring SKSE and SkyUI, the mod does not contain a native C++ plugin6. Its SKSE dependency is solely tied to running Papyrus script utility extensions and rendering its Mod Configuration Menu (MCM)6. The dynamic pricing formulas in *Trade and Barter*—adjusting margins based on faction alignment, racial disposition, Thane status, and regional merchant investments—are driven by perk structures (PERK), hidden passive spells (SPEL), and runtime actor value alterations (SetActorValue) applied to the player character6.  
Similarly, *Trade Routes* implements dynamic regional supply and demand through periodic Papyrus event scripts that modify merchant chest leveled lists (CONT and LVLI records) and dynamically adjust price margins via quest perks8. Mods such as *Better Barter*, *Evolving Economy*, and *True Medieval Economy* merely modify base item entries or vanilla Game Settings (GMSTs) such as fBarterMax and fBarterMin11. None of these economy mods hook into virtual function tables or patch memory addresses within SkyrimSE.exe.

### **Native SKSE Plugins Interfacing with Barter Systems**

While economy overhauls operate on high-level records, several widespread native plugins directly hook the barter menu or the underlying native calculation routines:

* *Skyrim Souls RE / Updated*: Intercepts Skyrim’s menu framework to prevent background engine pauses during UI interactions13. Rather than patching the vtable directly, it hooks the menu creator function within RE::MessageMenuManager to re-register a custom unpaused creator instance while preserving a reference to the original function13. It also alters window flags and input handling at the native level13.  
* *moreHUD Inventory Edition*: Built upon CommonLibSSE, this plugin loads custom Scaleform movie clips directly into bartermenu.swf, inventorymenu.swf, and containermenu.swf14. It iterates through RE::BarterMenu::itemList to extract entry data, attaching additional ActionScript 2.0 properties (such as enchantment statuses and weight-to-value metrics)14.  
* *Barter Limit Fix*: Resolves an engine bug where merchants possessing over 32,767 gold (the 16-bit signed integer boundary) fail to transfer currency to the player upon sales15. The plugin injects direct x64 assembly patches into the transaction routines of SkyrimSE.exe, forcing full 32-bit arithmetic16.  
* *Scrambled Bugs*: Applies patches directly to native perk calculation call sites, correcting engine oversights regarding how Speechcraft haggling perks calculate buy versus sell values16.

## **Community Standards for Virtual Table Interception in SKSE Plugins**

Modifying virtual method tables in an x64 Windows executable requires manipulating memory structures located in the read-only .rdata section of the binary1. In the Skyrim engine, a class vtable is globally shared across all instances of that class rather than duplicated per object.

### **The Chained Thunk Convention**

The recognized standard for hooking virtual methods within the CommonLibSSE and SKSE ecosystems is the chained thunk pattern1. Under this convention, a plugin must never perform a destructive write that discards the preexisting function pointer1. Instead, the plugin must capture and preserve the existing address before writing its own hook function into the table1. During execution, the hook must invoke the preserved pointer, ensuring all previously loaded plugins execute their logic1.

C++  
struct BarterMenuHook  
{  
    static constexpr std::size\_t VTABLE\_INDEX \= /\* Target Slot Index \*/;  
    using FnCallback \= void(\*)(RE::BarterMenu\*);  
    static inline REL::Relocation\<FnCallback\> original\_func;

    static void Hook\_Callback(RE::BarterMenu\* a\_this)  
    {  
        // 1\. Invoke prior hook or base engine implementation  
        original\_func(a\_this);

        // 2\. Execute custom Chronicle social standing price calculation  
        ApplyPriceMarkup(a\_this);  
    }

    static void Install()  
    {  
        REL::Relocation\<std::uintptr\_t\*\> vtable{ RE::VTABLE\_BarterMenu\[0\] };  
        original\_func \= vtable.write\_vfunc(VTABLE\_INDEX, \&Hook\_Callback);  
    }  
};

SKSE loads native plugins alphabetically from the Data/SKSE/Plugins/ directory1. If Plugin A installs a hook into a vtable slot, it captures the engine's base function pointer and replaces the slot with its own address1. When Plugin B subsequent in the load sequence hooks the identical slot, it captures Plugin A’s entry as its target1. This creates a last-in, first-out (LIFO) call chain:

> 1. Engine triggers the virtual function call through the vtable pointer.  
> 2. Execution jumps to Plugin B’s hook.  
> 3. Plugin B executes pre-processing, then calls its preserved pointer.  
> 4. Execution routes to Plugin A’s hook.  
> 5. Plugin A executes pre-processing, then calls the original engine routine.  
> 6. Call stack returns back through Plugin A and Plugin B.

If a developer implements a destructive overwrite without capturing the preceding pointer, any plugin loaded prior in the alphabetical sequence is severed from execution1.

### **Dedicated Interception Frameworks: DKUtil and Trampoline**

Modern native plugin development frequently adopts abstraction libraries such as dkutil to standardize hook stability19. The dkutil::hook::VMTHook utility provides template-driven virtual table swapping that automatically coordinates page permissions via VirtualProtect, handles pointer atomic storage, and prevents race conditions during initialization19.  
In contrast, SKSE's native Trampoline facility is designed for arbitrary code redirection within executable memory (.text), replacing five-byte or fourteen-byte instruction sequences with relative or absolute jumps (write\_branch / write\_call)18. While Trampoline is standard for mid-function call interception, vtable substitution remains the standard mechanism for altering object lifecycle methods18.

## **Architectural Vulnerabilities in Chronicle's Barter Hook**

Directly hooking RE::BarterMenu to modify vendor pricing structures introduces three severe engineering liabilities: class lifecycle mismatch, visual-functional state desynchronization, and UI thread starvation.

### **Class Lifecycle Mismatch in CommonLibSSE**

In CommonLibSSE-NG, RE::BarterMenu inherits from RE::IMenu21. While RE::IMenu declares lifecycle methods such as PostCreate, this virtual method is not uniformly implemented across all menu subclasses22. The base game uses PostCreate almost exclusively for character initialization interfaces, such as RE::RaceSexMenu22.  
RE::BarterMenu relies primarily on Accept to bind its ActionScript interface and PostDisplay for post-rendering tasks22. Consequently, targeting PostCreate on RE::BarterMenu exposes two primary points of failure:

> 1. The slot may contain a no-op stub inherited from IMenu, meaning the engine invokes it prior to Flash initialization22. At this stage, the menu’s movie view (uiMovie) and inventory data lists (itemList) are uninstantiated pointers14. Attempting to access item entries causes immediate null-pointer dereferencing, resulting in an access violation (0xC0000005)25.  
> 2. If the slot is completely unused by BarterMenu in specific runtime versions (such as AE 1.6.1170 versus SE 1.5.97), the hook will simply never execute, rendering the social pricing feature inert15.

### **Visual Versus Functional Engine Desynchronization**

The most critical architectural liability of Chronicle’s approach is the complete decoupling of the user interface presentation layer from the core game transaction handler.  
Skyrim divides bartering into two distinct sub-systems:

* **The User Interface (RE::BarterMenu)**: An ActionScript 2.0 interface (bartermenu.swf) wrapped in a C++ container14. Its responsibility is strictly representational: it queries the items in the player's and merchant's containers, queries the engine for baseline prices, formats the resulting numbers, and displays them on the screen14.  
* **The Transaction Engine**: Low-level assembly routines located within SkyrimSE.exe tied to PlayerCharacter and Actor barter processes. When the player clicks an item in the UI to finalize a transaction, the engine does not inspect the string or number rendered on the UI screen. Instead, it recomputes the cost natively using item base values, Speechcraft actor values, GMST pricing curve constants (fBarterMax, fBarterMin), and conditional perk entry points12.

If ChronicleBridge intercepts RE::BarterMenu and adjusts the values populated into the UI lists, the player will observe the altered price on the item card14. However, when the transaction is confirmed, the native engine routine recalculates the cost using vanilla formulas. The gold deducted from or granted to the player will match the vanilla engine computation, completely diverging from the price shown in Chronicle's UI16.  
This divergence creates game-breaking edge cases:

* If a vendor markup causes an item to display as costing 100 gold while the engine values it at 200 gold, a player holding 150 gold will be permitted by the UI to click the purchase button. However, the transaction engine will either fail silently due to insufficient funds, or force the player's gold purse into negative values.  
* Conversely, if Chronicle discounts an item to 100 gold from 200 gold, the purchase will succeed visually, but the engine will deduct the full 200 gold, baffling the user and generating persistent bug reports regarding phantom currency loss.

### **UI Thread Starvation and Unpaused Menus**

Chronicle relies on an external service to simulate social relationships, rumors, and grudges. If ChronicleBridge performs synchronous inter-process communication (IPC) over a network socket, named pipe, or file stream within a UI vtable callback, it blocks the main execution thread.  
This issue is amplified when players use *Skyrim Souls RE*, which unpauses the barter interface13. In an unpaused state, BarterMenu processes input and updates its Scaleform views concurrently with game physics, AI processing, and actor updates13. Any latency introduced by waiting for external simulation data will freeze the rendering pipeline, causing framerate drops, audio stuttering, or crashes13.

## **Documented Native Conflicts and Crash Profiles**

Cross-referencing crash logs generated by diagnostic utilities like CrashLogger.dll reveals distinct crash profiles associated with improper UI and barter hooks25:

> 1. **Calling Convention and Register Clobbering**: Virtual function calls on x64 Windows utilize the Microsoft x64 calling convention, where RCX stores the this pointer, and registers RDX, R8, and R9 carry the first three function arguments. Furthermore, caller-saved registers and stack alignment rules require 32 bytes of shadow space. In crash dumps where developers implemented custom assembly trampolines instead of standard C++ thunks, crashes frequently manifest at SkyrimSE.exe+0x15CCFC or inside UI vtable handlers due to improper stack unwinding or corrupted non-volatile registers28.  
> 2. **Heap Memory Corruption via ScrapHeap**: During the population of BarterMenu::itemList, the game utilizes a fast, short-lived memory pool known as RE::ScrapHeap28. When plugins such as *moreHUD Inventory Edition* walk the item list while another plugin concurrently alters item entries or pointers without acquiring the internal UI locks, the ScrapHeap state becomes corrupted14. This produces delayed access violation crashes long after the barter menu has been closed25.  
> 3. **Gold Limit Truncation Crashes**: If Chronicle applies aggressive price markups that inflate a merchant's total held gold or transaction size beyond signed integer boundaries, the transaction fails or causes gold subtraction arithmetic to wrap around, inducing inventory state corruption unless mitigated by *BarterLimitFix*15.

## **Technical Recommendations for ChronicleBridge**

To deliver social standing price adjustments without destabilizing the engine, introducing visual-functional desynchronization, or colliding with native UI plugins, the following architectural revisions are required.

### **Target Native Price Calculation Routines**

Chronicle must abandon UI vtable patching in favor of detouring the engine's internal barter calculation function. By hooking the native price calculation subroutines via an SKSE Trampoline (SKSE::GetTrampoline().write\_call or write\_branch), the modified price is returned universally18. The UI queries this function when rendering item cards, and the transaction engine invokes this identical routine when processing trades. This guarantees perfect synchronization between the visual interface and currency deduction without touching RE::BarterMenu's vtable.

### **Employ Engine Perk Points or Actor Values**

Rather than maintaining custom assembly detours, Chronicle can leverage existing engine extension hooks. By assigning the player character a background social perk that utilizes the native Apply Barter Mod perk entry point, Chronicle can dynamically alter an underlying actor value or global variable whenever a dialogue interaction begins. Mods such as *Trade and Barter* and *Scrambled Bugs* validate that the engine natively and reliably scales prices when driven through perk entry points, completely bypassing vtable vulnerabilities6.

### **Asynchronous State Caching**

To eliminate the danger of thread starvation—especially in environments featuring *Skyrim Souls RE*—all social calculation data must be decoupled from UI invocation13. The ChronicleBridge C++ plugin must continuously synchronize with the external simulation service in the background, caching each Whiterun NPC’s current trade modifier in a thread-safe local hash map (std::unordered\_map\<RE::FormID, float\>). When the barter routine executes, it performs an immediate, non-blocking ![][image1] memory lookup, completely removing IPC latency from the game's render and logic loops.

### **Strict Call-Through Chaining for Auxiliary UI Hooks**

If Chronicle must retain a UI-level hook to render custom social icons or reputation tooltips within bartermenu.swf, the implementation must adhere strictly to the thunk call-through pattern1. The plugin must utilize REL::Relocation::write\_vfunc or dkutil::hook::VMTHook to preserve the previous function pointer, avoid destructive overwriting, and target Accept or PostDisplay rather than the uninstantiated PostCreate slot1.

#### **Works cited**

> 1. take-all-lockpicks-vr/README.md at main \- GitHub, [https://github.com/AirWolf359/take-all-lockpicks-vr/blob/main/README.md](https://github.com/AirWolf359/take-all-lockpicks-vr/blob/main/README.md)  
> 2. Hytale's modding API is great for accessibility, but we need SKSE, [https://www.reddit.com/r/hytale/comments/1tktikn/hytales\_modding\_api\_is\_great\_for\_accessibility/](https://www.reddit.com/r/hytale/comments/1tktikn/hytales_modding_api_is_great_for_accessibility/)  
> 3. xmake fails on std::to\_underlying in latest c++23 version on MSVC, [https://github.com/xmake-io/xmake/issues/5032](https://github.com/xmake-io/xmake/issues/5032)  
> 4. CharmedBaryon/CommonLibSSE-NG \- GitHub, [https://github.com/CharmedBaryon/CommonLibSSE-NG](https://github.com/CharmedBaryon/CommonLibSSE-NG)  
> 5. Runtime Targeting \- CharmedBaryon/CommonLibSSE-NG GitHub, [https://github-wiki-see.page/m/CharmedBaryon/CommonLibSSE-NG/wiki/Runtime-Targeting](https://github-wiki-see.page/m/CharmedBaryon/CommonLibSSE-NG/wiki/Runtime-Targeting)  
> 6. Trade and Barter | The Elder Scrolls Mods Wiki \- Fandom, [https://tes-mods.fandom.com/wiki/Trade\_and\_Barter](https://tes-mods.fandom.com/wiki/Trade_and_Barter)  
> 7. Economy overhauls no skse : r/SkyrimModsXbox \- Reddit, [https://www.reddit.com/r/SkyrimModsXbox/comments/vagxlz/economy\_overhauls\_no\_skse/](https://www.reddit.com/r/SkyrimModsXbox/comments/vagxlz/economy_overhauls_no_skse/)  
> 8. Wyrmstooth \- Skyrim Créations \- Bethesda.net, [https://bethesda.net/fr/mods/skyrim/mod-detail/4199215](https://bethesda.net/fr/mods/skyrim/mod-detail/4199215)  
> 9. Master Trader \- TheThirdRace.com, [https://thethirdrace.com/games/skyrim/my-mods/master-trader.aspx](https://thethirdrace.com/games/skyrim/my-mods/master-trader.aspx)  
> 10. Modding Question: Leveled Items and Containers \- Is my ... \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/db4g34/modding\_question\_leveled\_items\_and\_containers\_is/](https://www.reddit.com/r/skyrimmods/comments/db4g34/modding_question_leveled_items_and_containers_is/)  
> 11. Mods that are in your top 100, but have less than 500 endorsements, [https://www.reddit.com/r/skyrimmods/comments/yxbl7w/mods\_that\_are\_in\_your\_top\_100\_but\_have\_less\_than/](https://www.reddit.com/r/skyrimmods/comments/yxbl7w/mods_that_are_in_your_top_100_but_have_less_than/)  
> 12. Skyrim SE & Skyrim AE Ultimate Modding Guide \- All In One, [https://www.sinitargaming.com/skyrim\_se.html](https://www.sinitargaming.com/skyrim_se.html)  
> 13. Vermunds/SkyrimSoulsRE: A mod for The Elder Scrolls V: Skyrim, [https://github.com/Vermunds/SkyrimSoulsRE](https://github.com/Vermunds/SkyrimSoulsRE)  
> 14. ahzaab/moreHUDInventory: moreHUD Inventory Edition Plugin, [https://github.com/ahzaab/moreHUDInventory](https://github.com/ahzaab/moreHUDInventory)  
> 15. Skyrim SE v1.6.1170 mod question. : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1qhys7i/skyrim\_se\_v161170\_mod\_question/](https://www.reddit.com/r/skyrimmods/comments/1qhys7i/skyrim_se_v161170_mod_question/)  
> 16. GitHub \- rethesda/SKSE64Plugins-KernalsEgg, [https://github.com/rethesda/SKSE64Plugins-KernalsEgg](https://github.com/rethesda/SKSE64Plugins-KernalsEgg)  
> 17. Skyrim SE v1.6.1170 mod question. \- Reddit, [https://www.reddit.com/r/skyrim/comments/1qhyrko/skyrim\_se\_v161170\_mod\_question/](https://www.reddit.com/r/skyrim/comments/1qhyrko/skyrim_se_v161170_mod_question/)  
> 18. Need help understanding trampoline hooks in SKSE plugins \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1r7u2eq/need\_help\_understanding\_trampoline\_hooks\_in\_skse/](https://www.reddit.com/r/skyrimmods/comments/1r7u2eq/need_help_understanding_trampoline_hooks_in_skse/)  
> 19. DKUtil \- GitLite, [https://gitlite.dev/detail.php?id=B6AmqaCPUSmnty4qv\_IBv7F2\_YxvXWVrSMRKtc6TUO8\&lang=en](https://gitlite.dev/detail.php?id=B6AmqaCPUSmnty4qv_IBv7F2_YxvXWVrSMRKtc6TUO8&lang=en)  
> 20. Help with hook in commonlib ng. : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1ox944m/help\_with\_hook\_in\_commonlib\_ng/](https://www.reddit.com/r/skyrimmods/comments/1ox944m/help_with_hook_in_commonlib_ng/)  
> 21. Class Hierarchy \- CommonLibSSE NG, [https://ng.commonlib.dev/hierarchy.html](https://ng.commonlib.dev/hierarchy.html)  
> 22. Class Members \- Functions \- CommonLibSSE (powerof3), [https://ryan.commonlib.dev/functions\_func\_p.html](https://ryan.commonlib.dev/functions_func_p.html)  
> 23. Class Members \- Functions \- CommonLibSSE NG, [https://ng.commonlib.dev/functions\_func\_p.html](https://ng.commonlib.dev/functions_func_p.html)  
> 24. Class Members \- Functions \- CommonLibSSE NG, [https://ng.commonlib.dev/functions\_func.html](https://ng.commonlib.dev/functions_func.html)  
> 25. GitHub \- parkerchace/SkyrimCrashGuard, [https://github.com/parkerchace/SkyrimCrashGuard](https://github.com/parkerchace/SkyrimCrashGuard)  
> 26. SkyUI Installation and Features Guide | PDF \- Scribd, [https://www.scribd.com/document/384886488/Readme-SkyUI-txt](https://www.scribd.com/document/384886488/Readme-SkyUI-txt)  
> 27. NetScriptFramework CrashLog \- GitHub Gist, [https://gist.github.com/Daimonicon/994fc364d61ece1ea4859a4eb64339d0](https://gist.github.com/Daimonicon/994fc364d61ece1ea4859a4eb64339d0)  
> 28. Skyrim AE BTPS crash logs \- GitHub Gist, [https://gist.github.com/ceejbot/0159781bc258a98278d768d3962d6b4b](https://gist.github.com/ceejbot/0159781bc258a98278d768d3962d6b4b)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAaCAYAAAAue6XIAAABgUlEQVR4Xu2WPy8FQRTFDxGJSiIkCj6FTiFEg/hTazS+gkgoFBKl+AQ6Eo2IArWWhEIrClGoKESh4l4zm2zOu7Mz78370+wvOcl7557ZOTvJ7ntATe+YFs2yWcEdGwn8isbZbIY3uIsciy78Z1UVsfkKG55BxNeafCK88BrhmfqHbAoHog/Eb3ZEdMtmFetwF5zkQQmd77GJcJEr0aJoB+FMgc772LQ4gQsP84CwTmhfdEoes4vGdYzOv9m0sEpYWDn9PkUek1L2HPEMFuBCKU9yqGyMlLJjiGfwBRda4gExgMay+mBEN0BaWSWa4QIhnuFyWyVvxnsxul7Wyq0ankVXy4Yy+stj+Uzbyj7Chfp5UELnr2x6ohugjWWV0Mmdwfn6IIWw1jEpZTcRz/wzBxe8Fw2JlkUv3pso5SzeRWtseopDYB2VQ54HJJbNYVT0w2YLaNFtNjuBbqTv4Rw6fqoFG8jb7An5N9sUN6h+o4SYR96NtswlGwnoX9Oamppe8gfPjnhX0Usy1wAAAABJRU5ErkJggg==>