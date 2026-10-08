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

Ui.Panel {
    id: root
    moduleName: "sky.hyprveil"
    ipcTarget: "sky.hyprveil"
    property Item anchorItem: null
    property var hostWidget: null
    readonly property var barIdentity: hostWidget || root
    readonly property color foreground: Color.popups.text
    readonly property string fontFamily: "Adwaita Sans"
    readonly property string controllerPath: Quickshell.env("HOME") + "/.local/bin/hyprveil"
    property var current: State.unknown()
    property string message: ""
    property bool querying: false
    property bool acting: false
    readonly property bool busy: acting || !!(hostWidget && (hostWidget.privacyBusy || hostWidget.privacyDispatching))
    property bool queryManual: false
    property string queuedAction: ""
    property var queuedAppearance: null
    property string tab: "hide"
    property var appearanceDraft: Appearance.defaults()
    property bool appearanceDirty: false
    property var submittedAppearance: null
    signal idleReady()
    property int cursor: 0
    property string actionName: ""
    property string pendingConfirmation: ""
    property string queryOut: ""
    property bool queryFinished: false
    property bool queryStdoutFinished: false
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

    function refresh(manual) {
        if (!opened || busy || querying) return
        querying = true
        queryManual = manual === true
        queryOut = ""
        queryFinished = false
        queryStdoutFinished = false
        queryCode = -1
        queryTimeout.restart()
        query.running = true
    }
    function finishQuery() {
        if (!querying || !queryFinished || !queryStdoutFinished) return
        queryTimeout.stop()
        var next = queryCode === 0 ? State.parse(queryOut) : State.unknown()
        if (JSON.stringify(current) !== JSON.stringify(next)) current = next
        queryOut = ""
        querying = false
        queryManual = false
        if (!current.known) message = "Не удалось подтвердить состояние. Обновите проверку."
        else if (pendingConfirmation !== "") {
            if (pendingConfirmation === "configure") {
                if (Appearance.equal(current.appearance, submittedAppearance)) {
                    if (Appearance.equal(appearanceDraft, submittedAppearance) && editor.colorValid) {
                        appearanceDraft = Appearance.parse(current.appearance)
                        appearanceDirty = false
                        editor.syncColor()
                        message = "Оформление применено."
                    } else {
                        appearanceDirty = true
                        message = "Оформление применено. Новые изменения ещё не применены."
                    }
                } else message = "Оформление не подтверждено. Изменения сохранены в предпросмотре."
            } else if ((pendingConfirmation === "start" || pendingConfirmation === "enable") && current.loaded)
                message = "Hyprveil загружен."
            else if (pendingConfirmation === "reload-config" && current.loaded)
                message = appearanceDirty ? "Lua перечитана. Изменения в черновике ещё не применены." : "Lua перечитана. Текущие настройки показаны."
            else if (current.loaded && current.mode === pendingConfirmation)
                message = "Настройка применена."
            else message = "Состояние изменилось после команды. Текущий стиль показан выше."
        }
        if (current.known && !appearanceDirty && !Appearance.equal(appearanceDraft, current.appearance)) {
            appearanceDraft = Appearance.parse(current.appearance)
            editor.syncColor()
        }
        pendingConfirmation = ""
        submittedAppearance = null
        if (queuedAction !== "") {
            var action = queuedAction, parameters = queuedAppearance
            queuedAction = ""; queuedAppearance = null
            if (action === "configure") applyAppearance(parameters)
            else act(action)
        }
        idleReady()
    }
    function act(action) {
        if (!opened || busy || !State.allowed(action, current)) return
        if (querying) { queuedAction = action; queuedAppearance = null; return }
        beginAction(action, [action])
    }
    function editAppearance(key, value) {
        if (acting) return
        var next = Appearance.update(appearanceDraft, key, value)
        if (!next) return
        appearanceDraft = next
        appearanceDirty = !current.known || !Appearance.equal(next, current.appearance)
    }
    function applyAppearance(parameters) {
        var p = Appearance.parse(parameters || appearanceDraft)
        if (!opened || busy || !current.known || !current.loaded || !p || (!parameters && !editor.colorValid)) return
        if (querying) { queuedAction = "configure"; queuedAppearance = p; return }
        submittedAppearance = p
        beginAction("configure", Appearance.command(p))
    }
    function resetAppearance() {
        appearanceDraft = Appearance.defaults()
        appearanceDirty = !current.known || !Appearance.equal(appearanceDraft, current.appearance)
        editor.syncColor()
        applyAppearance(appearanceDraft)
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
        message = ""
        // A query result is only a snapshot. Do not display it as proof while
        // a mode transition is in flight; a new status is required afterwards.
        current = State.unknown()
        actionFinished = false
        actionTimedOut = false
        actionCode = -1
        actionProcess.command = [controllerPath].concat(args)
        actionTimeout.restart()
        actionProcess.running = true
    }
    function finishAction() {
        if (!acting || !actionFinished) return
        actionTimeout.stop()
        acting = false
        if (actionTimedOut) message = "Контроллер не ответил вовремя. Состояние требует новой проверки."
        else if (actionCode !== 0) message = actionName === "configure"
            ? "Не удалось применить оформление. Проверьте конфигурацию Lua."
            : actionName === "reload-config" ? "Не удалось перечитать Lua. Проверьте конфигурацию Hyprland."
            : "Переключение не подтверждено. Проверьте состояние или журнал контроллера."
        else {
            pendingConfirmation = actionName
            message = "Команда выполнена. Проверяем состояние…"
        }
        Qt.callLater(function() { refresh(false) })
    }
    function options() {
        if (!current.known) return ["refresh"]
        return current.loaded ? ["spoiler", "omit", "black", "reset", "refresh", "reload-config", "customize"]
                              : [current.enabled ? "start" : "enable", "refresh"]
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
        }
    }

    Timer { interval: 2500; repeat: true; running: root.opened; onTriggered: root.refresh() }
    Timer {
        id: queryTimeout
        interval: 12000
        onTriggered: {
            query.running = false
            root.querying = false
            root.queryManual = false
            root.queryOut = ""
            root.current = State.unknown()
            root.message = "Проверка не ответила вовремя. Повторите её."
            root.queuedAction = ""; root.queuedAppearance = null
            root.idleReady()
        }
    }
    Timer {
        id: actionTimeout
        interval: 30000
        onTriggered: {
            root.actionTimedOut = true
            actionProcess.running = false
            root.actionFinished = true
            root.finishAction()
        }
    }
    Process {
        id: query
        command: [root.controllerPath, "status"]
        clearEnvironment: true
        environment: root.processEnvironment
        stdout: StdioCollector {
            waitForEnd: true
            onStreamFinished: {
                root.queryOut = text
                root.queryStdoutFinished = true
                root.finishQuery()
            }
        }
        // Consume diagnostics without logging private installation paths.
        stderr: SplitParser { onRead: function(line) {} }
        onExited: function(code) {
            root.queryCode = code
            root.queryFinished = true
            root.finishQuery()
        }
    }
    Process {
        id: actionProcess
        clearEnvironment: true
        environment: root.processEnvironment
        stdout: SplitParser { onRead: function(line) {} }
        stderr: SplitParser { onRead: function(line) {} }
        onExited: function(code) {
            root.actionCode = code
            root.actionFinished = true
            root.finishAction()
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
                                text: "Приватность"
                                textFormat: Text.PlainText
                                color: root.foreground
                                font.family: root.fontFamily
                                font.pixelSize: Style.space(20)
                                font.weight: Font.Medium
                                elide: Text.ElideRight
                            }
                            Text {
                                width: parent.width
                                text: "Hyprveil · захват экрана"
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
                                text: root.acting ? "Смена…" : root.querying && root.queryManual ? "Проверка" : !root.current.known ? (root.querying ? "Проверка" : "Нет связи")
                                    : root.current.mode === "spoiler" ? "Спойлер" : root.current.mode === "omit" ? "Скрыто"
                                    : root.current.mode === "black" ? "Маска" : root.current.loaded ? "Картинка" : "Не загружен"
                                textFormat: Text.PlainText
                                color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.62)
                                font.family: root.fontFamily
                                font.pixelSize: Style.space(10)
                            }
                        }
                    }
                    WindowPrivacy {
                        privacy: root.hostWidget ? root.hostWidget.focusPrivacy : Privacy.unknown()
                        busy: !!(root.hostWidget && root.hostWidget.privacyBusy)
                        fontFamily: root.fontFamily
                        onToggleRequested: if (root.hostWidget) root.hostWidget.togglePrivacy()
                    }
                    Row {
                        width: parent.width; spacing: Style.space(6)
                        Button {
                            width: (parent.width - parent.spacing) / 2
                            text: "Скрытие"; selected: root.tab === "hide"; focusable: true
                            fontFamily: root.fontFamily; fontSize: Style.space(12)
                            onClicked: root.setTab("hide")
                        }
                        Button {
                            id: customTab
                            width: (parent.width - parent.spacing) / 2
                            text: "Оформление" + (root.appearanceDirty ? " ·" : ""); selected: root.tab === "customize"; focusable: true
                            fontFamily: root.fontFamily; fontSize: Style.space(12)
                            hasCursor: root.cursor === root.options().indexOf("customize") && root.tab === "hide"
                            onClicked: root.setTab("customize")
                        }
                    }
                    Text {
                        width: parent.width
                        visible: root.current.spoilerFallback
                        text: root.acting ? "Переключаем стиль…" : root.querying && root.queryManual ? "Проверяем состояние…" : State.label(root.current.mode, root.current.spoilerFallback)
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
                    PanelSectionHeader { text: "Вид скрытого окна"; foreground: root.foreground; fontFamily: root.fontFamily; fontSize: Style.space(11) }
                    StyleRow {
                        id: spoilerRow
                        title: "Спойлер"
                        detail: "Мягкое мерцание на тёмной поверхности"
                        mode: "spoiler"
                        appearance: root.current.appearance
                        animate: root.opened
                        selected: root.current.loaded && root.current.mode === mode
                        enabled: root.current.known && root.current.loaded && !root.busy
                        hasCursor: root.cursor === 0 && root.current.loaded
                        fontFamily: root.fontFamily
                        onHovered: root.cursor = 0
                        onPicked: root.act(mode)
                    }
                    StyleRow {
                        id: omitRow
                        title: "Полностью скрыть"
                        detail: "Окно полностью исключается из захвата"
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
                        title: "Обычная маска"
                        detail: "Ровная чёрная заливка"
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
                        text: "На вашем экране окна выглядят как прежде."
                        textFormat: Text.PlainText
                        color: Color.muted
                        font.family: root.fontFamily
                        font.pixelSize: Style.space(11)
                        wrapMode: Text.WordWrap
                    }
                    Button {
                        id: loadButton
                        visible: root.current.known && !root.current.loaded
                        width: parent.width
                        text: root.current.enabled ? "Загрузить Hyprveil" : "Включить Hyprveil"
                        enabled: !root.busy
                        bordered: true
                        foreground: root.foreground
                        background: Color.popups.background
                        fontFamily: root.fontFamily
                        hasCursor: root.cursor === 0
                        onHovered: function(isHovered) { if (isHovered) root.cursor = 0 }
                        onClicked: root.act(root.current.enabled ? "start" : "enable")
                    }
                    PanelSeparator { foreground: root.foreground; strength: 0.075 }
                    Row {
                        width: parent.width
                        spacing: Style.space(8)
                        Button {
                        id: resetButton
                        width: parent.width - refreshButton.width - parent.spacing
                        text: "Вернуть исходное скрытие"
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
                            tooltipText: "Обновить состояние"
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
                        text: "Окна полностью исключаются из захвата."
                        textFormat: Text.PlainText
                        color: Color.muted
                        font.family: root.fontFamily
                        font.pixelSize: Style.space(11)
                        wrapMode: Text.WordWrap
                    }
                    }
                    AppearanceEditor {
                        id: editor
                        width: parent.width
                        visible: root.tab === "customize"
                        draft: root.appearanceDraft
                        mode: root.current.mode
                        dirty: root.appearanceDirty
                        busy: root.busy || !root.current.known || !root.current.loaded
                        enabled: !root.acting && root.current.known && root.current.loaded && !(root.hostWidget && root.hostWidget.privacyBusy)
                        animate: root.opened && visible
                        fontFamily: root.fontFamily
                        onEdited: function(key, value) { root.editAppearance(key, value) }
                        onVariantPicked: function(variant) { root.editAppearance("variant", variant); root.applyAppearance() }
                        onInteractionStarted: root.appearanceDirty = true
                        onApplyRequested: root.applyAppearance()
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
                            text: "Настройки Hyprland · Lua"
                            textFormat: Text.PlainText
                            color: Color.muted
                            font.family: root.fontFamily
                            font.pixelSize: Style.space(11)
                            elide: Text.ElideRight
                        }
                        Button {
                            id: reloadLuaButton
                            width: Style.space(132)
                            text: "Перечитать Lua"
                            tooltipText: "Применить изменения из ~/.config/hypr/hyprveil-settings.lua\nЧерновик оформления сохранится."
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
                        height: Style.space(34)
                        text: root.message
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
