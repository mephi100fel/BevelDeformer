import json
import os
import tempfile
import urllib.error
import urllib.request

import bpy
from bpy.types import Operator


GITHUB_API_BASE = "https://api.github.com"
DEFAULT_REPO = "mephi100fel/BevelDeformer"


def _parse_tag_version(tag: str) -> tuple[int, int, int] | None:
    if not tag:
        return None

    value = tag.strip()
    if value.startswith("v"):
        value = value[1:]

    parts = value.split(".")
    if len(parts) < 3:
        return None

    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _get_current_version_tuple() -> tuple[int, int, int]:
    try:
        import importlib

        pkg = importlib.import_module(__package__)
        version = pkg.bl_info.get("version", (0, 0, 0))
        return int(version[0]), int(version[1]), int(version[2])
    except Exception:
        return 0, 0, 0


def _make_request(url: str, *, token: str | None = None) -> urllib.request.Request:
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "BevelDeformer-Updater")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")

    if token:
        # Works for fine-grained and classic PATs
        req.add_header("Authorization", f"Bearer {token}")

    return req


def _http_get_json(url: str, *, token: str | None = None, timeout: float = 15.0) -> dict:
    req = _make_request(url, token=token)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8")
    return json.loads(data)


def _http_download(url: str, dest_path: str, *, token: str | None = None, timeout: float = 30.0) -> None:
    req = _make_request(url, token=token)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        chunk_size = 1024 * 256
        with open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)


def get_latest_release(repo: str, *, token: str | None) -> dict | None:
    url = f"{GITHUB_API_BASE}/repos/{repo}/releases/latest"

    try:
        return _http_get_json(url, token=token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def choose_zip_asset(release: dict) -> dict | None:
    assets = release.get("assets") or []
    zip_assets = [a for a in assets if str(a.get("name", "")).lower().endswith(".zip")]
    if not zip_assets:
        return None

    preferred = [a for a in zip_assets if "bevel_deformer" in str(a.get("name", "")).lower()]
    return preferred[0] if preferred else zip_assets[0]


def check_update(repo: str, *, token: str | None) -> tuple[bool, str, str | None, str | None]:
    current = _get_current_version_tuple()

    if not repo:
        return False, "Repo is not set.", None, None

    release = get_latest_release(repo, token=token)
    if release is None:
        return False, "No releases found.", None, None

    tag = str(release.get("tag_name", ""))
    latest = _parse_tag_version(tag)
    if latest is None:
        return False, f"Latest release tag is not a semver tag: {tag}", None, None

    asset = choose_zip_asset(release)
    if asset is None:
        return False, f"No .zip asset found in release {tag}", tag, None

    url = str(asset.get("browser_download_url", ""))
    if not url:
        return False, f"Release asset has no download URL in {tag}", tag, None

    if latest <= current:
        return False, f"Up to date. Current {current}, latest {latest} ({tag})", tag, url

    return True, f"Update available: {tag}", tag, url


def install_update_from_url(*, url: str, token: str | None) -> str:
    if not url:
        raise ValueError("Missing download URL")

    temp_dir = tempfile.gettempdir()
    filename = os.path.basename(url.split("?")[0]) or "bevel_deformer_update.zip"
    dest_path = os.path.join(temp_dir, filename)

    _http_download(url, dest_path, token=token)

    bpy.ops.preferences.addon_install(filepath=dest_path, overwrite=True)
    bpy.ops.preferences.addon_enable(module=__package__)

    return dest_path


class BD_OT_check_updates(Operator):
    bl_idname = "bd.check_updates"
    bl_label = "Check Updates"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        repo = str(getattr(prefs, "github_repo", DEFAULT_REPO)).strip()
        token = str(getattr(prefs, "github_token", "")).strip() or None

        try:
            available, message, _, _ = check_update(repo, token=token)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                self.report({'ERROR'}, "GitHub access denied (401/403). If the repo is private, provide a token.")
                return {'CANCELLED'}
            self.report({'ERROR'}, f"GitHub error: HTTP {e.code}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Update check failed: {e}")
            return {'CANCELLED'}

        level = {'INFO'} if available else {'INFO'}
        self.report(level, message)
        return {'FINISHED'}


class BD_OT_install_update(Operator):
    bl_idname = "bd.install_update"
    bl_label = "Install Update"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        repo = str(getattr(prefs, "github_repo", DEFAULT_REPO)).strip()
        token = str(getattr(prefs, "github_token", "")).strip() or None

        try:
            available, message, tag, url = check_update(repo, token=token)
            if not available:
                self.report({'INFO'}, message)
                return {'CANCELLED'}

            path = install_update_from_url(url=url, token=token)
            self.report(
                {'INFO'},
                f"Installed {tag} from {os.path.basename(path)}. Please restart Blender to fully apply the update.",
            )
            return {'FINISHED'}

        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                self.report({'ERROR'}, "GitHub access denied (401/403). If the repo is private, provide a token.")
                return {'CANCELLED'}
            self.report({'ERROR'}, f"GitHub error: HTTP {e.code}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Update install failed: {e}")
            return {'CANCELLED'}


_classes = (
    BD_OT_check_updates,
    BD_OT_install_update,
)


def register() -> None:
    for cls in _classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
