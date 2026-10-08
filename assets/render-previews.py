#!/usr/bin/env python3
"""Render public docs from real QML components and synthetic state only.

Requires installed Omarchy/Quickshell and Pillow. All windows use Qt offscreen;
the fixture has no desktop environment, native controller or personal pixels.
"""
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
APPEARANCE = {"variant": "telegram", "color": "#cbdcec", "grain": 65,
              "speed": 100, "darkness": 50, "eye": True, "eye_size": 80}

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
    (fixture / "plugin").symlink_to(ROOT / "plugin")
    controller = commands / "hyprveil"
    status = {"enabled": True, "loaded": True, "desired_mode": "spoiler", "appearance": APPEARANCE,
              "status": {"mode": "spoiler", "session": "live", "local_dump": "disabled-in-live",
                         "spoiler_status": "ready", "appearance": APPEARANCE}}
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
    assert Image.open(ASSETS / "social-preview.png").size == (1280, 640)
    assert (ASSETS / "social-preview.png").stat().st_size < 1024 * 1024
    print("Rendered real QML panels, synthetic preview animation and 1280×640 social card.")
