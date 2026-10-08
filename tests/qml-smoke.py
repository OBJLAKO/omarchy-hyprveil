#!/usr/bin/env python3
"""Load widget offscreen with a test-only KeyboardPanel window backend.

The real Wayland KeyboardPanel is verified by the compositor integration tests.
This fixture checks QML component creation without connecting to the user's
compositor or invoking the installed Hyprveil controller.
"""
import os
import json
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

args = argparse.ArgumentParser()
args.add_argument("--language", choices=("auto", "en", "ru"), default="auto", help="exercise the bar language override")
args.add_argument("--locale", choices=("en", "ru"), default="en", help="exercise the interface in an isolated Qt locale")
args.add_argument("--missing-core", action="store_true", help="verify setup guidance without an installed controller")
args.add_argument("--lab", type=Path, help="use stock KeyboardPanel in a marked isolated Hyprland lab")
args.add_argument("--customize", action="store_true", help="exercise customization, preserved draft and steady background polling")
args.add_argument("--native-config", action="store_true", help="exercise authoritative native values and queued Lua reload")
args.add_argument("--status-failure", action="store_true", help="exercise malformed fresh status after a successful action")
args.add_argument("--configure-failure", action="store_true", help="exercise refused Lua persistence without claiming an applied appearance")
options = args.parse_args()
if options.native_config:
    options.customize = True
plugin = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="hyprveil-qml-") as temp:
    fixture = Path(temp)
    (fixture / "Commons").symlink_to(Path("/usr/share/omarchy/shell/Commons"))
    ui = fixture / "Ui"
    ui.mkdir()
    for source in Path("/usr/share/omarchy/shell/Ui").iterdir():
        if source.name != "KeyboardPanel.qml" or options.lab:
            (ui / source.name).symlink_to(source)
    if not options.lab:
        (ui / "KeyboardPanel.qml").write_text('''
import QtQuick
Item {
    id: root
    property Item anchorItem: null
    property QtObject bar: null
    property var owner: null
    property bool open: false
    property Item focusTarget: null
    property int contentWidth: 470
    property int contentHeight: 800
    width: contentWidth
    height: contentHeight
    visible: open
    function fittedContentWidth(value) { return value }
    function fittedContentHeight(value) { return value }
}
''')
    (fixture / "plugin").symlink_to(plugin)
    home = fixture / "home"
    commands = home / ".local/bin"
    commands.mkdir(parents=True)
    (home / "mock-state.json").write_text(json.dumps({"mode": "black", "appearance": {"variant": "satin", "color": "#ffffff", "grain": 50, "speed": 100, "darkness": 50, "eye": True, "eye_size": 80}}))
    controller = commands / "hyprveil"
    controller.write_text('''#!/usr/bin/python3
import json, os, pathlib, sys
home = pathlib.Path(os.environ["HOME"])
action = sys.argv[1]
with (home / "commands.jsonl").open("a") as log:
    log.write(json.dumps({"action": action, "argv": sys.argv[1:], "clean": all(k not in os.environ for k in
        ("PYTHONPATH", "BASH_ENV", "LD_PRELOAD", "LD_LIBRARY_PATH"))}) + "\\n")
state = json.loads((home / "mock-state.json").read_text())
if action == "status":
    if state.get("invalid"):
        print(json.dumps({"error": "unattested status"}))
        sys.exit(0)
    print(json.dumps({"enabled": True, "loaded": True, "desired_mode": "omit", "appearance": state["appearance"],
        "config_file": str(home / ".config/hypr/hyprveil-settings.lua"),
        "status": {"mode": state["mode"], "session": "live", "local_dump": "disabled-in-live", "spoiler_status": "ready", "appearance": state["appearance"]}}))
elif action in ("spoiler", "omit"):
    state.update(mode=action, invalid=EXPECT_FAILURE)
    (home / "mock-state.json").write_text(json.dumps(state))
    print(json.dumps({"mode": action}))
elif action == "configure":
    if CONFIGURE_FAILURE:
        print("refused private diagnostic /secret/config.lua", file=sys.stderr)
        sys.exit(1)
    opts = dict(zip(sys.argv[2::2], sys.argv[3::2]))
    state["appearance"] = {"variant": opts["--variant"], "color": opts["--color"], "grain": int(opts["--grain"]),
        "speed": int(opts["--speed"]), "darkness": int(opts["--darkness"]), "eye": opts["--eye"] == "on", "eye_size": int(opts["--eye-size"])}
    (home / "mock-state.json").write_text(json.dumps(state))
    print(json.dumps({"mode": state["mode"], "appearance": state["appearance"]}))
elif action == "reload-config":
    state["reloads"] = state.get("reloads", 0) + 1
    state["mode"] = "spoiler" if state["reloads"] == 1 else "black"
    state["appearance"] = {"variant": "telegram" if state["reloads"] == 1 else "satin",
        "color": "#e3d9ff" if state["reloads"] == 1 else "#adcfc8", "grain": 61 if state["reloads"] == 1 else 52,
        "speed": 80, "darkness": 50, "eye": True, "eye_size": 80}
    (home / "mock-state.json").write_text(json.dumps(state))
    print(json.dumps({"mode": state["mode"], "appearance": state["appearance"]}))
else:
    print("unexpected action", file=sys.stderr)
    sys.exit(1)
'''.replace("EXPECT_FAILURE", "True" if options.status_failure else "False").replace("CONFIGURE_FAILURE", "True" if options.configure_failure else "False"))
    controller.chmod(0o700)
    if options.missing_core:
        controller.unlink()
    (plugin / "artifacts").mkdir(exist_ok=True)
    qml = '''
import QtQuick
import Quickshell
import Quickshell.Wayland
import "./plugin" as Plugin
ShellRoot {
    Plugin.BarWidget { id: widget; settings: ({language: "LANGUAGE_OVERRIDE"}) }
    Window {
        id: window
        width: 510
        height: 840
        visible: true
        color: "#101315"
        Rectangle { anchors.fill: parent; color: "#101315" }
        Plugin.Panel { id: panel; x: 20; y: 20; manageIpc: false; hostWidget: widget; language: widget.language }
    }
    property string expectedLanguage: "TEST_LOCALE"
    function hasText(item, expected) {
        if (typeof item.text === "string" && item.text === expected && item.visible) return true
        for (var i=0;i<item.children.length;i++) if (hasText(item.children[i], expected)) return true
        return false
    }
    function visualSnapshot(item) {
        if (!item.visible) return null
        var data = {width:item.width,height:item.height,enabled:item.enabled,opacity:item.opacity,children:[]}
        if (typeof item.text === "string") data.text=item.text
        for (var i=0;i<item.children.length;i++) { var c=visualSnapshot(item.children[i]); if(c) data.children.push(c) }
        return data
    }
    property string unknownVisual: ""
    property int stage: 0
    property int ticks: 0
    property int closedAt: 0
    property var steadyCurrent: null
    property string steadyMessage: ""
    Timer {
        interval: 100
        running: true
        repeat: true
        onTriggered: {
            ticks++
            if (widget.opened) throw new Error("unexpected open panel")
            if (stage === 0 && ticks >= 4) {
                if (panel.querying || panel.acting) throw new Error("closed panel executed a command")
                if (panel.language !== expectedLanguage || widget.language !== expectedLanguage) throw new Error("system locale ignored")
                panel.open()
                stage = 1
            } else if (stage === 1 && MISSING_CORE) {
                if (panel.current.known || panel.acting || !hasText(panel, panel.tr("prerequisite")) || !hasText(panel, panel.tr("setup_guide"))) throw new Error("missing core has no honest setup guidance")
                panel.act("start"); panel.act("spoiler"); panel.applyAppearance()
                if (panel.acting) throw new Error("missing core granted an action")
                panel.close()
                console.log("HYPRVEIL_QML_SMOKE_OK")
                Qt.quit()
            } else if (stage === 1 && !panel.busy && !panel.querying && panel.current.known) {
                if (!hasText(panel, panel.tr("privacy")) || !hasText(panel, panel.tr("spoiler")) || !hasText(panel, panel.tr("omit"))) throw new Error("localized controls missing")
                if (panel.current.mode !== "black") throw new Error("initial status not verified")
                if (CONFIGURE_FAILURE) {
                    panel.setTab("customize")
                    panel.editAppearance("color", "#AABBCD")
                    panel.applyAppearance()
                    stage = 30
                    return
                }
                widget.privacyBusy = true
                panel.act("spoiler")
                if (panel.acting) throw new Error("style changed during a privacy command")
                widget.privacyBusy = false
                panel.act("spoiler;touch")
                if (panel.busy) throw new Error("untrusted action accepted")
                panel.act("stop")
                if (panel.busy) throw new Error("unload action accepted")
                panel.act("spoiler")
                stage = 2
            } else if (stage === 2 && !panel.busy && !panel.querying) {
                if (EXPECT_FAILURE) {
                    if (panel.current.known) throw new Error("unattested result accepted")
                    if (panel.message !== panel.tr("status_unconfirmed")) throw new Error("malformed status shown as success")
                    panel.act("omit")
                    if (panel.busy) throw new Error("unattested status allowed an action")
                } else if (!panel.current.known || panel.current.mode !== "spoiler") throw new Error("action not verified by a fresh status")
                if (!USE_LAB && !EXPECT_FAILURE) window.contentItem.grabToImage(function(result) {
                    result.saveToFile("PREVIEW_PATH")
                    console.log("HYPRVEIL_PREVIEW_OK")
                })
                stage = 3
            } else if (stage === 3) {
                if (!EXPECT_FAILURE) {
                    panel.cursor = 3
                    panel.activateCursor()
                    stage = 4
                } else { unknownVisual=JSON.stringify(visualSnapshot(panel)); closedAt=ticks; stage=40 }
            } else if (stage === 4 && !panel.busy && !panel.querying) {
                if (!panel.current.known || panel.current.mode !== "omit") throw new Error("original hide reset did not enter omit")
                stage = 5
            } else if (stage === 5) {
                if (CUSTOMIZE) {
                    panel.setTab("customize")
                    panel.editAppearance("color", "#AABBCD")
                    panel.refresh(false)
                    stage = 7
                    return
                }
                panel.close()
                panel.act("omit")
                if (panel.busy) throw new Error("closed panel accepted an action")
                closedAt = ticks
                stage = 6
            } else if (stage === 6 && ticks - closedAt >= 28) {
                if (panel.busy) throw new Error("closed panel polled")
                console.log("HYPRVEIL_QML_SMOKE_OK")
                Qt.quit()
            } else if (stage === 40) {
                if (panel.current.known || panel.acting || JSON.stringify(visualSnapshot(panel)) !== unknownVisual) throw new Error("unknown state background poll flickered")
                if (ticks-closedAt>=61 && !panel.querying) { console.log("HYPRVEIL_UNKNOWN_STEADY_OK"); panel.close(); closedAt=ticks; stage=6 }
            } else if (stage === 30 && !panel.busy && !panel.querying) {
                if (!panel.current.known || panel.current.mode !== "black" || panel.current.appearance.color !== "#ffffff" ||
                    !panel.appearanceDirty || panel.appearanceDraft.color !== "#aabbcd" ||
                    panel.message !== panel.tr("appearance_failed") || panel.message.indexOf("/secret/") >= 0)
                    throw new Error("refused Lua persistence shown as applied or leaked diagnostics")
                panel.close()
                closedAt = ticks
                stage = 6
            } else if (stage === 7 && !panel.querying) {
                if (!panel.appearanceDirty || panel.appearanceDraft.color !== "#aabbcd") throw new Error("poll overwrote unsaved draft")
                panel.editAppearance("speed", 201)
                if (panel.appearanceDraft.speed !== 100) throw new Error("invalid speed accepted")
                panel.refresh(false)
                panel.applyAppearance()
                panel.editAppearance("grain", 66)
                stage = 8
            } else if (stage === 8 && !panel.busy && !panel.querying) {
                if (!panel.current.known || panel.current.mode !== "omit" || panel.current.appearance.color !== "#aabbcd" || !panel.appearanceDirty || panel.appearanceDraft.grain !== 66)
                    throw new Error("appearance not acknowledged or hiding mode changed")
                panel.applyAppearance()
                stage = 18
            } else if (stage === 18 && !panel.busy && !panel.querying) {
                if (panel.appearanceDirty || panel.current.appearance.grain !== 66) throw new Error("newer queued draft was discarded")
                if (NATIVE_CONFIG) {
                    panel.editAppearance("grain", 73)
                    panel.editAppearance("speed", 0)
                    panel.refresh(false)
                    panel.cursor = panel.options().indexOf("reload-config")
                    panel.activateCursor()
                    panel.cursor = 0
                    stage = 20
                    return
                }
                panel.editAppearance("variant", "telegram")
                panel.applyAppearance()
                stage = 9
            } else if (stage === 20 && !panel.busy && !panel.querying) {
                if (!panel.current.known || panel.current.mode !== "spoiler" || panel.current.desiredMode !== "omit" ||
                    panel.current.appearance.color !== "#e3d9ff" || !panel.appearanceDirty || panel.appearanceDraft.grain !== 73 ||
                    panel.appearanceDraft.speed !== 0 || panel.message !== panel.tr("lua_reloaded_dirty"))
                    throw new Error("Lua reload lost draft or used stale saved settings")
                panel.appearanceDraft = panel.current.appearance
                panel.appearanceDirty = false
                panel.refresh(false)
                panel.act("reload-config")
                stage = 21
            } else if (stage === 21 && !panel.busy && !panel.querying) {
                if (!panel.current.known || panel.current.mode !== "black" || panel.current.desiredMode !== "omit" ||
                    panel.current.appearance.color !== "#adcfc8" || panel.appearanceDirty || panel.appearanceDraft.color !== "#adcfc8" ||
                    panel.appearanceDraft.grain !== 52 || panel.message !== panel.tr("lua_reloaded"))
                    throw new Error("clean draft did not follow confirmed native Lua settings")
                panel.editAppearance("variant", "telegram")
                panel.applyAppearance()
                stage = 9
            } else if (stage === 9 && !panel.busy && !panel.querying) {
                if (panel.current.appearance.variant !== "telegram" || panel.current.appearance.color !== (NATIVE_CONFIG ? "#adcfc8" : "#aabbcd") || panel.current.appearance.grain !== (NATIVE_CONFIG ? 52 : 66))
                    throw new Error("variant click lost preserved parameters")
                panel.editAppearance("grain", 73)
                panel.editAppearance("speed", 0)
                steadyCurrent = panel.current
                steadyMessage = panel.message
                closedAt = ticks
                stage = 10
            } else if (stage === 10) {
                if (ticks - closedAt === 3 && !USE_LAB) window.contentItem.grabToImage(function(result) { result.saveToFile("CUSTOM_PREVIEW_PATH") })
                if (panel.busy || panel.current !== steadyCurrent || panel.message !== steadyMessage || !panel.appearanceDirty ||
                    panel.appearanceDraft.grain !== 73 || panel.appearanceDraft.speed !== 0 || panel.cursor !== 0)
                    throw new Error("background poll flickered or reset unsaved changes")
                if (ticks - closedAt >= 81 && !panel.querying) {
                    var button = widget.children.find(function(item) { return typeof item.triggerPress === "function" })
                    if (!button) throw new Error("bar button missing")
                    var hidden = {state: "hidden", address: "0x123", stable_id: "402653184", native_private: true, inherited: false}
                    widget.consumePrivacy(JSON.stringify(hidden))
                    var eye = button.children.find(function(item) { return typeof item.uncertain === "boolean" })
                    if (!eye || !eye.crossed || eye.uncertain) throw new Error("hidden bar eye wrong")
                    widget.privacyTarget = hidden; widget.privacyBusy = true
                    widget.consumePrivacy(JSON.stringify(hidden))
                    if (!widget.privacyBusy) throw new Error("identical watch status prematurely confirmed toggle")
                    widget.consumePrivacy(JSON.stringify({state: "visible", address: "0x123", stable_id: "402653184", native_private: false, inherited: false}))
                    if (widget.privacyBusy || eye.crossed || eye.uncertain) throw new Error("actual watch confirmation not reflected")
                    widget.privacyQueuedTarget = widget.focusPrivacy; widget.privacyQueued = true
                    widget.consumePrivacy(JSON.stringify({state: "visible", address: "0x123", stable_id: "402653185", native_private: false, inherited: false}))
                    if (widget.privacyQueued || widget.privacyQueuedTarget.address !== "" || widget.privacyQueuedTarget.stable_id !== "" || widget.privacyBusy || widget.privacyDispatching)
                        throw new Error("queued click followed changed focus")
                    widget.privacyTarget = hidden; widget.privacyBusy = true; widget.privacyConfirmed = false
                    widget.consumePrivacy(JSON.stringify({state: "visible", address: "0x123", stable_id: "402653186", native_private: false, inherited: false}))
                    if (widget.privacyConfirmed || widget.privacyBusy) throw new Error("recycled address confirmed an old target")
                    button.triggerPress(Qt.LeftButton)
                    if (widget.opened) throw new Error("left button opened styles")
                    button.triggerPress(Qt.RightButton)
                    if (!widget.opened) throw new Error("right button did not open styles")
                    widget.close()
                    panel.close()
                    console.log("HYPRVEIL_EDITOR_STEADY_WATCH_OK")
                    console.log("HYPRVEIL_QML_SMOKE_OK")
                    Qt.quit()
                }
            }
            if (ticks > 150) throw new Error("controller did not complete")
        }
    }
}
'''.replace("TEST_LOCALE", options.locale if options.language == "auto" else options.language).replace("LANGUAGE_OVERRIDE", options.language).replace("MISSING_CORE", "true" if options.missing_core else "false").replace("CUSTOM_PREVIEW_PATH", str(plugin / "artifacts" / ("preview-customization-" + options.locale + ".png"))).replace("PREVIEW_PATH", str(plugin / "artifacts" / ("preview-" + options.locale + ".png"))).replace("CUSTOMIZE", "true" if options.customize else "false").replace("NATIVE_CONFIG", "true" if options.native_config else "false").replace("USE_LAB", "true" if options.lab else "false").replace("EXPECT_FAILURE", "true" if options.status_failure else "false").replace("CONFIGURE_FAILURE", "true" if options.configure_failure else "false")
    if options.lab:
        start = qml.index("    Window {")
        end = qml.index("    property int stage:", start)
        qml = qml[:start] + '''
    PanelWindow {
        id: window
        visible: true
        screen: Quickshell.screens[0]
        implicitHeight: 34
        anchors { top: true; left: true; right: true }
        color: "#101315"
        WlrLayershell.namespace: "hyprveil-ui-test"
        QtObject {
            id: barModel
            property string position: "top"
            property int barSize: 34
            property string fontFamily: "sans-serif"
            property color barForeground: "#cacccc"
            property var activePopout: null
            function requestPopout(key) { activePopout = key }
            function releasePopout(key) { if (activePopout === key) activePopout = null }
        }
        Item { id: anchor; width: 30; height: 34 }
        Plugin.Panel { id: panel; bar: barModel; anchorItem: anchor; manageIpc: false; hostWidget: widget; language: widget.language }
    }
''' + qml[end:]
    (fixture / "shell.qml").write_text(qml)
    runtime = fixture / "runtime"
    runtime.mkdir(mode=0o700)
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
                       QT_QPA_PLATFORMTHEME="", QT_STYLE_OVERRIDE="Fusion", XDG_RUNTIME_DIR=str(runtime),
                       HOME=str(home), PYTHONPATH="/fixture-injection", BASH_ENV="/fixture-injection")
    for key in ("WAYLAND_DISPLAY", "DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "DBUS_SESSION_BUS_ADDRESS"):
        environment.pop(key, None)
    if options.lab:
        from marked_lab import load_lab, lab_env
        lab_runtime, metadata = load_lab(options.lab)
        environment = lab_env(lab_runtime, metadata)
        environment.update(QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="", QT_STYLE_OVERRIDE="Fusion",
                           HOME=str(home), PYTHONPATH="/fixture-injection", BASH_ENV="/fixture-injection")
    environment.update(LANG="ru_RU.UTF-8" if options.locale == "ru" else "en_US.UTF-8", LC_ALL="ru_RU.UTF-8" if options.locale == "ru" else "en_US.UTF-8")
    output = subprocess.run(["/usr/bin/quickshell", "--no-color", "--path", str(fixture)],
                            env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, timeout=20)
    print(output.stdout)
    if output.returncode != 0 or "HYPRVEIL_QML_SMOKE_OK" not in output.stdout:
        raise SystemExit("QML did not load")
    forbidden = ("failed to load", "TypeError", "ReferenceError", "Cannot assign", "Unable to assign", "is not a type", "Unexpected token")
    if any(problem.lower() in output.stdout.lower() for problem in forbidden):
        raise SystemExit("QML reported an error")
    if options.missing_core:
        assert not (home / "commands.jsonl").exists(), "missing-core fixture unexpectedly ran a controller"
        print("passed missing-core guidance, locale and no-auto-install/load checks")
        raise SystemExit(0)
    log = [json.loads(line) for line in (home / "commands.jsonl").read_text().splitlines()]
    expected = ["status", "spoiler", "status"]
    if not options.status_failure:
        expected += ["omit", "status"]
    if options.customize:
        expected += ["status", "status", "configure", "status", "configure", "status"]
        if options.native_config:
            expected += ["status", "reload-config", "status", "status", "reload-config", "status"]
        expected += ["configure", "status"]
    actions = [record["action"] for record in log]
    if options.configure_failure:
        expected = ["status", "configure", "status"]
    if (not options.customize and (actions[:len(expected)] != expected or any(action != "status" for action in actions[len(expected):]))) or (options.customize and (actions[:len(expected)] != expected or any(action != "status" for action in actions[len(expected):]))):
        raise SystemExit("unexpected controller commands: " + repr(log))
    if not all(record["clean"] for record in log):
        raise SystemExit("unsafe inherited environment")
    print("passed QML load, action, fresh-status, allowlist, clean-environment and closed-panel polling checks")
