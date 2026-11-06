#!/usr/bin/env python3
"""AOSP17 row 168: pinned, source-only NXP NFC app vs Mainline ownership gate.

This is not a Soong/Java/APEX build, vendor HAL validation or physical NFC test.
"""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

LEGACY = "ad34196f30d240dcda264d8fd4c109f15177dc96"
LEGACY_TREE = "ce7cc0cbf93389b4c0a7b1d5640e3f129c1f9e54"
AOSP = "940212c440f57032a19cf0f90c7faa8eca48d546"
AOSP_TREE = "da01c841e3238648d0ae33c3392c05f1552e63d5"
SEC_R3 = "6f3a074cf6c87a2dcc3970c03462a6970b06f9cd"
SEC_R3_TREE = "ee6a57f5ccc30d113588f6cc5bffff94932bffb5"
LEGACY_PATH = "vendor/nxp/opensource/commonsys/packages/apps/Nfc"
LEGACY_NAME = "vendor_nxp_opensource_commonsys_packages_apps_Nfc"


def require(ok, msg):
    if not ok:
        raise RuntimeError(msg)


def git(root, *args):
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True).strip()


def show(root, ref, path):
    return git(root, "show", f"{ref}:{path}")


def pinned(root, ref, expected, tree, label):
    actual = git(root, "rev-parse", f"{ref}^{{commit}}")
    require(actual == expected, f"{label}: unexpected commit {actual}")
    actual_tree = git(root, "rev-parse", f"{actual}^{{tree}}")
    require(actual_tree == tree, f"{label}: unexpected tree {actual_tree}")
    return actual


def old_nxp_app(root):
    ref = pinned(root, "refs/remotes/origin/seventeen",
                 LEGACY, LEGACY_TREE, "historical NXP app")
    bp = show(root, ref, "Android.bp")
    product = show(root, ref, "nfc_system_product.mk")
    jni = show(root, ref, "nci/SN100x/jni/Android.bp")
    manifest = ET.fromstring(show(root, ref, "AndroidManifest.xml"))
    nfc_service = show(root, ref, "src/com/android/nfc/NfcService.java")
    wlc_proxy = show(root, ref, "src/com/android/nfc/WlcServiceProxy.java")
    wlc_service = show(root, ref, "src/com/android/nfc/NxpWlcAdapterService.java")
    files = git(root, "ls-tree", "-r", "--name-only", ref).splitlines()

    require('name: "NQNfcNci"' in bp
            and "system_ext_specific: true" in bp
            and 'certificate: "platform"' in bp
            and '"libsn100nfc_nci_jni"' in bp
            and 'uses_libs: ["com.nxp.nfc.nq"]' in bp
            and '"vendor.nxp.hardware.nfc-V2.0-java"' in bp,
            "archived NQNfcNci app/permission/Soong dependencies changed")
    for item in ("TARGET_FWK_SUPPORTS_FULL_VALUEADDS", "NQNfcNci",
                 "libsn100nfc-nci", "libsn100nfc_nci_jni",
                 "com.nxp.nfc.nq", "libnqnfc-nci"):
        require(item in product, f"archived QSSI product dependency changed: {item}")
    for item in ("libandroidicu", "libchrome",
                 "vendor.nxp.hardware.nfc@2.0",
                 "vendor/nxp/opensource/commonsys/external/libnfc-nci"):
        require(item in jni, f"archived JNI dependency changed: {item}")
    android = "{http://schemas.android.com/apk/res/android}"
    require(manifest.attrib.get("package") == "com.android.nfc",
            "archived NFC package identity changed")
    require(manifest.get(android + "sharedUserId") == "android.uid.nfc",
            "archived NFC privileged UID changed")
    permissions = {p.get(android + "name")
                   for p in manifest.findall("uses-permission")}
    require({"android.permission.NFC",
             "android.permission.WRITE_SECURE_SETTINGS",
             "android.permission.INTERACT_ACROSS_USERS_FULL"} <= permissions,
            "archived NFC permission boundary changed")
    require(any(b.get(android + "name", "").startswith("com.nxp.nfc_extras.")
                for b in manifest.findall("protected-broadcast")),
            "archived NXP broadcast API changed")
    require("com.nxp.nfc.INxpNfcAdapter" in nfc_service
            and "com.nxp.nfc.INxpWlcAdapter" in nfc_service
            and "ISecureElementService" in nfc_service,
            "old NXP framework and SE bindings changed")
    require('Class.forName("com.android.nfc.wlc.WlcClient")' in wlc_proxy,
            "archived NXP NFC charging reflection contract changed")
    require("NfcPermissions.enforceUserPermissions(mContext)" in wlc_service,
            "archived WLC Binder permission contract changed")
    require(any(x.startswith("nfc-dta/") for x in files),
            "archived vendor DTA tool source inventory changed")
    require("src/com/android/nfc/beam/BeamSendService.java" in files,
            "archived beam/P2P code inventory changed")
    print("PASS: 2022 NQNfcNci owns com.android.nfc and old QSSI/HIDL Java/JNI")
    print("PASS: old NXP NFC WLC, SE, vendor DTA and permissions reviewed")


def modern_mainline(root):
    ref = pinned(root, "refs/tags/android-17.0.0_r1",
                 AOSP, AOSP_TREE, "official AOSP17 NFC")
    bp = show(root, ref, "NfcNci/Android.bp")
    apex = show(root, ref, "apex/Android.bp")
    nfc = show(root, ref, "NfcNci/src/com/android/nfc/NfcService.java")
    wlc = show(root, ref, "NfcNci/src/com/android/nfc/wlc/NfcCharging.java")
    permissions = show(root, ref, "NfcNci/src/com/android/nfc/NfcPermissions.java")
    manifest = ET.fromstring(show(root, ref, "NfcNci/AndroidManifest.xml"))

    require('name: "NfcNci"' in bp and 'name: "NfcNciApex"' in bp
            and 'jni_libs: ["libnfc_nci_jni"]' in bp
            and '"com.android.nfcservices"' in bp,
            "modern NFC app/variant/JNI ownership changed")
    require('name: "com.android.nfcservices"' in apex
            and 'apps: ["NfcNciApex"]' in apex,
            "Mainline NFC APEX packaging changed")
    require(manifest.attrib.get("package") == "com.android.nfc",
            "official Mainline NFC package identity changed")
    for item in ("NfcCharging", "NfcOemExtension", "IT4tNdefNfcee",
                 "RoutingOptionManager", "ISecureElementService",
                 "mNfcCharging"):
        require(item in nfc, f"modern NFC service feature changed: {item}")
    require("class NfcCharging" in wlc, "modern NFC wireless charging missing")
    require("enforceAdminPermissions" in permissions
            and "enforceUserPermissions" in permissions,
            "official NFC service permission utilities changed")
    require("getNfcAdapterVendorInterface(\"nxp\")" not in nfc,
            "unexpected legacy NXP Binder adapter integrated into Mainline")
    print("PASS: AOSP17 NFC Mainline provides one app owner + APEX alternate variant")
    print("PASS: AOSP17 NFC has native WLC, OEM, T4T, SE and routing owner")


def security_release_candidate(root):
    pinned(root, "refs/tags/android-security-17.0.0_r3",
           SEC_R3, SEC_R3_TREE, "AOSP17 NFC November security candidate")
    changed = git(root, "diff", "--name-only", AOSP, SEC_R3).splitlines()
    require(len(changed) > 0,
            "security release NFC tree matches older baseline unexpectedly")
    # Informational delta only. This must NOT modify the active PE manifest.
    print("PASS: Android17 security r3 is an independently pinned newer NFC candidate")
    print(f"INFO: NFC source paths differing from android-17.0.0_r1: {len(changed)}")
    for path in changed[:12]:
        print(f"INFO: security-diff {path}")
    if len(changed) > 12:
        print(f"INFO: ... and {len(changed) - 12} additional changed paths")
    print("OPEN: full Android17 release/security rebase and Soong compatibility")


def manifest_boundary(root):
    root = Path(root)
    entry = ET.parse(root / "default.xml").getroot()
    require(len(entry) == 1 and entry[0].get("name") ==
            "aosp17_pe_p2_kernel_configs.xml",
            "active AOSP17 entrypoint has changed")
    bootstrap = ET.parse(root / "aosp17_pe_bootstrap.xml").getroot()
    owners = {p.get("path"): p.get("name") for p in bootstrap.findall("project")}
    require(owners.get("packages/modules/Nfc") == "platform/packages/modules/Nfc",
            "official Mainline NFC source owner changed")
    require(owners.get("hardware/nxp/nfc") == "platform/hardware/nxp/nfc",
            "official NXP HAL source owner changed")
    require(owners.get("system/secure_element") ==
            "platform/system/secure_element",
            "AOSP17 secure element source owner changed")
    require(LEGACY_PATH not in owners and LEGACY_NAME not in owners.values(),
            "unreviewed NXP NFC APK source activated")

    # Additional source-only NFC security stage may be evaluated, but
    # it must not replace the reviewed default AOSP17 r1 source graph.
    candidate = ET.parse(
        root / "aosp17_pe_p2_nfc_security_candidate.xml").getroot()
    candidate_nfc = [p for p in candidate.findall("project")
                     if p.get("path") == "packages/modules/Nfc"]
    require(len(candidate_nfc) == 1
            and candidate_nfc[0].get("name") == "platform/packages/modules/Nfc"
            and candidate_nfc[0].get("revision") == SEC_R3,
            "experimental NFC security candidate absent or not pinned")
    validator = (root / "tools/validate_aosp17_base_profiles.py").read_text()
    tests = (root / "tools/test_aosp17_manifest_entrypoint.py").read_text()
    require(f'if "{LEGACY_PATH}" in projects:' in validator,
            "row 168 archived NFC app path guard not present")
    require(f'"{LEGACY_NAME}"' in validator,
            "row 168 archived NFC repo-name guard not present")
    for name in ("test_legacy_nxp_nfc_apk_cannot_enter_android17",
                 "test_legacy_nxp_nfc_apk_cannot_replace_mainline"):
        require(f"def {name}(" in tests,
                f"row 168 adversarial test missing: {name}")
    subprocess.run(
        [sys.executable, str(root / "tools/validate_aosp17_base_profiles.py")],
        cwd=root, check=True)
    print("PASS: 25 profiles retain AOSP17 NFC/SE owners with row 168 deny guards")


def main():
    require(len(sys.argv) == 4,
            "Usage: check_nxp_nfc_app_mainline.py LEGACY_APP AOSP17_NFC MANIFEST")
    old, modern, manifest = [Path(s).resolve() for s in sys.argv[1:]]
    require(all(x.is_dir() for x in (old, modern, manifest)),
            "missing one or more source checkouts")
    old_nxp_app(old)
    modern_mainline(modern)
    security_release_candidate(modern)
    manifest_boundary(manifest)
    print("PASS: row 168 isolated AOSP17 NFC application/source boundary")
    print("NOT TESTED: NFC/SE Soong/APEX build, CTS/VTS, vendor ABI or mondrian")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, ET.ParseError,
            subprocess.CalledProcessError) as e:
        print("FAIL:", e, file=sys.stderr)
        sys.exit(1)
