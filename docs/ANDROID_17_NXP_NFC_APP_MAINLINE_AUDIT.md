# PixelExperience-Reborn AOSP 17 — row 168, historical NXP NFC application

**Reviewed:** 2026-11-07. **Future device target:** POCO F5 Pro / Redmi K60 (`mondrian`, Snapdragon SM8475).
**Status:** source-only review, independent platform first. Neither Java/Soong build nor physical NFC operation has been tested.

## Decision — do not install the old NXP application

**Retain official AOSP17 `packages/modules/Nfc` (Mainline) and its single selected NFC package/APEX owner. Do NOT add archived `vendor/nxp/opensource/commonsys/packages/apps/Nfc` to the active manifest or install `NQNfcNci`.** This is a substantive choice based on module and API ownership, not a claim that old NXP work has no value. The archived NFC app is a different, 2022-era Android NFC service build; it is not a standalone patch for a modern NXP HAL.

The current PE-Reborn `default.xml` is **source-only, not a bootable product**. Any NFC services, features, controller firmware or device configuration require an independent PE-Reborn Android17 device/product design and build. LF52406 LineageOS device trees are **optional last-resort hardware reference only**, never an imported baseline or an automatic source of product settings.

## Reproducible source identity

| Source | Pinned identity | Role |
| --- | --- | --- |
| Legacy `vendor_nxp_opensource_commonsys_packages_apps_Nfc` `seventeen` | commit `ad34196f30d240dcda264d8fd4c109f15177dc96`, tree `ce7cc0cbf93389b4c0a7b1d5640e3f129c1f9e54`; last commit 2022-12-31 | Archived `NQNfcNci`, NXP JNI and vendor extensions, NXP DTA tooling, NFC beam/P2P-era classes |
| AOSP17 NFC release | `android-17.0.0_r1`, commit `940212c440f57032a19cf0f90c7faa8eca48d546`, tree `da01c841e3238648d0ae33c3392c05f1552e63d5` | Active `platform/packages/modules/Nfc`: NFC Mainline, `NfcNci`, `NfcNciApex`, `libnfc_nci_jni`, NFC charging, privileged service, security/test owners |
| Subsequent Android17 NFC security candidate | `android-security-17.0.0_r3`, commit `6f3a074cf6c87a2dcc3970c03462a6970b06f9cd`, tree `ee6a57f5ccc30d113588f6cc5bffff94932bffb5`, tag dated 2026-11-02 | Verified **newer review candidate**, NOT automatically imported into the whole Android17 manifest. A platform-wide security-rebase review is a separate step. |

Official upstream:
- https://android.googlesource.com/platform/packages/modules/Nfc/+/refs/tags/android-17.0.0_r1
- https://android.googlesource.com/platform/packages/modules/Nfc/+/refs/tags/android-security-17.0.0_r3

## Real dependencies of the archived implementation

1. Root `Android.bp`: `android_app { name: "NQNfcNci", system_ext_specific: true, platform_apis: true, certificate: "platform" }`; JNI `libsn100nfc_nci_jni`; `libs/uses_libs = com.nxp.nfc.nq`; static dependency on `vendor.nxp.hardware.nfc-V2.0-java`.
2. `nfc_system_product.mk` adds the archived app + `libnqnfc-nci`, `libnqnfc_nci_jni`, `libsn100nfc_nci_jni`, `libsn100nfc-nci` and `com.nxp.nfc.nq` if `TARGET_FWK_SUPPORTS_FULL_VALUEADDS`. This is an **old QSSI/CAF product dependency graph**, not AOSP17 device logic.
3. `nci/SN100x/jni/Android.bp` builds `libsn100nfc_nci_jni` and imports old `vendor/nxp/opensource/commonsys/external/libnfc-nci/SN100x` headers and `vendor.nxp.hardware.nfc@2.0`, `libchrome`, `libandroidicu`. This crosses the modern NFC APEX/native/Soong boundary and would couple previously audited rows 166/167 again.
4. `AndroidManifest.xml` package is `com.android.nfc` with legacy `android.uid.nfc`, requests many privileged/cross-user permissions and declares NXP-specific protected broadcasts. Adding its APK beside the official `com.android.nfc` creates package/privilege conflicts. The presence of a declared permission does **not** prove Android17 permission compatibility.
5. `NfcService.java` includes old `INxpNfcAdapter`, `INxpWlcAdapter`, direct `ISecureElementService` and NFC-specific service messages (T4T NFCEE, secure reader/mPOS, vendor hooks), plus deprecated beam/SNEP/LLCP/Wi-Fi handover code.
6. `src/com/android/nfc/WlcServiceProxy.java` uses reflection to load `com.android.nfc.wlc.WlcClient`; `NxpWlcAdapterService.java` exposes NXP WLC Binder APIs and checks `NFC` permission and NFC enabled state. This old integration is not proof of a real NFC charging controller.
7. `nfc-dta/` includes NXP Digital Test Application tooling. This is potentially useful for **laboratory** validation if vendor-compatible, but **must not** be installed into a consumer ROM without an independent version, licensing and device test audit.

## Feature-by-feature AOSP17 comparison

| Legacy NXP feature | Android17 source owner / current equivalent | Decision |
| --- | --- | --- |
| NFC system application and NFC service | `packages/modules/Nfc/NfcNci`: `NfcNci` and `NfcNciApex`; `apex/Android.bp` `com.android.nfcservices`; official `com.android.nfc` | **Keep AOSP17 only**. Installing `NQNfcNci` would add a second app/service implementation. |
| NFC JNI and NCI native stack | `packages/modules/Nfc/NfcNci/nci` and `libnfc-nci` | **Keep AOSP17**. Do not revive `libsn100nfc_nci_jni` or the old `libandroidicu` visibility assumptions. |
| NFC Wireless Charging | `NfcNci/src/com/android/nfc/wlc/NfcCharging.java`, Mainline `NfcService.java` with `mNfcCharging` and WLC state | **Already available as AOSP17 implementation**. Whether mondrian supports NFC WLC is **unknown**; no hardware feature claim or UI. |
| OEM callbacks and vendor commands | AOSP17 `NfcOemExtension`, vendor NCI notification and response hooks | **Use modern owner**. Require a concrete use case and authorized consumer before any extension. |
| NFC routing, payment and off-host SE | AOSP17 `CardEmulationManager`, `RoutingOptionManager`, `android.se.omapi` and separate official Secure Element service | **Preserve modern permission/SE boundaries**; never copy old NXP AID/UICC or APDU access assumptions. |
| T4T NFCEE | Modern `NfcService` `IT4tNdefNfcee`, T4T NFCEE data and routing | **Existing upstream capability**, subject to HAL/vendor support and permission gates. |
| Secure Reader/mPOS/MIFARE vendor diagnostics | Old NXP classes and native extensions; no AOSP17 equivalence automatically assumed | **Candidate only** if exact capability/device app/service/HAL contract demonstrated, no speculative port. |
| NXP DTA RF/NFC test suite | NXP archived `nfc-dta` vs AOSP17 `tests/`, `TEST_MAPPING`, host/device tests | **Lab-only candidate**; first try official tests, verify controller support, licences and production separation. |
| Android Beam/P2P-era paths | Old `beam/`, `snep/`, `llcp/` | **Do not resurrect** unused historical APIs as ROM platform features. |
| Newer AOSP17 security release | Official `android-security-17.0.0_r3` NFC tree | **Follow-up security review**. Do not update one APEX component to a mismatched platform revision without build/API/compatibility/security validation. |

## Required engineering gates for an actual independent NFC bring-up

- Establish exactly one package `com.android.nfc`, one application/APEX owner, one `INfc/default` HAL service, and a compatible configuration/firmware set. AOSP17 `NfcNci` and `NfcNciApex` are **alternative build variants**, not two apps to ship together.
- Check AIDL/HIDL HAL/SE routing, OMAPI `ISecureElementService`, JNI accessibility and ELF/Soong linkage in a clean independent PE-Reborn device build. Do not substitute stubs for real NFC firmware.
- Validate exported components, app UID, privileged allowlists, NFC and `WRITE_SECURE_SETTINGS`, binder caller identity, per-user state, SE/APDU permissions, APEX signing/update path, SELinux enforcing, neverallow and VINTF.
- Run NFC Mainline Java/JNI unit tests, host/fuzz tests, Soong/APEX compilation, `checkvintf`, CTS/VTS and hardware NFC tag read/write, HCE, eSE/UICC and RF performance/power tests. Only test WLC if real NFC WLC support is verified.
- Compare `android-security-17.0.0_r3` to release baseline and review whether **the entire platform's** Android17 source graph should adopt a newer security release; preserve exact SHA and compatible APIs.

## Actions in this review

An isolated audit branch adds this document and a pinned cross-source static test. The active AOSP17 working manifest gains a negative guard against this archived source checkout and repo name; a separate negative test tries to replace the official NFC owner. No source override, NFC app, firmware, HAL, SE route or LineageOS-derived device config is activated.

**Scope limitation:** A green source/manifest CI does not mean NFC is compiled, released, certified or functional on mondrian.
