import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import qs.Ui as Ui
import "." as Hyprveil
import "State.js" as State
import "Privacy.js" as Privacy
import "I18n.js" as I18n

Ui.BarWidget {
    id: root
    readonly property string language: I18n.selectLanguage(setting("language", "auto"), Qt.locale().name)
    function tr(key) { return I18n.text(key, language) }
    moduleName: "io.github.objlako.hyprveil"
    readonly property bool opened: panel.opened
    readonly property bool popoutSwitchClosing: panel.popoutSwitchClosing
    readonly property real openPanelIndicatorWidth: Style.space(19)
    readonly property string currentSignature: String(Quickshell.env("HYPRLAND_INSTANCE_SIGNATURE") || "")
    readonly property bool signatureValid: Privacy.validSignature(currentSignature)
    property bool privacyBusy: false
    readonly property bool privacyDispatching: privacyProcess.running
    property bool privacyConfirmed: false
    property bool privacyReplySeen: false
    property bool privacyReplyGood: false
    property var focusPrivacy: Privacy.unknown()
    property var privacyTarget: Privacy.unknown()
    property bool privacyQueued: false
    property var privacyQueuedTarget: Privacy.unknown()
    readonly property string privacyWatcherPath: decodeURIComponent(Qt.resolvedUrl("privacy-watch").toString().replace(/^file:\/\//, ""))
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    function open() { panel.open() }
    function close() { panel.close() }
    function toggle() { panel.toggle() }
    function closeForPopoutSwitch() { panel.closeForPopoutSwitch() }
    function togglePrivacy() {
        if (!Privacy.allowed(currentSignature, privacyBusy || privacyDispatching, panel.busy, focusPrivacy)) return
        if (panel.querying) { privacyQueuedTarget = Privacy.normalized(focusPrivacy); privacyQueued = true; return }
        privacyBusy = true
        privacyTarget = Privacy.normalized(focusPrivacy)
        privacyReplySeen = false
        privacyReplyGood = false
        privacyConfirmed = false
        privacyTimeout.restart()
        privacyProcess.running = true
    }
    function consumePrivacy(line) {
        var next = Privacy.parse(line)
        if (JSON.stringify(next) !== JSON.stringify(focusPrivacy)) focusPrivacy = next
        if (privacyQueued && next.state !== "unknown" && (next.address !== privacyQueuedTarget.address || next.stable_id !== privacyQueuedTarget.stable_id || next.state !== privacyQueuedTarget.state)) {
            privacyQueued = false
            privacyQueuedTarget = Privacy.unknown()
            panel.message = root.tr("target_changed")
        }
        if (privacyBusy && next.address === privacyTarget.address && next.stable_id === privacyTarget.stable_id && next.state !== privacyTarget.state &&
            (next.state === "hidden" || next.state === "visible")) {
            privacyConfirmed = true
            if (!privacyDispatching) { privacyTimeout.stop(); privacyBusy = false }
        } else if (privacyBusy && next.state !== "unknown" && (next.address !== privacyTarget.address || next.stable_id !== privacyTarget.stable_id)) {
            privacyTimeout.stop()
            privacyBusy = false
            panel.message = root.tr("focus_changed")
        }
    }
    Connections {
        target: panel
        function onIdleReady() {
            if (root.privacyQueued && !panel.busy && !panel.querying) {
                root.privacyQueued = false
                if (root.focusPrivacy.address === root.privacyQueuedTarget.address && root.focusPrivacy.stable_id === root.privacyQueuedTarget.stable_id && root.focusPrivacy.state === root.privacyQueuedTarget.state)
                    root.togglePrivacy()
                else panel.message = root.tr("target_changed")
                root.privacyQueuedTarget = Privacy.unknown()
            }
        }
    }
    Process {
        id: privacyWatcher
        command: ["/usr/bin/python3", root.privacyWatcherPath, "watch"]
        clearEnvironment: true
        environment: panel.processEnvironment
        running: true
        stdout: SplitParser { onRead: function(line) { root.consumePrivacy(line) } }
        stderr: SplitParser { onRead: function(line) {} }
        onExited: { root.focusPrivacy = Privacy.unknown(); watcherReconnect.restart() }
    }
    Timer { id: watcherReconnect; interval: 1500; onTriggered: privacyWatcher.running = true }

    Process {
        id: privacyProcess
        // Reject focus changes and recycled addresses inside the compositor,
        // then apply the explicit visible/hidden choice through the public
        // native setter. No user Lua helper or private module is required.
        command: Privacy.command(root.currentSignature, root.privacyTarget)
        clearEnvironment: true
        environment: panel.processEnvironment
        stdout: SplitParser {
            onRead: function(line) {
                if (String(line).trim() === "") return
                root.privacyReplyGood = !root.privacyReplySeen && String(line).trim() === "ok"
                root.privacyReplySeen = true
            }
        }
        stderr: SplitParser { onRead: function(line) {} }
        onExited: function(code) {
            privacyTimeout.stop()
            if (code !== 0 || !root.privacyReplyGood) {
                root.privacyBusy = false
                panel.message = root.tr("privacy_dispatch_failed")
                panel.refresh(false)
            } else if (root.privacyConfirmed) root.privacyBusy = false
            else if (root.privacyBusy) privacyTimeout.restart()
        }
    }
    Timer {
        id: privacyTimeout
        interval: 8000
        onTriggered: {
            privacyProcess.running = false
            root.privacyBusy = false
            panel.message = root.tr("privacy_unconfirmed")
        }
    }

    Hyprveil.Panel {
        language: root.language
        id: panel
        bar: root.bar
        settings: root.settings
        anchorItem: button
        hostWidget: root
    }
    WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        labelVisible: false
        hasVisualContent: true
        fixedWidth: root.vertical ? root.barSize : Style.space(30)
        dimmed: root.privacyBusy
        tooltipText: "Hyprveil · " + (root.focusPrivacy.state === "hidden" ? root.tr("tooltip_hidden")
                : root.focusPrivacy.state === "visible" ? root.tr("tooltip_visible") : root.focusPrivacy.state === "none" ? root.tr("tooltip_none") : root.tr("tooltip_unknown"))
            + (root.focusPrivacy.inherited ? root.tr("tooltip_inherited") : "")
            + (panel.current.known ? root.tr("last_check") + State.label(panel.current.mode, panel.current.spoilerFallback, root.language) : "")
            + root.tr("left_hint")
            + root.tr("right_hint")
        onPressed: function(mouseButton) {
            if (mouseButton === Qt.RightButton) root.toggle()
            else if (mouseButton === Qt.LeftButton || mouseButton === Qt.MiddleButton) root.togglePrivacy()
        }
        Eye {
            anchors.centerIn: parent
            width: Style.space(19)
            height: width
            ink: root.focusPrivacy.state === "hidden" ? Color.accent : Color.muted
            crossed: root.focusPrivacy.state === "hidden"
            uncertain: root.focusPrivacy.state === "unknown"
            opacity: 0.9
        }
        Rectangle {
            anchors.right: parent.right
            anchors.rightMargin: Style.space(4)
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Style.space(6)
            width: Style.space(2)
            height: width
            radius: width / 2
            color: Color.accent
            opacity: 0.42
            visible: panel.current.known && panel.current.loaded && panel.current.mode === "spoiler"
        }
    }
}
