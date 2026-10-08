#!/usr/bin/env python3
"""Render only synthetic QML masks; test RGB tint, full darkness and pearl eye."""
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

plugin = Path(__file__).resolve().parents[1]
def appearance(variant="satin", color="#ffffff", darkness=50, eye=False):
    return {"variant": variant, "color": color, "grain": 100, "speed": 0,
            "darkness": darkness, "eye": eye, "eye_size": 80}
cases = [appearance(variant=variant, color=color, darkness=darkness)
         for variant in ("satin", "telegram")
         for color, darkness in (("#000000", 50), ("#ffffff", 100))]
cases += [appearance(color="#ff0000"), appearance(color="#ff0000", darkness=100, eye=True)]
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
        width: 720; height: 96; visible: true; color: "#000000"
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
""".replace("CASES", json.dumps(cases)).replace("OUTPUT", json.dumps(str(output)))
    shell = fixture / "shell.qml"
    shell.write_text(source)
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(fixture),
           "XDG_RUNTIME_DIR": str(runtime), "QT_QPA_PLATFORM": "offscreen",
           "QT_QUICK_BACKEND": "software", "QML_DISABLE_DISK_CACHE": "1"}
    result = subprocess.run(["/usr/bin/quickshell", "-p", str(shell)], env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
    assert result.returncode == 0 and "HYPRVEIL_SYNTHETIC_COLORS_OK" in result.stdout, result.stdout
    image = Image.open(output).convert("RGBA")
    for index in range(4):
        field = pixels(image, (index * 120 + 10, 10, index * 120 + 110, 86))
        assert all(pixel == (0, 0, 0, 255) for pixel in field), (index, set(field))
    red = pixels(image, (490, 10, 590, 86))
    assert any(r > 0 for r, g, b, a in red) and all(g == b == 0 and a == 255 for r, g, b, a in red)
    eye = pixels(image, (610, 10, 710, 86))
    assert any(g > 20 and b > 20 for r, g, b, a in eye), "eye incorrectly follows the red tint or darkness"
    assert all(a == 255 for r, g, b, a in eye), "mask preview is not opaque"
print("passed 6 synthetic preview color, darkness, opacity and constant-eye cases")
