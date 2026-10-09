pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import qs.Ui as Ui
import "State.js" as State
import "Appearance.js" as Appearance
import "Privacy.js" as Privacy
import "I18n.js" as I18n

Ui.Panel {
    id: root
    property string language: I18n.language(Qt.locale().name)
    function tr(key) { return I18n.text(key, language) }
    moduleName: "io.github.objlako.hyprveil"
    ipcTarget: "io.github.objlako.hyprveil"
    property Item anchorItem: null
    property var hostWidget: null
    readonly property var barIdentity: hostWidget || root
    readonly property color foreground: Color.popups.text
    readonly property string fontFamily: "Adwaita Sans"
    readonly property string controllerHelper: decodeURIComponent(Qt.resolvedUrl("panel-controller").toString().replace(/^file:\/\//, ""))
    property var controllerCommand: ["/usr/bin/python3", controllerHelper]
    property var current: State.unknown()
    property string message: ""
    property bool querying: false
    property bool acting: false
    readonly property bool busy: acting || !!(hostWidget && (hostWidget.privacyBusy || hostWidget.privacyDispatching))
    property bool queryManual: false
    property bool statusChecked: false
    property string queuedAction: ""
    property string tab: "hide"
    property var appearanceDraft: Appearance.defaults()
    property bool appearanceDirty: false
    property var appearanceEdits: ({})
    property int appearanceRevision: 0
    property bool appearanceSaveBlocked: false
    property string appearanceError: ""
    property var submittedFields: null
    property var submittedAppearance: null
    signal idleReady()
    property int cursor: 0
    property string actionName: ""
    property string pendingConfirmation: ""
    property string queryOut: ""
    property bool queryFinished: false
    property bool queryTimedOut: false
    property bool queryOverflow: false
    property int queryCode: -1
    property bool actionFinished: false
    property int actionCode: -1
    property bool actionTimedOut: false

    // Child processes cannot inherit shell hooks, Python injection paths or
    // dynamic-loader variables from Quickshell. Commands are argv arrays.
    readonly property var processEnvironment: {
        var env = { PATH: "/usr/bin:/bin", LANG: "C.UTF-8", PYTHONNOUSERSITE: "1" }
        var keep = ["HOME", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "HYPRLAND_INSTANCE_SIGNATURE"]
        for (var i = 0; i < keep.length; ++i) {
            var value = Quickshell.env(keep[i])
            if (value !== undefined && value !== null && String(value) !== "") env[keep[i]] = String(value)
        }
        return env
    }

    function refresh(manual, background) {
        if ((!opened && background !== true) || busy || querying) return
        querying = true
        queryManual = manual === true
        queryOut = ""
        queryFinished = false
        queryTimedOut = false
        queryOverflow = false
        queryCode = -1
        queryTimeout.restart()
        query.running = true
    }
    function finishQuery() {
        if (!querying || !queryFinished) return
        queryTimeout.stop()
        statusChecked = true
        var next = queryCode === 0 && !queryTimedOut && !queryOverflow ? State.parse(queryOut) : State.unknown()
        if (JSON.stringify(current) !== JSON.stringify(next)) current = next
        queryOut = ""
        querying = false
        queryManual = false
        if (queryTimedOut) message = root.tr("query_timeout")
        else if (!current.known) message = root.tr("status_unconfirmed")
        else if (pendingConfirmation !== "") {
            if (pendingConfirmation === "configure") {
                var confirmed = current.loaded && submittedFields !== null
                var fields = Object.keys(submittedFields || {})
                for (var i = 0; i < fields.length; ++i) {
                    if (current.appearance[fields[i]] !== submittedFields[fields[i]].value) confirmed = false
                }
                if (confirmed) {
                    var remaining = Object.assign({}, appearanceEdits)
                    for (var j = 0; j < fields.length; ++j) {
                        var key = fields[j]
                        // Only the exact edit that was sent is acknowledged.
                        // Newer values, including a quick change back, survive.
                        if (remaining[key] && remaining[key].revision === submittedFields[key].revision)
                            delete remaining[key]
                    }
                    appearanceEdits = remaining
                } else {
                    appearanceSaveBlocked = true
                    appearanceError = root.tr("appearance_unconfirmed")
                }
            } else if ((pendingConfirmation === "start" || pendingConfirmation === "enable") && current.loaded)
                message = root.tr("loaded")
            else if (pendingConfirmation === "reload-config" && current.loaded)
                message = appearanceDirty ? root.tr("lua_reloaded_dirty") : root.tr("lua_reloaded")
            else if (current.loaded && current.mode === pendingConfirmation)
                message = root.tr("setting_applied")
            else message = root.tr("state_changed")
        }
        if (!current.known && Object.keys(appearanceEdits).length) {
            appearanceSaveBlocked = true
            appearanceError = root.tr("appearance_unconfirmed")
        }
        if (current.known) {
            // Native/Lua changes to untouched fields remain authoritative.
            // Overlay only this editor's unconfirmed field values.
            var merged = Appearance.parse(current.appearance)
            var edits = Object.keys(appearanceEdits)
            for (var k = 0; k < edits.length; ++k) merged[edits[k]] = appearanceEdits[edits[k]].value
            if (!Appearance.equal(appearanceDraft, merged)) appearanceDraft = merged
        }
        appearanceDirty = Object.keys(appearanceEdits).length > 0
        pendingConfirmation = ""
        submittedFields = null
        submittedAppearance = null
        if (queuedAction !== "") {
            var action = queuedAction
            queuedAction = ""
            act(action, true)
        }
        idleReady()
        Qt.callLater(flushAppearance)
    }
    function collectQuery(chunk) {
        if (!querying || queryOverflow || queryTimedOut) return
        // Parse raw chunks: a missing newline must not create an unbounded
        // SplitParser or StdioCollector buffer in the shell process.
        if (queryOut.length + chunk.length > 32768) {
            queryOut = ""
            queryOverflow = true
            query.signal(9)
        } else queryOut += chunk
    }
    function act(action, alreadyRequested) {
        if ((!opened && alreadyRequested !== true) || !State.allowed(action, current)) return
        if (acting && actionName === "configure") { queuedAction = action; return }
        if (busy) return
        if (querying) { queuedAction = action; return }
        beginAction(action, [action])
    }
    function editAppearance(key, value) {
        var patch = {}; patch[key] = value
        editAppearancePatch(patch)
    }
    function editAppearancePatch(patch, force) {
        var next = Appearance.updateMany(appearanceDraft, patch)
        if (!next) return
        var fields = Object.keys(patch), changed = false
        if (!fields.length) return
        for (var i = 0; i < fields.length; ++i)
            if (next[fields[i]] !== appearanceDraft[fields[i]]) changed = true
        if (!changed && !force && !appearanceSaveBlocked) return
        var edits = Object.assign({}, appearanceEdits)
        appearanceRevision++
        for (var j = 0; j < fields.length; ++j) {
            var key = fields[j]
            if (force || appearanceSaveBlocked || next[key] !== appearanceDraft[key])
                edits[key] = {value: next[key], revision: appearanceRevision}
        }
        appearanceEdits = edits
        appearanceDraft = next
        appearanceDirty = true
        appearanceSaveBlocked = false
        appearanceError = ""
        message = ""
        appearanceAutosave.restart()
    }
    function applyAppearance(parameters) {
        // Retained for IPC/test callers; normal controls all use autosave.
        if (parameters) editAppearancePatch(parameters, true)
        appearanceAutosave.stop()
        flushAppearance()
    }
    function flushAppearance() {
        if (!appearanceDirty || appearanceSaveBlocked || busy || querying || submittedFields !== null || appearanceAutosave.running) return
        if (!current.known) { refresh(false, true); return }
        if (!current.loaded) {
            appearanceSaveBlocked = true
            appearanceError = root.tr("appearance_unconfirmed")
            return
        }
        if (!Object.keys(appearanceEdits).length) { appearanceDirty = false; return }
        submittedFields = Object.assign({}, appearanceEdits)
        submittedAppearance = Appearance.parse(appearanceDraft)
        beginAction("configure", Appearance.command(submittedAppearance, Object.keys(submittedFields)))
    }
    function resetAppearance() {
        editAppearancePatch(Appearance.defaults(), true)
        editor.syncColor()
    }
    function setTab(next) {
        if (["hide", "customize"].indexOf(next) < 0) return
        tab = next; cursor = 0; flick.contentY = 0
        if (tab === "customize") Qt.callLater(function() { editor.forceActiveFocus() })
    }
    function beginAction(action, args) {
        acting = true
        actionName = action
        pendingConfirmation = ""
        if (action !== "configure") message = ""
        // A query result is only a snapshot. Do not display it as proof while
        // a mode transition is in flight; a new status is required afterwards.
        if (action !== "configure") current = State.unknown()
        actionFinished = false
        actionTimedOut = false
        actionCode = -1
        actionProcess.command = controllerCommand.concat(args)
        actionTimeout.restart()
        actionProcess.running = true
    }
    function finishAction() {
        if (!acting || !actionFinished) return
        actionTimeout.stop()
        acting = false
        if (actionName === "configure" && (actionTimedOut || actionCode !== 0)) {
            appearanceSaveBlocked = true
            appearanceError = root.tr(actionTimedOut ? "controller_timeout" : "appearance_failed")
        } else if (actionTimedOut) message = root.tr("controller_timeout")
        else if (actionCode !== 0) message = actionName === "reload-config" ? root.tr("lua_failed")
            : root.tr("action_unconfirmed")
        else {
            pendingConfirmation = actionName
            if (actionName !== "configure") message = root.tr("command_checking")
        }
        Qt.callLater(function() { refresh(false, actionName === "configure") })
    }
    function options() {
        if (!current.known) return ["refresh"]
        return current.loaded ? ["spoiler", "omit", "black", "reset", "refresh", "reload-config", "customize"]
                              : current.loadSupported ? [current.enabled ? "start" : "enable", "refresh"] : ["refresh"]
    }
    function moveCursor(delta) {
        var list = options()
        cursor = (cursor + delta + list.length) % list.length
        Qt.callLater(scrollCursor)
    }
    function scrollCursor() {
        var action = options()[Math.min(cursor, options().length - 1)]
        var targets = { black: blackRow, omit: omitRow, spoiler: spoilerRow,
                        reset: resetButton, start: loadButton, enable: loadButton, refresh: refreshButton, "reload-config": reloadLuaButton, customize: customTab }
        var target = targets[action]
        if (!target) return
        var top = target.mapToItem(content, 0, 0).y
        var bottom = top + target.height
        if (top < flick.contentY) flick.contentY = top
        else if (bottom > flick.contentY + flick.height) flick.contentY = bottom - flick.height
        flick.contentY = Math.max(0, Math.min(flick.contentY, flick.contentHeight - flick.height))
    }
    function activateCursor() {
        var item = options()[Math.min(cursor, options().length - 1)]
        if (item === "refresh") { message = ""; refresh(true) }
        else if (item === "customize") setTab("customize")
        else if (item === "reset") act("omit")
        else act(item)
    }
    onOpenedChanged: {
        if (opened) {
            cursor = 0
            message = ""
            // Refresh only while the panel is visible. The bar tooltip names
            // its cached value as a last check, so closed-panel snapshots cannot
            // promise a live privacy state.
            Qt.callLater(function() { refresh(false) })
        } else {
            // A click already authorized these edits. Closing the popout does
            // not cancel its last value or require another open to confirm it.
            if (!editor.colorValid) editor.syncColor()
            appearanceAutosave.stop()
            Qt.callLater(flushAppearance)
        }
    }
    onBusyChanged: if (!busy) Qt.callLater(function() {
        if (submittedFields !== null || pendingConfirmation !== "") refresh(false, true)
        else flushAppearance()
    })

    Timer { interval: 2500; repeat: true; running: root.opened; onTriggered: root.refresh() }
    Timer { id: appearanceAutosave; interval: 120; onTriggered: root.flushAppearance() }
    Timer {
        id: queryTimeout
        interval: 12000
        onTriggered: {
            root.queryTimedOut = true
            root.queryOut = ""
            root.current = State.unknown()
            root.message = root.tr("query_timeout")
            root.queuedAction = ""
            // running=false sends SIGTERM and can leave a stuck child alive.
            // Retain ownership until its real exit; do not reuse this Process.
            query.signal(9)
        }
    }
    Timer {
        id: actionTimeout
        interval: 30000
        onTriggered: {
            root.actionTimedOut = true
            actionProcess.signal(9)
        }
    }
    Process {
        id: query
        command: root.controllerCommand.concat(["status"])
        clearEnvironment: true
        environment: root.processEnvironment
        stdout: SplitParser { splitMarker: ""; onRead: function(chunk) { root.collectQuery(chunk) } }
        // Consume diagnostics without logging private installation paths.
        stderr: SplitParser { splitMarker: ""; onRead: function(chunk) {} }
        onExited: function(code) {
            root.queryCode = code
            root.queryFinished = true
            root.finishQuery()
        }
        onRunningChanged: {
            // FailedToStart has no exited signal in Quickshell.
            if (!running && root.querying && !root.queryFinished) {
                root.queryCode = -1
                root.queryFinished = true
                root.finishQuery()
            }
        }
    }
    Process {
        id: actionProcess
        clearEnvironment: true
        environment: root.processEnvironment
        stdout: SplitParser { splitMarker: ""; onRead: function(chunk) {} }
        stderr: SplitParser { splitMarker: ""; onRead: function(chunk) {} }
        onExited: function(code) {
            root.actionCode = code
            root.actionFinished = true
            root.finishAction()
        }
        onRunningChanged: {
            if (!running && root.acting && !root.actionFinished) {
                root.actionCode = -1
                root.actionFinished = true
                root.finishAction()
            }
        }
    }

    KeyboardPanel {
        id: popup
        anchorItem: root.anchorItem
        owner: root.barIdentity
        bar: root.bar
        open: root.opened
        focusTarget: keys
        contentWidth: fittedContentWidth(Style.space(450))
        contentHeight: fittedContentHeight(content.implicitHeight)

        PanelKeyCatcher {
            id: keys
            anchors.fill: parent
            blocked: root.tab === "customize"
            onCloseRequested: root.close()
            onTabRequested: function(direction) { root.moveCursor(direction) }
            onMoveRequested: function(dx, dy) { root.moveCursor(dy || dx) }
            onActivateRequested: root.activateCursor()
            onTextKey: function(text) {
                if (text === "r") { root.message = ""; root.refresh(true) }
                else if (text === "c") root.setTab("customize")
            }

            Flickable {
                id: flick
                anchors.fill: parent
                contentHeight: content.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                Column {
                    id: content
                    width: parent.width
                    spacing: Style.space(12)

                    Item {
                        width: parent.width
                        implicitHeight: Style.space(60)
                        Rectangle {
                            id: heroMark
                            width: Style.space(38)
                            height: width
                            anchors.verticalCenter: parent.verticalCenter
                            radius: Style.space(11)
                            color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.035)
                            border.width: 1
                            border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.065)
                            Eye { width: Style.space(23); height: width; anchors.centerIn: parent; ink: root.foreground; opacity: 0.8 }
                        }
                        Column {
                            anchors.left: heroMark.right
                            anchors.leftMargin: Style.space(13)
                            anchors.right: statusPill.left
                            anchors.rightMargin: Style.space(10)
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: Style.space(4)
                            Text {
                                width: parent.width
                                text: root.tr("privacy")
                                textFormat: Text.PlainText
                                color: root.foreground
                                font.family: root.fontFamily
                                font.pixelSize: Style.space(20)
                                font.weight: Font.Medium
                                elide: Text.ElideRight
                            }
                            Text {
                                width: parent.width
                                text: root.tr("capture_subtitle")
                                textFormat: Text.PlainText
                                color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.43)
                                font.family: root.fontFamily
                                font.pixelSize: Style.space(11)
                                elide: Text.ElideRight
                            }
                        }
                        Rectangle {
                            id: statusPill
                            width: Style.space(90)
                            height: Style.space(25)
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            radius: height / 2
                            color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.025)
                            border.width: 1
                            border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.08)
                            Text {
                                id: pillText
                                anchors.centerIn: parent
                                text: root.acting && root.actionName !== "configure" ? root.tr("changing") : root.querying && root.queryManual ? root.tr("checking_short") : !root.current.known ? (!root.statusChecked && root.querying ? root.tr("checking_short") : root.tr("offline"))
                                    : root.current.mode === "spoiler" ? root.tr("spoiler") : root.current.mode === "omit" ? root.tr("hidden_short")
                                    : root.current.mode === "black" ? root.tr("mask_short") : root.current.loaded ? root.tr("image_short") : root.tr("unloaded_short")
                                textFormat: Text.PlainText
                                color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.62)
                                font.family: root.fontFamily
                                font.pixelSize: Style.space(10)
                            }
                        }
                    }
                    WindowPrivacy {
                        language: root.language
                        privacy: root.hostWidget ? root.hostWidget.focusPrivacy : Privacy.unknown()
                        busy: !!(root.hostWidget && root.hostWidget.privacyBusy)
                        fontFamily: root.fontFamily
                        onToggleRequested: if (root.hostWidget) root.hostWidget.togglePrivacy()
                    }
                    Column {
                        width: parent.width
                        spacing: Style.space(8)
                        visible: !root.current.known && !root.acting
                        Text {
                            width: parent.width
                            text: root.tr("prerequisite")
                            textFormat: Text.PlainText
                            color: Color.muted
                            font.family: root.fontFamily
                            font.pixelSize: Style.space(11)
                            wrapMode: Text.WordWrap
                        }
                        Button {
                            text: root.tr("setup_guide")
                            fontFamily: root.fontFamily
                            fontSize: Style.space(11)
                            focusable: true
                            onClicked: Qt.openUrlExternally("https://github.com/OBJLAKO/omarchy-hyprveil#install")
                        }
                    }
                    Row {
                        width: parent.width; spacing: Style.space(6)
                        Button {
                            width: (parent.width - parent.spacing) / 2
                            text: root.tr("hiding"); selected: root.tab === "hide"; focusable: true
                            fontFamily: root.fontFamily; fontSize: Style.space(12)
                            onClicked: root.setTab("hide")
                        }
                        Button {
                            id: customTab
                            width: (parent.width - parent.spacing) / 2
                            text: root.tr("appearance") + (root.appearanceDirty ? " ·" : ""); selected: root.tab === "customize"; focusable: true
                            fontFamily: root.fontFamily; fontSize: Style.space(12)
                            hasCursor: root.cursor === root.options().indexOf("customize") && root.tab === "hide"
                            onClicked: root.setTab("customize")
                        }
                    }
                    Text {
                        width: parent.width
                        visible: root.current.spoilerFallback
                        text: root.acting && root.actionName !== "configure" ? root.tr("changing_style") : root.querying && root.queryManual ? root.tr("checking") : State.label(root.current.mode, root.current.spoilerFallback, root.language)
                        textFormat: Text.PlainText
                        color: root.current.spoilerFallback ? Color.urgent : root.current.known ? root.foreground : Color.muted
                        font.family: root.fontFamily
                        font.pixelSize: Style.font.bodySmall
                        wrapMode: Text.WordWrap
                    }
                    Column {
                    width: parent.width
                    spacing: Style.space(12)
                    visible: root.tab === "hide"
                    PanelSectionHeader { text: root.tr("hidden_style"); foreground: root.foreground; fontFamily: root.fontFamily; fontSize: Style.space(11) }
                    StyleRow {
                        id: spoilerRow
                        title: root.tr("spoiler")
                        detail: root.tr("spoiler_detail")
                        mode: "spoiler"
                        appearance: root.current.appearance
                        animate: root.opened && root.tab === "hide"
                        selected: root.current.loaded && root.current.mode === mode
                        enabled: root.current.known && root.current.loaded && !root.busy
                        hasCursor: root.cursor === 0 && root.current.loaded
                        fontFamily: root.fontFamily
                        onHovered: root.cursor = 0
                        onPicked: root.act(mode)
                    }
                    StyleRow {
                        id: omitRow
                        title: root.tr("omit")
                        detail: root.tr("omit_detail")
                        mode: "omit"
                        selected: root.current.loaded && root.current.mode === mode
                        enabled: root.current.known && root.current.loaded && !root.busy
                        hasCursor: root.cursor === 1 && root.current.loaded
                        fontFamily: root.fontFamily
                        onHovered: root.cursor = 1
                        onPicked: root.act(mode)
                    }
                    StyleRow {
                        id: blackRow
                        title: root.tr("black")
                        detail: root.tr("black_detail")
                        mode: "black"
                        selected: root.current.loaded && root.current.mode === mode
                        enabled: root.current.known && root.current.loaded && !root.busy
                        hasCursor: root.cursor === 2 && root.current.loaded
                        fontFamily: root.fontFamily
                        onHovered: root.cursor = 2
                        onPicked: root.act(mode)
                    }
                    Text {
                        width: parent.width
                        text: root.tr("desktop_unchanged")
                        textFormat: Text.PlainText
                        color: Color.muted
                        font.family: root.fontFamily
                        font.pixelSize: Style.space(11)
                        wrapMode: Text.WordWrap
                    }
                    Button {
                        id: loadButton
                        visible: root.current.known && !root.current.loaded && root.current.loadSupported
                        width: parent.width
                        text: root.current.enabled ? root.tr("load") : root.tr("enable")
                        enabled: !root.busy
                        bordered: true
                        foreground: root.foreground
                        background: Color.popups.background
                        fontFamily: root.fontFamily
                        hasCursor: root.cursor === 0
                        onHovered: function(isHovered) { if (isHovered) root.cursor = 0 }
                        onClicked: root.act(root.current.enabled ? "start" : "enable")
                    }
                    Button {
                        width: parent.width
                        visible: root.current.known && !root.current.loaded && !root.current.loadSupported && !!root.hostWidget
                        text: root.tr("setup_native")
                        enabled: !root.busy
                        foreground: root.foreground
                        fontFamily: root.fontFamily
                        onClicked: root.hostWidget.setup()
                    }
                    Text {
                        width: parent.width
                        visible: root.current.known && !root.current.loaded && !root.current.loadSupported
                        text: root.tr("hyprpm_enable_hint")
                        textFormat: Text.PlainText; color: Color.muted
                        font.family: root.fontFamily; font.pixelSize: Style.space(11)
                        wrapMode: Text.WordWrap
                    }
                    PanelSeparator { foreground: root.foreground; strength: 0.075 }
                    Row {
                        width: parent.width
                        spacing: Style.space(8)
                        Button {
                        id: resetButton
                        width: parent.width - refreshButton.width - parent.spacing
                        text: root.tr("reset_hiding")
                        enabled: root.current.known && root.current.loaded && !root.busy
                        leftAlign: true
                        foreground: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.7)
                        background: "transparent"
                        fontFamily: root.fontFamily
                        fontSize: Style.space(12)
                        hasCursor: root.cursor === 3 && root.current.loaded
                        onHovered: function(isHovered) { if (isHovered) root.cursor = 3 }
                        onClicked: root.act("omit")
                        }
                        Button {
                            id: refreshButton
                            width: Style.space(31)
                            text: "↻"
                            tooltipText: root.tr("refresh")
                            enabled: !root.busy
                            fontFamily: root.fontFamily
                            fontSize: Style.space(16)
                            foreground: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.55)
                            hasCursor: root.cursor === root.options().indexOf("refresh")
                            onHovered: function(isHovered) { if (isHovered) root.cursor = root.options().indexOf("refresh") }
                            onClicked: { root.message = ""; root.refresh(true) }
                        }
                    }
                    Text {
                        width: parent.width
                        text: root.tr("omit_note")
                        textFormat: Text.PlainText
                        color: Color.muted
                        font.family: root.fontFamily
                        font.pixelSize: Style.space(11)
                        wrapMode: Text.WordWrap
                    }
                    }
                    AppearanceEditor {
                        language: root.language
                        id: editor
                        width: parent.width
                        visible: root.tab === "customize"
                        draft: root.appearanceDraft
                        mode: root.current.mode
                        dirty: root.appearanceDirty
                        busy: (root.acting && root.actionName !== "configure") || !root.current.known || !root.current.loaded
                        saving: (root.acting && root.actionName === "configure") || root.submittedFields !== null
                        enabled: (!root.acting || root.actionName === "configure") && root.current.known && root.current.loaded
                        animate: root.opened && visible
                        fontFamily: root.fontFamily
                        onEdited: function(key, value) { root.editAppearance(key, value) }
                        onEditedPatch: function(patch) { root.editAppearancePatch(patch) }
                        onVariantPicked: function(variant) { root.editAppearance("variant", variant) }
                        onColorValidChanged: if (colorValid) Qt.callLater(root.flushAppearance)
                        onResetRequested: root.resetAppearance()
                        onCloseRequested: root.close()
                    }
                    Row {
                        width: parent.width
                        visible: root.current.known && root.current.loaded
                        spacing: Style.space(10)
                        Text {
                            width: parent.width - reloadLuaButton.width - parent.spacing
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.tr("lua_settings")
                            textFormat: Text.PlainText
                            color: Color.muted
                            font.family: root.fontFamily
                            font.pixelSize: Style.space(11)
                            elide: Text.ElideRight
                        }
                        Button {
                            id: reloadLuaButton
                            width: Style.space(132)
                            text: root.tr("reload_lua")
                            tooltipText: root.tr("reload_lua_hint")
                            enabled: !root.busy
                            fontFamily: root.fontFamily
                            fontSize: Style.space(11)
                            foreground: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.65)
                            hasCursor: root.cursor === root.options().indexOf("reload-config") && root.tab === "hide"
                            onHovered: function(isHovered) { if (isHovered && root.tab === "hide") root.cursor = root.options().indexOf("reload-config") }
                            onClicked: root.act("reload-config")
                        }
                    }
                    Text {
                        width: parent.width
                        visible: root.current.known && root.current.loaded && !root.current.persistenceSupported
                        text: root.tr("runtime_only")
                        textFormat: Text.PlainText; color: Color.muted
                        font.family: root.fontFamily; font.pixelSize: Style.space(11)
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        width: parent.width
                        height: Style.space(34)
                        text: root.appearanceError || root.message
                        textFormat: Text.PlainText
                        color: root.current.known ? root.foreground : Color.urgent
                        font.family: root.fontFamily
                        font.pixelSize: Style.font.caption
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                }
            }
        }
    }
}
