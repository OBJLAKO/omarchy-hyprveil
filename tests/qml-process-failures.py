#!/usr/bin/env python3
"""Exercise subprocess failure recovery offscreen, without a compositor.

Every child uses a temporary HOME. SIGTERM-resistant children are killed by the
fixture cleanup even if an unpatched widget fails a regression assertion.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile

PLUGIN = Path(os.environ.get("HYPRVEIL_TEST_PLUGIN", Path(__file__).resolve().parents[1]))
SCENARIOS = ("query-timeout", "query-overflow", "action-timeout", "query-start", "action-start",
             "hyprpm-unloaded", "hyprpm-runtime", "privacy-timeout", "privacy-overflow", "privacy-start", "watch-overflow")
DEFAULTS = {"variant": "prism", "color": "#ffffff", "grain": 50, "speed": 100,
            "darkness": 50, "eye": True, "eye_size": 80, "icon": "eye", "icon_opacity": 75}

for scenario in SCENARIOS:
    with tempfile.TemporaryDirectory(prefix="hyprveil-process-") as temporary:
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
        controller = commands / "hyprveil"
        controller.write_text('''#!/usr/bin/python3
import json, os, pathlib, signal, sys, time
home = pathlib.Path(os.environ["HOME"])
action = sys.argv[1]
with (home / "pids").open("a") as file:
    file.write(str(os.getpid()) + "\\n")
scenario = SCENARIO
if (scenario == "query-timeout" and action == "status") or (scenario == "action-timeout" and action == "spoiler") or scenario == "privacy-timeout":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    time.sleep(60)
if (scenario == "query-overflow" and action == "status") or scenario == "privacy-overflow":
    # Deliberately omit delimiters; a line parser must not buffer this forever.
    sys.stdout.write("x" * 131072); sys.stdout.flush()
    time.sleep(60)
if action == "status":
    p = DEFAULTS
    loaded = scenario != "hyprpm-unloaded"
    print(json.dumps({"loaded":loaded,"enabled":loaded,"load_supported":False,"persistence_supported":False,
        "desired_mode":"black","appearance":p,
        "status":{"session":"live","local_dump":"disabled-in-live","mode":"black","appearance":p} if loaded else None}))
'''.replace("SCENARIO", repr(scenario)).replace("DEFAULTS", repr(DEFAULTS)))
        controller.chmod(0o700)
        if scenario in ("query-start", "privacy-start"):
            controller.unlink()
        qml = '''import QtQuick
import Quickshell
import "./plugin" as Plugin
ShellRoot {
    Plugin.BarWidget { id: widget }
    Plugin.Panel { id: panel; manageIpc: false; controllerCommand: [Quickshell.env("HOME") + "/.local/bin/hyprveil"] }
    property var queryProcess: null
    property var actionProcess: null
    property var privacyProcess: null
    property int ticks: 0
    property int stage: 0
    function hasText(item, text) {
        if (item.text === text && item.visible) return true
        for (var i=0;i<item.children.length;i++) if(hasText(item.children[i],text)) return true
        return false
    }
    function process(objects, query) {
        for (var i=0;i<objects.length;i++) {
            var item=objects[i]
            if (typeof item.signal === "function" && item.command !== undefined &&
                (query ? item.command.length>1 && item.command[item.command.length-1] === "status" : item.command.length===0)) return item
        }
        throw new Error("test process not found")
    }
    Component.onCompleted: {
        for (var i=0;i<panel.data.length;i++) {
            var item=panel.data[i]
            if (item.interval===12000 || item.interval===30000) item.interval=250
        }
        queryProcess=process(panel.data,true)
        actionProcess=process(panel.data,false)
        if (SCENARIO.indexOf("privacy-")===0) {
            for (var j=0;j<widget.data.length;j++) {
                var child=widget.data[j]
                if (typeof child.signal==="function" && child.command.length===0) privacyProcess=child
                if (child.interval===8000) { child.interval=250; child.start() }
            }
            if (!privacyProcess) throw new Error("privacy process not found")
            widget.privacyBusy=true; widget.privacyFinished=false; widget.privacyReply=""; widget.privacyTimedOut=false
            privacyProcess.command=[Quickshell.env("HOME")+"/.local/bin/hyprveil", "privacy"]
            privacyProcess.running=true
        } else if (SCENARIO === "watch-overflow") {
            widget.focusPrivacy={state:"hidden"}
            widget.collectPrivacyWatch("x".repeat(131072))
        } else panel.open()
    }
    Timer {
        interval: 25; running: true; repeat: true
        onTriggered: {
            ticks++
            if (stage===0 && SCENARIO.indexOf("privacy-")===0 && !widget.privacyBusy) {
                if (privacyProcess.running || !widget.privacyFinished) throw new Error("privacy failure released a live child")
                if (SCENARIO!=="privacy-start" && (!widget.privacyTimedOut || widget.privacyReply.length!==0 && SCENARIO==="privacy-overflow"))
                    throw new Error("privacy timeout or output bound lost")
                stage=3
            } else if (stage===0 && SCENARIO === "watch-overflow") {
                if (widget.privacyWatchBuffer!=="" || widget.focusPrivacy.state!=="unknown") throw new Error("watch overflow not bounded")
                stage=3
            } else if (stage===0 && SCENARIO.indexOf("hyprpm-")===0 && !panel.querying && panel.current.known) {
                if (panel.current.loadSupported || panel.current.persistenceSupported) throw new Error("Hyprpm ownership lost")
                if (SCENARIO === "hyprpm-unloaded") {
                    if (panel.current.loaded || JSON.stringify(panel.options()) !== '["refresh"]' || !hasText(panel,panel.tr("hyprpm_enable_hint")))
                        throw new Error("unloaded Hyprpm core exposed legacy loading")
                    panel.act("start"); panel.act("enable")
                    if(panel.acting) throw new Error("Hyprpm loading executed through legacy action")
                } else if (!panel.current.loaded || !hasText(panel,panel.tr("runtime_only"))) throw new Error("runtime-only settings not explained")
                stage=3
            } else if (stage===0 && SCENARIO.indexOf("action-")===0 && !panel.querying && panel.current.known) {
                if (SCENARIO === "action-start") {
                    // Keep status valid, but select a missing action executable.
                    panel.beginAction("spoiler", ["spoiler"])
                    actionProcess.command=["/path/that/does/not/exist"]
                    actionProcess.signal(9)
                    stage=2
                } else { panel.act("spoiler"); stage=1 }
            } else if (stage===1 && !panel.acting) {
                if (actionProcess.running) throw new Error("timeout released a live action child")
                if (panel.message !== panel.tr("controller_timeout")) throw new Error("action timeout lost")
                stage=3
            } else if (stage===2 && !panel.acting && !actionProcess.running) stage=3
            else if (stage===0 && SCENARIO.indexOf("query-")===0 && !panel.querying) {
                if (queryProcess.running) throw new Error("query failure released a live child")
                if (panel.current.known) throw new Error("bad query accepted")
                if (SCENARIO === "query-timeout" && panel.message !== panel.tr("query_timeout")) throw new Error("query timeout lost")
                if (panel.queryOut.length>32768) throw new Error("unbounded query retained")
                stage=3
            }
            if (stage===3) { console.log("HYPRVEIL_PROCESS_FAILURE_OK"); Qt.quit() }
            if (ticks>100) throw new Error("subprocess failure did not recover")
        }
    }
}
'''.replace("SCENARIO", json.dumps(scenario))
        # A separate tiny launcher fails exec without disturbing status lookup.
        if scenario == "action-start":
            qml = qml.replace('panel.beginAction("spoiler", ["spoiler"])\n                    actionProcess.command=["/path/that/does/not/exist"]\n                    actionProcess.signal(9)',
                              'actionProcess.command=["/path/that/does/not/exist"]; panel.acting=true; panel.actionFinished=false; actionProcess.running=true')
        (root / "shell.qml").write_text(qml)
        runtime = root / "runtime"
        runtime.mkdir(mode=0o700)
        environment = dict(os.environ, HOME=str(home), XDG_RUNTIME_DIR=str(runtime),
                           QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", QT_QPA_PLATFORMTHEME="", QT_STYLE_OVERRIDE="Fusion")
        for key in ("WAYLAND_DISPLAY", "DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "DBUS_SESSION_BUS_ADDRESS"):
            environment.pop(key, None)
        try:
            result = subprocess.run(["/usr/bin/quickshell", "--no-color", "--path", str(root)], env=environment,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=5)
            if result.returncode != 0 or "HYPRVEIL_PROCESS_FAILURE_OK" not in result.stdout:
                raise SystemExit(scenario + " failed:\n" + result.stdout)
            print("passed", scenario)
        finally:
            for pid in (home / "pids").read_text().splitlines() if (home / "pids").exists() else ():
                try:
                    if str(controller).encode() in Path("/proc", pid, "cmdline").read_bytes().split(b"\0"):
                        os.kill(int(pid), signal.SIGKILL)
                except (ProcessLookupError, FileNotFoundError):
                    pass
