#!/usr/bin/env python3
"""Exercise real QML autosave scheduling with isolated, delayed subprocesses.

No compositor, installed controller, user configuration or desktop bus is used.
The fixture records every argv and final state, rather than mocking QML methods.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

PLUGIN = Path(os.environ.get("HYPRVEIL_TEST_PLUGIN", Path(__file__).resolve().parents[1]))
SCENARIOS = ("during-configure", "during-query", "atomic-icon", "close-debounce",
             "close-inflight", "failure-recovery", "privacy-busy", "invalid-color",
             "queued-close", "queued-query-close", "focused-external-color", "motif-layout")
DEFAULTS = {"variant": "prism", "color": "#ffffff", "grain": 50, "speed": 100,
            "darkness": 50, "eye": True, "eye_size": 80, "icon": "eye", "icon_opacity": 75}

CONTROLLER = r'''#!/usr/bin/python3
import json, os, pathlib, sys, time
home = pathlib.Path(os.environ["HOME"])
action = sys.argv[1]
previous = [json.loads(line) for line in (home / "commands.jsonl").read_text().splitlines()] if (home / "commands.jsonl").exists() else []
number = 1 + sum(row["action"] == action for row in previous)
record = {"action": action, "argv": sys.argv[1:], "number": number, "pid": os.getpid(), "time": time.monotonic(),
          "clean": all(key not in os.environ for key in ("PYTHONPATH", "BASH_ENV", "LD_PRELOAD", "LD_LIBRARY_PATH", "DBUS_SESSION_BUS_ADDRESS", "HYPRLAND_INSTANCE_SIGNATURE"))}
with (home / "commands.jsonl").open("a") as file:
    file.write(json.dumps(record) + "\n")
state = json.loads((home / "state.json").read_text())
if action == "status":
    if SCENARIO in ("during-query", "focused-external-color", "queued-query-close") and number == 2:
        if SCENARIO == "during-query":
            state["speed"] = 130
        elif SCENARIO == "focused-external-color":
            state["color"] = "#adcfc8"
        (home / "state.json").write_text(json.dumps(state))
        time.sleep(0.36)
    else:
        time.sleep(0.035)
    print(json.dumps({"loaded": True, "enabled": True, "load_supported": False, "persistence_supported": True,
        "desired_mode": "black", "appearance": state,
        "status": {"session": "live", "local_dump": "disabled-in-live", "mode": "black", "appearance": state}}))
elif action == "configure":
    time.sleep(0.36)
    if SCENARIO == "failure-recovery" and number == 1:
        print("fixture refused persistence /secret/private.lua", file=sys.stderr)
        sys.exit(17)
    names = {"--variant": "variant", "--color": "color", "--grain": "grain", "--speed": "speed", "--darkness": "darkness",
             "--eye": "eye", "--eye-size": "eye_size", "--icon": "icon", "--icon-opacity": "icon_opacity"}
    args = sys.argv[2:]
    if not args or len(args) % 2:
        sys.exit("malformed configure argv")
    for flag, value in zip(args[::2], args[1::2]):
        key = names[flag]
        state[key] = value == "on" if key == "eye" else value if key in ("variant", "color", "icon") else int(value)
    (home / "state.json").write_text(json.dumps(state))
    print(json.dumps({"appearance": state}))
elif action == "black":
    print(json.dumps({"mode": "black"}))
else:
    sys.exit("unexpected fixture action")
'''

QML = r'''import QtQuick
import Quickshell
import "./plugin" as Plugin
ShellRoot {
    Item { id: host; property bool privacyBusy: false; property bool privacyDispatching: false
        property var focusPrivacy: ({state:"unknown",address:"",stable_id:"",native_private:false,inherited:false}) }
    Window { width: 510; height: 900; visible: true
        Plugin.Panel { id: panel; manageIpc: false; hostWidget: host
            controllerCommand: [Quickshell.env("HOME") + "/.local/bin/hyprveil"] }
    }
    property var editor: null
    property var popup: null
    property var hex: null
    property int stage: 0
    property int ticks: 0
    property int checkpoint: 0
    property real initialHeight: 0
    property real maxHeightDelta: 0
    property int editableSamples: 0
    property int motifIndex: 0
    property var motifs: ["error404", "anonymous", "matrix"]
    function find(item, kind, name) {
        if (kind === "editor" && typeof item.advanced === "boolean" && item.draft !== undefined) return item
        if (kind === "popup" && item.contentWidth !== undefined && typeof item.fittedContentHeight === "function") return item
        if (kind === "icon" && item.modelData === name && typeof item.clicked === "function") return item
        if (kind === "preset" && item.modelData === name && typeof item.pick === "function") return item
        if (kind === "hex" && item.acceptableInput !== undefined && typeof item.textEdited === "function") return item
        for (var i=0;i<item.children.length;i++) { var child=find(item.children[i],kind,name); if(child) return child }
        return null
    }
    function edit(key, value) { editor.edited(key,value) }
    function settled() { return !panel.acting && !panel.querying && !panel.appearanceDirty && panel.submittedFields === null }
    function expect(value, reason) { if (!value) throw new Error(SCENARIO + ": " + reason + " stage=" + stage) }
    function finish() {
        expect(panel.current.known && panel.current.loaded, "lost attested current state")
        expect(!panel.appearanceSaveBlocked && !panel.appearanceDirty, "save not confirmed")
        expect(editableSamples > 0 || SCENARIO === "focused-external-color" || SCENARIO === "queued-query-close", "configure interval not observed")
        console.log("HYPRVEIL_AUTOSAVE_OK " + JSON.stringify({scenario:SCENARIO,editable_samples:editableSamples,max_height_delta:maxHeightDelta,closed:!panel.opened}))
        Qt.quit()
    }
    Component.onCompleted: panel.open()
    Timer {
        interval: 20; running: true; repeat: true
        onTriggered: {
            ticks++
            if (editor && panel.acting && panel.actionName === "configure") {
                expect(panel.current.known && editor.enabled && !editor.busy, "configure disabled controls or cleared known state")
                editableSamples++
                if (panel.opened && SCENARIO !== "atomic-icon") {
                    maxHeightDelta=Math.max(maxHeightDelta,Math.abs(popup.contentHeight-initialHeight))
                    expect(maxHeightDelta <= 1, "configure changed popup height")
                }
            }
            if (stage === 0 && panel.current.known && !panel.querying) {
                panel.setTab("customize")
                editor=find(panel,"editor",""); popup=find(panel,"popup",""); hex=find(panel,"hex","")
                expect(editor && popup && hex, "real editor controls not found")
                if (SCENARIO === "atomic-icon" || SCENARIO === "invalid-color" || SCENARIO === "motif-layout") editor.advanced=true
                stage=1
            } else if (stage === 1) {
                initialHeight=popup.contentHeight
                if (SCENARIO === "during-query") { panel.refresh(false); stage=2 }
                else if (SCENARIO === "motif-layout") {
                    expect(panel.appearanceDraft.variant==="prism" && panel.appearanceDraft.eye, "motif layout baseline changed")
                    find(editor,"preset",motifs[0]).pick(); stage=14
                }
                else if (SCENARIO === "queued-query-close") {
                    panel.refresh(false); panel.act("black"); panel.close(); stage=8
                }
                else if (SCENARIO === "focused-external-color") {
                    hex.forceActiveFocus(); panel.refresh(false); stage=12
                }
                else if (SCENARIO === "atomic-icon") {
                    var icon=find(editor,"icon","shield")
                    expect(icon && icon.visible && icon.enabled, "actual icon selector unavailable")
                    icon.clicked()
                    expect(panel.appearanceDraft.icon === "shield" && panel.appearanceDraft.eye, "icon visibility patch not atomic")
                    stage=8
                } else {
                    edit("grain",17)
                    if (SCENARIO === "close-debounce") { panel.close(); stage=8 }
                    else if (SCENARIO === "invalid-color") {
                        hex.forceActiveFocus(); hex.text="#12"; hex.textEdited()
                        expect(!editor.colorValid, "invalid color accepted")
                        var theme=find(editor,"preset","matrix"), lock=find(editor,"icon","lock")
                        expect(theme.enabled && lock.enabled, "incomplete color disabled unrelated controls")
                        theme.pick(); lock.clicked()
                        expect(!editor.colorValid, "other controls rewrote focused incomplete color")
                        panel.close(); stage=8
                    } else stage=3
                }
            } else if (stage === 2 && panel.querying) {
                edit("grain",18); edit("grain",24)
                stage=8
            } else if (stage === 3 && panel.acting && panel.actionName === "configure") {
                if (SCENARIO === "during-configure") {
                    edit("grain",18); edit("grain",17); edit("grain",23)
                    var nextTheme=find(editor,"preset","matrix")
                    expect(nextTheme.enabled, "inflight configure disabled preset selector")
                    nextTheme.pick()
                    stage=8
                } else if (SCENARIO === "close-inflight") {
                    edit("grain",23); panel.close(); stage=8
                } else if (SCENARIO === "privacy-busy") {
                    host.privacyBusy=true; panel.close(); stage=4
                } else if (SCENARIO === "queued-close") {
                    panel.act("black"); panel.close(); stage=8
                } else stage=5
            } else if (stage === 4 && !panel.acting) {
                expect(host.privacyBusy && panel.submittedFields !== null, "busy acknowledgement overlap not exercised")
                checkpoint=ticks; stage=6
            } else if (stage === 6 && ticks-checkpoint>=8) {
                host.privacyBusy=false; stage=8
            } else if (stage === 5 && panel.appearanceSaveBlocked && !panel.acting && !panel.querying) {
                expect(panel.appearanceDirty && panel.appearanceDraft.grain===17 && panel.current.appearance.grain===50, "failure discarded dirty edit or claimed success")
                expect(panel.appearanceError.length>0 && panel.appearanceError.indexOf("/secret/")<0, "failure leaked diagnostics or lost error")
                checkpoint=ticks; panel.refresh(false); stage=7
            } else if (stage === 7) {
                expect(!panel.acting && panel.appearanceSaveBlocked && panel.appearanceDirty, "failure retried without new edit")
                if (ticks-checkpoint===8 || ticks-checkpoint===16) panel.refresh(false)
                if (ticks-checkpoint>=24 && !panel.querying) { edit("grain",24); stage=8 }
            } else if (stage === 14) {
                maxHeightDelta=Math.max(maxHeightDelta,Math.abs(popup.contentHeight-initialHeight))
                expect(maxHeightDelta<=1, "art motif or icon hint changed popup height")
                if (settled()) {
                    expect(panel.current.appearance.variant===motifs[motifIndex] && panel.current.appearance.eye, "motif not freshly confirmed with visible icon")
                    if (++motifIndex === motifs.length) finish()
                    else find(editor,"preset",motifs[motifIndex]).pick()
                }
            } else if (stage === 12 && !panel.querying) {
                expect(panel.current.appearance.color==="#adcfc8" && hex.text==="#ffffff", "focused untouched text did not preserve external native color")
                editor.forceActiveFocus(); checkpoint=ticks; stage=13
            } else if (stage === 13 && ticks-checkpoint>=2) {
                expect(hex.text==="#adcfc8" && !panel.appearanceDirty && !panel.acting, "blur overwrote external color or marked untouched text dirty")
                finish()
            } else if (stage === 8 && settled()) {
                var expected=SCENARIO === "during-configure" || SCENARIO === "close-inflight" ? 23 : SCENARIO === "during-query" || SCENARIO === "failure-recovery" ? 24 : SCENARIO === "atomic-icon" || SCENARIO === "queued-query-close" ? 50 : 17
                expect(panel.current.appearance.grain===expected && panel.appearanceDraft.grain===expected, "latest edit was lost")
                if (SCENARIO === "during-query") expect(panel.current.appearance.speed===130 && panel.appearanceDraft.speed===130, "untouched native field overwritten")
                if (SCENARIO === "during-configure") expect(panel.current.appearance.variant==="matrix", "latest variant was lost")
                if (SCENARIO === "invalid-color") expect(panel.current.appearance.color==="#ffffff" && panel.current.appearance.variant==="matrix" && panel.current.appearance.icon==="lock" && editor.colorValid && !panel.opened, "incomplete color prevented other saves or leaked into model")
                if (SCENARIO.indexOf("close-")===0 || SCENARIO === "privacy-busy" || SCENARIO === "queued-close" || SCENARIO === "queued-query-close") expect(!panel.opened, "closed save reopened panel")
                finish()
            }
            if (ticks>200) throw new Error(SCENARIO + ": autosave failed to settle stage=" + stage)
        }
    }
}
'''


def run_case(scenario):
    with tempfile.TemporaryDirectory(prefix="hyprveil-autosave-") as temporary:
        root = Path(temporary)
        (root / "Commons").symlink_to("/usr/share/omarchy/shell/Commons")
        ui = root / "Ui"
        ui.mkdir()
        for source in Path("/usr/share/omarchy/shell/Ui").iterdir():
            if source.name != "KeyboardPanel.qml":
                (ui / source.name).symlink_to(source)
        (ui / "KeyboardPanel.qml").write_text('''import QtQuick
Item {
    property Item anchorItem: null
    property QtObject bar: null
    property var owner: null
    property bool open: false
    property Item focusTarget: null
    property int contentWidth: 470
    property int contentHeight: 800
    width: contentWidth; height: contentHeight; visible: open
    function fittedContentWidth(v) { return v }
    function fittedContentHeight(v) { return v }
}
''')
        (root / "plugin").symlink_to(PLUGIN)
        home = root / "home"
        commands = home / ".local/bin"
        commands.mkdir(parents=True)
        state = dict(DEFAULTS)
        if scenario == "atomic-icon":
            state.update(eye=False, icon="none")
        (home / "state.json").write_text(json.dumps(state))
        controller = commands / "hyprveil"
        controller.write_text(CONTROLLER.replace("SCENARIO", repr(scenario)))
        controller.chmod(0o700)
        (root / "shell.qml").write_text(QML.replace("SCENARIO", json.dumps(scenario)))
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        environment = dict(os.environ, HOME=str(home), XDG_RUNTIME_DIR=str(runtime), QT_QPA_PLATFORM="offscreen",
                           QT_QUICK_BACKEND="software", QT_QPA_PLATFORMTHEME="", QT_STYLE_OVERRIDE="Fusion",
                           PYTHONPATH="/fixture-injection", BASH_ENV="/fixture-injection")
        for key in ("WAYLAND_DISPLAY", "DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "DBUS_SESSION_BUS_ADDRESS"):
            environment.pop(key, None)
        started = time.monotonic()
        output = ""
        returncode = -1
        try:
            result = subprocess.run(["/usr/bin/quickshell", "--no-color", "--path", str(root)], env=environment,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=7)
            output, returncode = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error:
            output = error.stdout.decode() if isinstance(error.stdout, bytes) else error.stdout or ""
        finally:
            log = [json.loads(line) for line in (home / "commands.jsonl").read_text().splitlines()] if (home / "commands.jsonl").exists() else []
            for record in log:
                try:
                    if str(controller).encode() in Path("/proc", str(record["pid"]), "cmdline").read_bytes().split(b"\0"):
                        os.kill(record["pid"], signal.SIGKILL)
                except (ProcessLookupError, FileNotFoundError):
                    pass
            leftovers = []
            for record in log:
                try:
                    if str(controller).encode() in Path("/proc", str(record["pid"]), "cmdline").read_bytes().split(b"\0"):
                        leftovers.append(record["pid"])
                except FileNotFoundError:
                    pass
        final = json.loads((home / "state.json").read_text())
        summary = {"scenario": scenario, "returncode": returncode, "seconds": round(time.monotonic()-started, 3),
                   "commands": log, "final": final, "output": output[-16384:]}
        summary["process_leftovers"] = leftovers
        summary["ok"] = returncode == 0 and "HYPRVEIL_AUTOSAVE_OK " in output and not any(
            word in output for word in ("TypeError", "ReferenceError", "Cannot assign", "Unable to assign", "Error:"))
        configurations = [row for row in log if row["action"] == "configure"]
        expected_count = 3 if scenario == "motif-layout" else 0 if scenario in ("focused-external-color", "queued-query-close") else 2 if scenario in ("during-configure", "close-inflight", "failure-recovery") else 1
        summary["ok"] &= len(configurations) == expected_count and all(row["clean"] for row in log) and not leftovers
        if scenario == "atomic-icon" and configurations:
            summary["ok"] &= dict(zip(configurations[0]["argv"][1::2], configurations[0]["argv"][2::2])) == {"--icon": "shield", "--eye": "on"}
        if scenario == "during-query" and configurations:
            summary["ok"] &= configurations[0]["argv"] == ["configure", "--grain", "24"] and final["speed"] == 130
        if scenario == "during-configure" and len(configurations) == 2:
            summary["ok"] &= dict(zip(configurations[1]["argv"][1::2], configurations[1]["argv"][2::2])) == {"--grain": "23", "--variant": "matrix"}
        if scenario == "invalid-color" and configurations:
            summary["ok"] &= "--color" not in configurations[0]["argv"] and final["color"] == "#ffffff" and final["variant"] == "matrix" and final["icon"] == "lock"
        if scenario == "queued-close":
            summary["ok"] &= [row["action"] for row in log if row["action"] != "status"] == ["configure", "black"]
        if scenario == "queued-query-close":
            summary["ok"] &= [row["action"] for row in log if row["action"] != "status"] == ["black"]
        if scenario == "focused-external-color":
            summary["ok"] &= all(row["action"] == "status" for row in log) and final["color"] == "#adcfc8"
        if scenario == "motif-layout":
            summary["ok"] &= [row["argv"] for row in configurations] == [["configure", "--variant", variant] for variant in ("error404", "anonymous", "matrix")]
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", action="append", choices=SCENARIOS)
    parser.add_argument("--report", type=Path)
    options = parser.parse_args()
    sources = ("Panel.qml", "AppearanceEditor.qml", "Appearance.js", "I18n.js", "State.js")
    before = {name: hashlib.sha256((PLUGIN / name).read_bytes()).hexdigest() for name in sources}
    results = []
    for scenario in options.scenario or SCENARIOS:
        result = run_case(scenario)
        results.append(result)
        print("passed" if result["ok"] else "FAILED", scenario, flush=True)
        if not result["ok"]:
            print(result["output"], flush=True)
            print(json.dumps(result["commands"], indent=2), flush=True)
    after = {name: hashlib.sha256((PLUGIN / name).read_bytes()).hexdigest() for name in sources}
    source_stable = before == after
    ok = all(row["ok"] for row in results) and source_stable
    if options.report:
        options.report.parent.mkdir(parents=True, exist_ok=True)
        options.report.write_text(json.dumps({"ok": ok, "source_stable": source_stable,
                                             "source_sha256": after, "cases": results}, indent=2) + "\n")
    if not source_stable:
        print("FAILED: imported QML/JS changed during test run")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
