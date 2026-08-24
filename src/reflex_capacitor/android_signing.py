"""Android release signing helpers for Capacitor Gradle builds."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SIGNING_BEGIN = "// reflex-capacitor signing begin"
SIGNING_END = "// reflex-capacitor signing end"

KEYSTORE_ENV = "REFLEX_CAPACITOR_KEYSTORE_PATH"
KEYSTORE_PASSWORD_ENV = "REFLEX_CAPACITOR_KEYSTORE_PASSWORD"
KEY_ALIAS_ENV = "REFLEX_CAPACITOR_KEY_ALIAS"
KEY_PASSWORD_ENV = "REFLEX_CAPACITOR_KEY_PASSWORD"


@dataclass(frozen=True, kw_only=True)
class AndroidSigningConfig:
    """Release keystore settings."""

    keystore_path: Path
    keystore_password: str
    key_alias: str
    key_password: str

    @classmethod
    def from_env(cls) -> AndroidSigningConfig | None:
        """Load signing config from standard environment variables."""
        path = os.environ.get(KEYSTORE_ENV, "").strip()
        if not path:
            return None
        store_password = os.environ.get(KEYSTORE_PASSWORD_ENV, "").strip()
        key_alias = os.environ.get(KEY_ALIAS_ENV, "").strip()
        key_password = os.environ.get(KEY_PASSWORD_ENV, "").strip()
        if not store_password or not key_alias or not key_password:
            msg = (
                "reflex-capacitor: set all signing env vars when using "
                f"{KEYSTORE_ENV}: {KEYSTORE_PASSWORD_ENV}, {KEY_ALIAS_ENV}, {KEY_PASSWORD_ENV}"
            )
            raise ValueError(msg)
        keystore_path = Path(path).expanduser().resolve()
        if not keystore_path.is_file():
            msg = f"reflex-capacitor: keystore not found at {keystore_path}"
            raise FileNotFoundError(msg)
        return cls(
            keystore_path=keystore_path,
            keystore_password=store_password,
            key_alias=key_alias,
            key_password=key_password,
        )


def write_keystore_properties(android_root: Path, signing: AndroidSigningConfig) -> Path:
    """Write ``android/keystore.properties`` (gitignored by Capacitor template)."""
    store_path = signing.keystore_path
    try:
        rel = store_path.relative_to(android_root)
        store_file = str(rel).replace("\\", "/")
    except ValueError:
        store_file = str(store_path).replace("\\", "/")

    props_path = android_root / "keystore.properties"
    props_path.write_text(
        "\n".join(
            [
                f"storeFile={store_file}",
                f"storePassword={signing.keystore_password}",
                f"keyAlias={signing.key_alias}",
                f"keyPassword={signing.key_password}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return props_path


def _signing_snippet() -> str:
    return f"""
{SIGNING_BEGIN}
def rcKeystorePropertiesFile = rootProject.file("keystore.properties")
def rcKeystoreProperties = new Properties()
if (rcKeystorePropertiesFile.exists()) {{
    rcKeystoreProperties.load(new FileInputStream(rcKeystorePropertiesFile))
}}
{SIGNING_END}
""".strip()


def _signing_configs_block() -> str:
    return """
    signingConfigs {
        release {
            if (rcKeystorePropertiesFile.exists()) {
                keyAlias rcKeystoreProperties['keyAlias']
                keyPassword rcKeystoreProperties['keyPassword']
                storeFile file(rcKeystoreProperties['storeFile'])
                storePassword rcKeystoreProperties['storePassword']
            }
        }
    }
""".strip()


def apply_release_signing(android_root: Path, signing: AndroidSigningConfig) -> None:
    """Configure Gradle release signing via keystore.properties + build.gradle patch."""
    write_keystore_properties(android_root, signing)
    gradle_path = android_root / "app" / "build.gradle"
    if not gradle_path.is_file():
        msg = f"reflex-capacitor: missing {gradle_path} — run `reflex-capacitor init` first"
        raise FileNotFoundError(msg)
    patch_app_build_gradle(gradle_path)


def patch_app_build_gradle(gradle_path: Path) -> None:
    """Idempotently patch ``android/app/build.gradle`` for release signing."""
    text = gradle_path.read_text(encoding="utf-8")
    if SIGNING_BEGIN in text and "signingConfig signingConfigs.release" in text:
        return

    snippet = _signing_snippet()
    if SIGNING_BEGIN not in text:
        marker = "android {"
        idx = text.find(marker)
        if idx == -1:
            msg = f"reflex-capacitor: could not find `android {{` in {gradle_path}"
            raise ValueError(msg)
        insert_at = idx + len(marker)
        text = text[:insert_at] + "\n" + snippet + text[insert_at:]

    if "signingConfigs {" not in text:
        marker = "android {"
        idx = text.find(marker)
        if idx == -1:
            msg = f"reflex-capacitor: could not find `android {{` in {gradle_path}"
            raise ValueError(msg)
        insert_at = idx + len(marker)
        if SIGNING_BEGIN in text:
            end = text.find(SIGNING_END, insert_at)
            if end != -1:
                insert_at = end + len(SIGNING_END)
        text = text[:insert_at] + "\n" + _signing_configs_block() + text[insert_at:]

    if "signingConfig signingConfigs.release" not in text:
        release_marker = "release {"
        idx = text.find(release_marker)
        if idx == -1:
            msg = f"reflex-capacitor: could not find release buildType in {gradle_path}"
            raise ValueError(msg)
        insert_at = idx + len(release_marker)
        text = (
            text[:insert_at]
            + "\n            signingConfig signingConfigs.release"
            + text[insert_at:]
        )

    gradle_path.write_text(text, encoding="utf-8")


def release_output_paths(android_root: Path, *, aab: bool) -> list[Path]:
    """Return expected Gradle release artifact paths."""
    outputs = android_root / "app" / "build" / "outputs"
    if aab:
        return sorted((outputs / "bundle" / "release").glob("*.aab"))
    return sorted((outputs / "apk" / "release").glob("*.apk"))
