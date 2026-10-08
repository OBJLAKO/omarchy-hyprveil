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
APPEARANCE = {"variant": "telegram", "color": "#cbdcec", "grain": 65,
              "speed": 100, "darkness": 50, "eye": True, "eye_size": 80}
NATIVE_POSTER_SHA256 = "90d26f63344fcc0e2b5da3135fd49e35e3b9678dc00f20f0b382de5f52f46b2a"


def marketplace_cover():
    """Compose actual materials; never draw window contents or spoiler pixels."""
    poster = ASSETS / "native-demo.png"
    if hashlib.sha256(poster.read_bytes()).hexdigest() != NATIVE_POSTER_SHA256:
        raise RuntimeError("native sample differs from its reviewed synthetic capture")
    native = json.loads((ASSETS / "native-capture-provenance.json").read_text())
    if (native.get("source") != "real Hyprland GPU captures in a fresh marked isolated compositor"
            or not native.get("lab_stopped")
            or not native.get("marker_absent_from_every_protected_frame")
            or native["outputs"]["demo/poster.png"]["sha256"] != NATIVE_POSTER_SHA256):
        raise RuntimeError("native sample lacks stopped, synthetic capture provenance")
    cover = Image.new("RGB", (1600, 900), "#0e1619")
    draw = ImageDraw.Draw(cover)
    font_path = "/usr/share/fonts/Adwaita/AdwaitaSans-Regular.ttf"

    def label(x, y, value, size, fill="#dce5e6"):
        font = ImageFont.truetype(font_path, size)
        draw.text((x, y), value, font=font, fill=fill)

    draw.line((1046, 52, 1046, 840), fill="#2a3a40", width=1)
    label(58, 38, "HYPRVEIL  /  OMARCHY", 19, "#9bb7c1")
    label(54, 83, "Capture privacy", 73, "#edf2ed")
    label(54, 164, "from your bar.", 73, "#edf2ed")
    label(59, 258, "Keep your window visible. Choose what its capture reveals.", 24, "#a7bbb9")
    label(59, 306, "ONE CLICK    ·    THREE STYLES    ·    LIVE APPEARANCE", 16, "#89aa9c")
    with Image.open(poster) as sample:
        cover.paste(sample.convert("RGB"), (58, 350))
    label(59, 841, "Hyprveil native capture · synthetic notes", 16, "#91a9a3")
    label(1089, 30, "REAL OMARCHY PANEL", 15, "#9bb7c1")
    draw.rounded_rectangle((1077, 59, 1557, 836), radius=18, fill="#101315", outline="#32444c", width=1)
    with Image.open(ASSETS / "appearance-panel.png") as panel:
        panel = panel.convert("RGB").resize((456, 751), Image.Resampling.LANCZOS)
        cover.paste(panel, (1089, 72))
    label(1089, 848, "Offscreen QML · English / Russian", 15, "#8ba5ae")
    cover.save(ROOT / "preview.png", optimize=True)


def write_provenance():
    names = ["preview.png", "assets/hiding-panel.png", "assets/appearance-panel.png",
             "assets/social-preview.png", "assets/spoiler-preview.gif", "assets/native-demo.png"]
    native = json.loads((ASSETS / "native-capture-provenance.json").read_text())
    data = {
        "version": 1,
        "ui": {"source": "real repository QML components rendered with Qt offscreen",
               "locale": "English (C.UTF-8)", "controller": "status-only synthetic fixture",
               "theme": "explicit synthetic palette in temporary HOME",
               "personal_desktop_capture": False, "native_rendering": False},
        "native_sample": {"source": "Hyprveil native capture of synthetic GTK notes in a marked isolated compositor",
                          "native_sha256": native["native_sha256"], "lab_stopped": True,
                          "upstream_repository": "https://github.com/OBJLAKO/hyprveil",
                          "upstream_asset": "assets/demo/poster.png",
                          "sha256": NATIVE_POSTER_SHA256},
        "composition": "crop-free scaling, labels and framing; no synthesized native window or mask pixels",
        "outputs": {name: {"sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(),
                           "bytes": (ROOT / name).stat().st_size} for name in names},
    }
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
        Plugin.Panel { id: hiding; x:20; y:20; manageIpc:false; hostWidget:syntheticPrivacy }
    }
    Window {
        id: appearanceWindow
        width: 510; height: 840; visible: true; color: "#101315"
        Rectangle { anchors.fill:parent; color:"#101315" }
        Plugin.Panel { id: appearance; x:20; y:20; manageIpc:false; hostWidget:syntheticPrivacy }
    }
    Window {
        id: socialWindow
        width:1280; height:640; visible:true; color:"#10171b"
        Rectangle { anchors.fill:parent; color:"#10171b" }
        Image { x:0; y:0; width:1280; height:360; source:BRAND }
        Text { x:90; y:362; text:"A focused control panel for capture privacy."; color:"#d9e2e2"; font.family:"Adwaita Sans"; font.pixelSize:30 }
        Plugin.SpoilerPreview {
            x:90; y:435; width:440; height:116; radius:12
            appearance: APPEARANCE
        }
        Column {
            x:580; y:437; spacing:15
            Text { text:"WINDOW PRIVACY  /  NATIVE SETTINGS"; color:"#9cacb4"; font.family:"Adwaita Sans"; font.pixelSize:17; font.letterSpacing:2 }
            Text { text:"Satin · Telegram · Black · Omit"; color:"#d4dcdd"; font.family:"Adwaita Sans"; font.pixelSize:25 }
            Text { text:"OBJLAKO / omarchy-hyprveil"; color:"#778c96"; font.family:"Adwaita Sans"; font.pixelSize:17 }
        }
        Text { x:90; y:595; text:"Procedural UI preview · Native rendering belongs to Hyprveil."; color:"#778c96"; font.family:"Adwaita Sans"; font.pixelSize:14 }
    }
    Window {
        id: texturesWindow
        width:960; height:350; visible:true; color:"#10171b"
        Rectangle { anchors.fill:parent; color:"#10171b" }
        Text { x:30; y:20; text:"Spoiler appearance"; color:"#d6e0e0"; font.family:"Adwaita Sans"; font.pixelSize:25 }
        Text { x:31; y:67; text:"SATIN"; color:"#91a5af"; font.family:"Adwaita Sans"; font.pixelSize:13; font.letterSpacing:2 }
        Text { x:497; y:67; text:"TELEGRAM"; color:"#91a5af"; font.family:"Adwaita Sans"; font.pixelSize:13; font.letterSpacing:2 }
        Plugin.SpoilerPreview { id:satin; x:30; y:96; width:434; height:194; radius:12; appearance:({variant:"satin",color:"#cbdcec",grain:65,speed:100,darkness:50,eye:true,eye_size:80}) }
        Plugin.SpoilerPreview { id:telegram; x:496; y:96; width:434; height:194; radius:12; appearance:APPEARANCE }
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
                socialWindow.contentItem.grabToImage(function(r) { r.saveToFile(SOCIAL) })
            }
            if (root.capturing) return
            root.capturing=true
            satin.children.find(function(c) { return typeof c.phase === "number" }).phase=root.frame/32*Math.PI*2
            telegram.children.find(function(c) { return typeof c.phase === "number" }).phase=root.frame/32*Math.PI*2
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
    for name in ("hiding-panel.png", "appearance-panel.png", "social-preview.png"):
        with Image.open(ASSETS / name) as image:
            assert image.mode in ("RGB", "RGBA")
            assert image.mode == "RGB" or image.getchannel("A").getextrema() == (255, 255)
            # Strip all ancillary metadata; only the synthetic rendered pixels ship.
            opaque = image.convert("RGB")
        opaque.save(ASSETS / name, optimize=True)
    assert Image.open(ASSETS / "social-preview.png").size == (1280, 640)
    assert (ASSETS / "social-preview.png").stat().st_size < 1024 * 1024

# The QML process and its isolated fixture have both stopped before publishing
# the final composition and its hashes.
marketplace_cover()
write_provenance()
assert (ROOT / "preview.png").is_file()
print("Rendered English QML panels, synthetic animation, 1280×640 social card and 1600×900 marketplace preview.")
