#include "VendorPriceHook.h"

#include "BarterMenuSink.h"
#include "VendorMarkupCache.h"

namespace ChronicleBridge {

    namespace {

        // PostCreate's real signature is `void PostCreate()` -- an
        // implicit-`this` member function. On the MSVC x64 ABI a
        // non-virtual free function taking the object pointer as its first
        // (register) argument is call-compatible with a thiscall member
        // function taking no arguments -- the same "naked free function
        // standing in for a vtable slot" shape every other vfunc-swap hook
        // in the CommonLibSSE-NG ecosystem uses (report 28 F2/F3's own
        // DPF-derived reference does the same).
        using PostCreate_t = void (*)(RE::IMenu*);
        REL::Relocation<PostCreate_t> g_origPostCreate;

        // The replaced ActionScript "UpdateItemCardInfo" callback for ONE
        // specific BarterMenu::PostCreate call. A fresh instance per menu
        // open (not a single process-wide singleton) -- report 28 F3's own
        // DPF-derived reference does the same, since the saved "original"
        // callback and the captured multiplier are both specific to the
        // menu instance that was just constructed. The multiplier is
        // captured once, at menu-open time, from VendorMarkupCache's
        // current snapshot -- a grudge that cools mid-barter-session won't
        // be picked up until the menu is reopened. Acceptable for a first
        // cut, the same tunable-precision tradeoff chronicle/vendor_markup.
        // py's own placeholder ceiling already accepts.
        class UpdateItemCardInfoHook : public RE::GFxFunctionHandler {
        public:
            UpdateItemCardInfoHook(RE::GFxValue a_original, double a_multiplier) :
                _original(std::move(a_original)), _multiplier(a_multiplier) {}

            // report 28 F3's documented flow: read the "value" field off
            // the passed-in per-row update object, multiply it, write it
            // back, then forward to the real ActionScript callback exactly
            // as before -- this callback is never allowed to silently
            // swallow the call, since a barter menu's item list depends on
            // it running every time Scaleform asks for a row's price.
            void Call(Params& a_params) override {
                if (a_params.argCount > 0 && a_params.args != nullptr) {
                    RE::GFxValue& updateObj = a_params.args[0];
                    RE::GFxValue value(RE::GFxValue::ValueType::kNumber);
                    if (updateObj.IsObject() && updateObj.GetMember("value", &value) && value.IsNumber()) {
                        value.SetNumber(value.GetNumber() * _multiplier);
                        updateObj.SetMember("value", value);
                    }
                }

                _original.Invoke("call", a_params.retVal, a_params.argsWithThisRef, a_params.argCount + 1);
            }

        private:
            RE::GFxValue _original;
            double _multiplier;
        };

        void PostCreate(RE::IMenu* a_this) {
            // Always call the real original first -- report 28's own
            // finding is that PostCreate on BarterMenu is a documented
            // no-op today (IMenu.h: "// 02 - { return; }"), but calling
            // through unconditionally is the only correct way to hook a
            // vfunc that might do real work in some other build/DLC/future
            // patch. Everything below is additive, never a replacement for
            // whatever PostCreate itself does.
            g_origPostCreate(a_this);

            // This override is only ever installed on RE::VTABLE_BarterMenu
            // -- the ONLY objects that dispatch through it are BarterMenu
            // instances, so this static_cast is safe (not a downcast across
            // an unrelated hierarchy, and BarterMenu : public IMenu is
            // single, non-virtual inheritance, so the pointer value itself
            // is unchanged).
            auto* barterMenu = static_cast<RE::BarterMenu*>(a_this);

            // Same vendor-resolution chain BarterMenuSink.cpp's detection
            // path uses -- see VendorPriceHook.h's ORDERING CAVEAT for the
            // one open question about whether this resolves at THIS exact
            // moment in BarterMenu's lifecycle.
            auto* vendor = ResolveBarterVendorActor();
            if (!vendor) {
                return;
            }

            auto npcId = ResolveNpcIdForActor(vendor);
            if (!npcId) {
                // Not a named-cast NPC -- no Chronicle grudge/markup state
                // is possible for a generic merchant, same reasoning
                // BarterMenuHandler::ProcessEvent already uses.
                return;
            }

            auto multiplier = GetPlayerMarkupMultiplier(*npcId);
            if (!multiplier) {
                // Step 5 of this slice's own instructions / report 28's
                // Recommendation: no player-directed markup entry for this
                // vendor -- install NOTHING. Zero behavior change, and
                // simpler/safer than intercept-and-multiply-by-1.0.
                return;
            }

            auto& runtimeData = barterMenu->GetRuntimeData();

            RE::GFxValue oldFunc;
            if (!runtimeData.root.GetMember("UpdateItemCardInfo", &oldFunc)) {
                SKSE::log::warn(
                    "ChronicleBridge vendor-price: BarterMenu root has no 'UpdateItemCardInfo' member -- cannot "
                    "install price hook for vendor '{}'",
                    *npcId);
                return;
            }

            if (!barterMenu->uiMovie) {
                SKSE::log::warn(
                    "ChronicleBridge vendor-price: BarterMenu has no uiMovie yet -- cannot install price hook for "
                    "vendor '{}'",
                    *npcId);
                return;
            }

            // report 28 F3's documented shape: wrap a fresh
            // GFxFunctionHandler in a GFx-managed function object via
            // CreateFunction, then SetMember it back onto the menu's root
            // clip in place of the real callback. The local `handler`
            // GPtr going out of scope at the end of this function is safe
            // -- CreateFunction's own documented job is to construct a
            // native-function proxy that retains its own reference to the
            // handler, the same assumption report 28's read of the real
            // DPF source relies on (its own local `impl` GPtr is likewise
            // function-scoped).
            auto handler = RE::make_gptr<UpdateItemCardInfoHook>(oldFunc, *multiplier);
            RE::GFxValue newFunc;
            barterMenu->uiMovie->CreateFunction(&newFunc, handler.get());
            runtimeData.root.SetMember("UpdateItemCardInfo", newFunc);

            SKSE::log::info(
                "ChronicleBridge vendor-price: installed {:.2f}x player-directed markup on BarterMenu's "
                "UpdateItemCardInfo for vendor '{}' (UNVERIFIED against a live save -- compiled only, whether this "
                "drives the real transaction gold vs. only the displayed figure is not confirmed, see "
                "VendorPriceHook.h)",
                *multiplier, *npcId);
        }

    }  // namespace

    void InstallVendorPriceHook() {
        REL::Relocation<std::uintptr_t> vtbl{RE::VTABLE_BarterMenu[0]};
        g_origPostCreate = vtbl.write_vfunc(0x2, &PostCreate);
        SKSE::log::info(
            "ChronicleBridge: BarterMenu PostCreate vtable-slot swap installed (vendor price-markup write hook, "
            "docs/research/28-vendor-price-hook-address-library-spike.md)");
    }

}  // namespace ChronicleBridge
