#!/usr/bin/env python3
"""Render public docs from real QML components and synthetic state only.

Requires installed Omarchy/Quickshell and Pillow. All windows use Qt offscreen;
the fixture has no desktop environment, native controller or personal pixels.
"""
import json
import hashlib
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
APPEARANCE = {"variant": "error404", "color": "#ffffff", "grain": 50,
              "speed": 100, "darkness": 35, "eye": False, "eye_size": 80, "icon": "none", "icon_opacity": 75}
NATIVE_POSTER_SHA256 = "6729773b98172779cf5aad9a8f73bbaa557c8add9e8ccd78255fbab5374e3a82"


def marketplace_cover():
    """The main cover is an explicit explanatory illustration, rendered separately."""
    subprocess.run(["/usr/bin/python3", str(ASSETS / "render-cover.py")], check=True)
    import shutil
    shutil.copyfile(ASSETS / "social-preview.png", ROOT / "preview.png")


def write_provenance():
    names = ["preview.png", "assets/hiding-panel.png", "assets/appearance-panel.png",
             "assets/social-preview.png", "assets/spoiler-preview.gif", "assets/native-demo.png", "assets/native-styles.gif"]
    names += [str(path.relative_to(ROOT)) for path in sorted((ASSETS / "presets").glob("*"))]
    native = json.loads((ASSETS / "native-capture-provenance.json").read_text())
    data = {
        "version": 1,
        "ui": {"source": "real repository QML components rendered with Qt offscreen",
               "locale": "English (C.UTF-8)", "controller": "status-only synthetic fixture",
               "theme": "explicit synthetic palette in temporary HOME",
               "personal_desktop_capture": False, "native_compositor_session": False,
               "preset_swatches": "actual synthetic native captures; assets/presets/provenance.json"},
        "native_sample": {"source": "Hyprveil native capture of synthetic GTK notes in a marked isolated compositor",
                          "native_sha256": native["native_sha256"], "lab_stopped": True,
                          "upstream_repository": "https://github.com/OBJLAKO/hyprveil",
                          "upstream_asset": "assets/demo/poster.png",
                          "sha256": NATIVE_POSTER_SHA256},
        "cover": {"kind": "explanatory illustration", "desktop_capture": False, "provenance": "assets/cover-provenance.json"},
        "composition": "QML screenshots are synthetic; native demo is an actual GPU capture; main cover is a labeled illustration",
        "outputs": {name: {"sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                           "bytes": (ROOT / name).stat().st_size} for name in names},
    }
    previous = json.loads((ASSETS / "provenance.json").read_text())
    if "native_styles" in previous: data["native_styles"] = previous["native_styles"]
    (ASSETS / "provenance.json").write_text(json.dumps(data, indent=2) + "\n")

with tempfile.TemporaryDirectory(prefix="hyprveil-public-preview-") as temporary:
    fixture = Path(temporary)
    runtime = fixture / "runtime"
    runtime.mkdir(mode=0o700)
    home = fixture / "home"
    commands = home / ".local/bin"
    commands.mkdir(parents=True)
    # Seed Omarchy's real theme loader in the isolated HOME. No live theme or
    # personal configuration is read; every component receives these tokens.
    theme = home / ".local/state/omarchy/current/theme"
    theme.mkdir(parents=True)
    (theme / "colors.toml").write_text('''
background = "#101315"
foreground = "#dce4e8"
accent = "#9eb7c6"
muted = "#81929c"
red = "#bd8585"
''')
    (theme / "shell.toml").write_text('''
[popups]
background = "#101315"
background-alpha = 1.0
text = "#dce4e8"
border = "#344149"
[controls]
normal-color = "foreground"
normal-fill-alpha = 0.025
normal-border = "#52616b"
normal-border-alpha = 0.45
hover-cursor-color = "accent"
hover-cursor-fill-alpha = 0.10
focus-color = "accent"
focus-fill-alpha = 0.10
selected-color = "accent"
selected-fill-alpha = 0.16
selected-border-width = 0
[font]
base-size = 12
''')
    (fixture / "Commons").symlink_to("/usr/share/omarchy/shell/Commons")
    ui = fixture / "Ui"
    ui.mkdir()
    for source in Path("/usr/share/omarchy/shell/Ui").iterdir():
        if source.name != "KeyboardPanel.qml":
            (ui / source.name).symlink_to(source)
    (ui / "KeyboardPanel.qml").write_text('''
import QtQuick
Item {
    property Item anchorItem: null
    property QtObject bar: null
    property var owner: null
    property bool open: false
    property Item focusTarget: null
    property int contentWidth: 470
    property int contentHeight: 800
    width: contentWidth; height: contentHeight; visible: open
    function fittedContentWidth(value) { return value }
    function fittedContentHeight(value) { return value }
}
''')
    # A local import alias only; the public plugin's runtime lives at repo root.
    (fixture / "plugin").symlink_to(ROOT)
    controller = commands / "hyprveil"
    status = {"enabled": True, "loaded": True, "desired_mode": "spoiler", "appearance": APPEARANCE,
              "status": {"mode": "spoiler", "session": "live", "local_dump": "disabled-in-live",
                         "spoiler_status": "ready", "appearance": APPEARANCE,
                         "config_api": 1, "image_path": ""}}
    controller.write_text("#!/usr/bin/python3\nimport json,sys\nassert sys.argv[1:] == ['status']\nprint(" + repr(json.dumps(status)) + ")\n")
    controller.chmod(0o700)
    frames = fixture / "frames"
    frames.mkdir()
    qml = '''
import QtQuick
import Quickshell
import qs.Commons
import "./plugin" as Plugin
ShellRoot {
    id: root
    property int frame: 0
    property bool capturing: false
    property bool panelsSaved: false
    property int readyTicks: 0
    QtObject {
        id: syntheticPrivacy
        property bool privacyBusy: false
        property bool privacyDispatching: false
        property var focusPrivacy: ({state:"hidden",address:"0x123",stable_id:"402653184",native_private:true,inherited:false})
        function togglePrivacy() {}
    }
    Window {
        id: hidingWindow
        width: 510; height: 840; visible: true; color: "#101315"
        Rectangle { anchors.fill:parent; color:"#101315" }
        Plugin.Panel { id: hiding; x:20; y:20; manageIpc:false; hostWidget:syntheticPrivacy
            controllerCommand: [Quickshell.env("HOME") + "/.local/bin/hyprveil"] }
    }
    Window {
        id: appearanceWindow
        width: 510; height: 840; visible: true; color: "#101315"
        Rectangle { anchors.fill:parent; color:"#101315" }
        Plugin.Panel { id: appearance; x:20; y:20; manageIpc:false; hostWidget:syntheticPrivacy
            controllerCommand: [Quickshell.env("HOME") + "/.local/bin/hyprveil"] }
    }
    Window {
        id: texturesWindow
        width:960; height:350; visible:true; color:"#10171b"
        Rectangle { anchors.fill:parent; color:"#10171b" }
        Text { x:30; y:20; text:"Spoiler appearance"; color:"#d6e0e0"; font.family:"Adwaita Sans"; font.pixelSize:25 }
        Text { x:31; y:67; text:"PRISM"; color:"#91a5af"; font.family:"Adwaita Sans"; font.pixelSize:13; font.letterSpacing:2 }
        Text { x:497; y:67; text:"SIGNAL"; color:"#91a5af"; font.family:"Adwaita Sans"; font.pixelSize:13; font.letterSpacing:2 }
        Plugin.SpoilerPreview { id:prism; x:30; y:96; width:434; height:194; radius:12; appearance:({variant:"prism",color:"#cbdcec",grain:65,speed:100,darkness:50,eye:true,eye_size:80,icon:"eye",icon_opacity:75}) }
        Plugin.SpoilerPreview { id:signal; x:496; y:96; width:434; height:194; radius:12; appearance:({variant:"signal",color:"#cbdcec",grain:65,speed:100,darkness:50,eye:false,eye_size:80,icon:"none",icon_opacity:75}) }
        Text { x:31; y:312; text:"Procedural QML preview · No window pixels · Not a native capture recording"; color:"#7c909b"; font.family:"Adwaita Sans"; font.pixelSize:13 }
    }
    Timer {
        interval:100; running:true; repeat:true
        onTriggered: {
            if (!hiding.opened) { hiding.open(); appearance.open(); return }
            if (!hiding.current.known || !appearance.current.known || hiding.querying || appearance.querying) return
            if (hiding.language!=="en" || appearance.language!=="en") throw new Error("preview must be English")
            if (String(Color.background)!=="#101315" || String(Color.foreground)!=="#dce4e8" || String(Color.accent)!=="#9eb7c6") return
            if (root.frame===0) appearance.setTab("customize")
            root.readyTicks++
            if (root.readyTicks<3) return
            if (!root.panelsSaved) {
                root.panelsSaved=true
                hidingWindow.contentItem.grabToImage(function(r) { r.saveToFile(HIDING) })
                appearanceWindow.contentItem.grabToImage(function(r) { r.saveToFile(APPEARANCE_PANEL) })
            }
            if (root.capturing) return
            root.capturing=true
            prism.children.find(function(c) { return typeof c.phase === "number" }).phase=root.frame/32*Math.PI*2
            signal.children.find(function(c) { return typeof c.phase === "number" }).phase=root.frame/32*Math.PI*2
            Qt.callLater(function() {
                texturesWindow.contentItem.grabToImage(function(r) {
                    r.saveToFile(FRAMES + "/" + String(root.frame).padStart(2,"0") + ".png")
                    root.frame++
                    root.capturing=false
                    if (root.frame===32) { console.log("HYPRVEIL_PUBLIC_PREVIEW_OK"); Qt.quit() }
                })
            })
        }
    }
}
'''
    for key, value in {"APPEARANCE_PANEL": str(ASSETS / "appearance-panel.png"), "APPEARANCE": APPEARANCE,
                       "BRAND": str(ASSETS / "brand.svg"), "HIDING": str(ASSETS / "hiding-panel.png"),
                       "SOCIAL": str(ASSETS / "social-preview.png"), "FRAMES": str(frames)}.items():
        qml = qml.replace(key, json.dumps(value))
    (fixture / "shell.qml").write_text(qml)
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(home), "XDG_RUNTIME_DIR": str(runtime),
           "QT_QPA_PLATFORM": "offscreen", "QT_QUICK_BACKEND": "software", "QT_QPA_PLATFORMTHEME":"",
           "QT_STYLE_OVERRIDE":"Fusion", "QML_DISABLE_DISK_CACHE": "1"}
    result = subprocess.run(["/usr/bin/quickshell", "--no-color", "--path", str(fixture)], env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=15)
    if result.returncode or "HYPRVEIL_PUBLIC_PREVIEW_OK" not in result.stdout:
        raise SystemExit(result.stdout)
    frames_png = [Image.open(path).convert("RGB") for path in sorted(frames.glob("*.png"))]
    frames_png[0].save(ASSETS / "spoiler-preview.gif", save_all=True, append_images=frames_png[1:],
                       duration=438, loop=0, optimize=True)
    for name in ("hiding-panel.png", "appearance-panel.png"):
        with Image.open(ASSETS / name) as image:
            assert image.mode in ("RGB", "RGBA")
            assert image.mode == "RGB" or image.getchannel("A").getextrema() == (255, 255)
            # Strip all ancillary metadata; only the synthetic rendered pixels ship.
            opaque = image.convert("RGB")
        opaque.save(ASSETS / name, optimize=True)

# The QML process and its isolated fixture have both stopped before publishing
# the final composition and its hashes.
marketplace_cover()
write_provenance()
assert (ROOT / "preview.png").is_file()
print("Rendered English QML panels, synthetic animation, minimal 1280×640 illustrated cover.")
