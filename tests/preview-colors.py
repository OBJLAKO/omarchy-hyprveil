#!/usr/bin/env python3
"""Render only synthetic QML masks; test RGB tint, full darkness and pearl eye."""
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

plugin = Path(__file__).resolve().parents[1]
def appearance(variant="prism", color="#ffffff", darkness=50, eye=False, icon="eye", icon_opacity=75):
    return {"variant": variant, "color": color, "grain": 100, "speed": 0,
            "darkness": darkness, "eye": eye, "eye_size": 80, "icon": icon, "icon_opacity": icon_opacity}
cases = [appearance(variant=variant, color=color, darkness=darkness)
         for variant in ("prism", "signal", "aurora", "contour", "radar", "matte", "error404", "matrix", "anonymous", "glass")
         for color, darkness in (("#000000", 50), ("#ffffff", 100))]
cases += [appearance(color="#ff0000")]
cases += [appearance(color="#ff0000", darkness=100, eye=True, icon=icon) for icon in ("eye", "lock", "shield")]
cases += [appearance(darkness=100, eye=True, icon="none"), appearance(darkness=100, eye=True, icon_opacity=0)]
def pixels(image, box):
    crop = image.crop(box)
    return list(getattr(crop, "get_flattened_data", crop.getdata)())
with tempfile.TemporaryDirectory(prefix="hyprveil-preview-") as temp:
    fixture = Path(temp)
    runtime = fixture / "runtime"
    runtime.mkdir(mode=0o700)
    (fixture / "plugin").symlink_to(plugin)
    output = fixture / "masks.png"
    source = """
import QtQuick
import Quickshell
import "./plugin" as Plugin
ShellRoot {
    Window {
        id: window
        width: CASE_WIDTH; height: 96; visible: true; color: "#000000"
        Row {
            Repeater {
                model: CASES
                delegate: Plugin.SpoilerPreview {
                    required property var modelData
                    width: 120; height: 96; radius: 0; border.width: 0
                    appearance: modelData
                }
            }
        }
        Timer {
            interval: 350; running: true
            onTriggered: window.contentItem.grabToImage(function(result) {
                result.saveToFile(OUTPUT)
                console.log("HYPRVEIL_SYNTHETIC_COLORS_OK")
                Qt.quit()
            })
        }
    }
}
""".replace("CASE_WIDTH", str(120 * len(cases))).replace("CASES", json.dumps(cases)).replace("OUTPUT", json.dumps(str(output)))
    shell = fixture / "shell.qml"
    shell.write_text(source)
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(fixture),
           "XDG_RUNTIME_DIR": str(runtime), "QT_QPA_PLATFORM": "offscreen",
           "QT_QUICK_BACKEND": "software", "QML_DISABLE_DISK_CACHE": "1"}
    result = subprocess.run(["/usr/bin/quickshell", "-p", str(shell)], env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
    assert result.returncode == 0 and "HYPRVEIL_SYNTHETIC_COLORS_OK" in result.stdout, result.stdout
    image = Image.open(output).convert("RGBA")
    for index in range(20):
        field = pixels(image, (index * 120 + 10, 10, index * 120 + 110, 86))
        assert all(pixel == (0, 0, 0, 255) for pixel in field), (index, set(field))
    red = pixels(image, (2410, 10, 2510, 86))
    assert any(r > 0 for r, g, b, a in red) and all(g == b == 0 and a == 255 for r, g, b, a in red)
    for index in range(21, 24):
        icon = pixels(image, (index * 120 + 10, 10, index * 120 + 110, 86))
        assert any(g > 20 and b > 20 for r, g, b, a in icon), "icon incorrectly follows the red tint or darkness"
        assert all(a == 255 for r, g, b, a in icon), "mask preview is not opaque"
    for index in range(24, 26):
        field = pixels(image, (index * 120 + 10, 10, index * 120 + 110, 86))
        assert all(pixel == (0, 0, 0, 255) for pixel in field), "hidden icon changed mask opacity or color"
print("passed 26 synthetic preview tint, darkness, icon and opacity cases")
