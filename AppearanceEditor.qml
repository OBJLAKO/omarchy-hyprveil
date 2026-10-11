pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Ui
import "Appearance.js" as Appearance
import "I18n.js" as I18n

Column {
    id: root
    property string language: I18n.language(Qt.locale().name)
    function tr(key) { return I18n.text(key, language) }
    property var draft: Appearance.defaults()
    property bool dirty: false
    property bool busy: false
    property bool saving: false
    property bool animate: false
    property bool advanced: false
    property bool assetsSupported: false
    property string mode: "spoiler"
    property bool customIconEditor: false
    property color foreground: Color.popups.text
    property string fontFamily: "Adwaita Sans"
    readonly property bool colorValid: hex.acceptableInput
    readonly property bool pathsValid: Appearance.validPath(shaderPath.text, true) && Appearance.validPath(iconPath.text, false)
    signal edited(string key, var value)
    signal editedPatch(var patch)
    signal variantPicked(string variant)
    signal builtinIconPicked(string icon)
    signal resetRequested()
    signal closeRequested()
    function syncColor() { hex.text = draft.color }
    function commitPaths() { if (assetsSupported) { shaderPath.commit(); iconPath.commit() } }
    function pickBuiltin(variant) {
        shaderPath.discard("")
        editedPatch(assetsSupported ? {variant: variant, shader_path: ""} : {variant: variant})
    }
    onDraftChanged: {
        if (!hex.activeFocus) syncColor()
    }
    Keys.onEscapePressed: closeRequested()
    spacing: Style.space(12)

    component LocalPath: TextField {
        id: pathField
        property string savedValue: ""
        property bool shader: false
        property bool changedByUser: false
        signal committed(string path)
        maximumLength: 4096
        font.family: root.fontFamily; font.pixelSize: Style.space(11)
        foreground: changedByUser && !Appearance.validPath(text, shader) ? Color.urgent : root.foreground
        text: savedValue
        onSavedValueChanged: if (!activeFocus && !changedByUser) text = savedValue
        onTextEdited: changedByUser = true
        function discard(value) { changedByUser = false; text = value }
        function commit() {
            if (!changedByUser) return
            if (Appearance.validPath(text, shader)) {
                changedByUser = false
                committed(text)
            }
        }
        onAccepted: commit()
        onEditingFinished: { commit(); if (!changedByUser) text = savedValue }
    }
    component Adjustment: Item {
        id: adjustment
        property string caption: ""
        property int value: 0
        property int minimum: 0
        property int maximum: 100
        property string suffix: "%"
        signal edited(int next)
        width: parent ? parent.width : 0
        implicitHeight: Style.space(39)
        activeFocusOnTab: true
        Keys.onLeftPressed: edited(Math.max(minimum, value - 1))
        Keys.onRightPressed: edited(Math.min(maximum, value + 1))
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Home) { edited(minimum); event.accepted = true }
            else if (event.key === Qt.Key_End) { edited(maximum); event.accepted = true }
        }
        Row {
            width: parent.width
            Text { width: parent.width - valueLabel.implicitWidth; text: adjustment.caption; textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.space(12) }
            Text { id: valueLabel; text: adjustment.value + adjustment.suffix; textFormat: Text.PlainText; color: Color.muted; font.family: root.fontFamily; font.pixelSize: Style.space(11) }
        }
        PanelSlider {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            implicitHeight: Style.space(21)
            minimum: adjustment.minimum; maximum: adjustment.maximum; value: adjustment.value
            integer: true; step: 1; knobSize: Style.space(12); trackHeight: Style.space(3)
            fillColor: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.5)
            knobColor: root.foreground
            trackColor: adjustment.activeFocus ? "#414950" : "#293138"
            onMoved: function(next) { adjustment.forceActiveFocus(); adjustment.edited(Math.round(next)) }
        }
    }
    SpoilerPreview { width: parent.width; height: Style.space(118); appearance: root.draft; customShaderLabel: root.tr("shader_preview"); animate: root.animate; radius: Style.space(10) }
    Grid {
        width: parent.width; columns: 5; spacing: Style.space(7)
        Repeater {
            model: Appearance.variants
            delegate: Rectangle {
                id: preset
                required property string modelData
                readonly property bool selected: root.draft.shader_path === "" && root.draft.variant === modelData
                width: (parent.width - parent.spacing * (parent.columns - 1)) / parent.columns
                height: Style.space(68)
                radius: Style.space(7)
                color: "transparent"
                border.width: selected || activeFocus ? 1 : 0
                border.color: selected ? Color.accent : root.foreground
                enabled: !root.busy
                opacity: enabled ? 1 : 0.45
                activeFocusOnTab: true
                Accessible.role: Accessible.Button
                Accessible.name: root.tr(modelData)
                function pick() { root.pickBuiltin(modelData) }
                Keys.onSpacePressed: pick()
                Keys.onReturnPressed: pick()
                Rectangle {
                    x: Style.space(3); y: Style.space(3)
                    width: parent.width - x * 2; height: Style.space(41)
                    radius: Style.space(5); color: "#101315"; clip: true
                    // Fixed reference swatches are actual native GPU captures.
                    // The larger procedural preview follows this user's draft.
                    Image {
                        anchors.fill: parent
                        source: Qt.resolvedUrl("assets/presets/" + preset.modelData + ".png")
                        fillMode: Image.PreserveAspectCrop; smooth: true
                    }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom; anchors.bottomMargin: Style.space(6)
                    text: root.tr(preset.modelData); textFormat: Text.PlainText
                    color: preset.selected ? root.foreground : Color.muted
                    font.family: root.fontFamily; font.pixelSize: Style.space(10)
                }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: preset.pick() }
            }
        }
    }
    Row {
        width: parent.width
        spacing: Style.space(10)
        Repeater {
            model: ["#ffffff", "#cbdcec", "#a8b5f2", "#adcfc8", "#d7b9ca", "#d6c9ad"]
            delegate: Rectangle {
                required property string modelData
                width: Style.space(23); height: width; radius: width / 2
                anchors.verticalCenter: parent.verticalCenter
                color: modelData
                border.width: root.draft.color === modelData || activeFocus ? 2 : 0
                border.color: "#758496"
                opacity: 0.84
                activeFocusOnTab: true
                function pick() { root.edited("color", modelData); root.syncColor() }
                Keys.onSpacePressed: pick()
                Keys.onReturnPressed: pick()
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: parent.pick() }
            }
        }
        TextField {
            id: hex
            objectName: "spoilerColor"
            width: Math.max(Style.space(86), parent.width - Style.space(198))
            font.family: root.fontFamily; font.pixelSize: Style.space(11)
            text: root.draft.color; maximumLength: 7; placeholderText: "#ffffff"
            validator: RegularExpressionValidator { regularExpression: /#[0-9a-fA-F]{6}/ }
            onTextEdited: {
                if (acceptableInput) root.edited("color", text.toLowerCase())
            }
            // Only human text edits create intent. A native color can change
            // while this field merely has focus; blur must not send stale text.
            onActiveFocusChanged: if (!activeFocus) root.syncColor()
        }
    }
    Adjustment { caption: root.tr("grain"); value: root.draft.grain; onEdited: function(next) { root.edited("grain", next) } }
    Adjustment { caption: root.tr("speed"); value: root.draft.speed; maximum: 200; onEdited: function(next) { root.edited("speed", next) } }
    Adjustment { caption: root.tr("darkness"); value: root.draft.darkness; onEdited: function(next) { root.edited("darkness", next) } }
    Button {
        width: parent.width
        text: root.tr("advanced") + (root.advanced ? " ▴" : " ▾")
        focusable: true; fontFamily: root.fontFamily; fontSize: Style.space(11)
        onClicked: root.advanced = !root.advanced
    }
    Column {
        width: parent.width; spacing: Style.space(12); visible: root.advanced
        Text { text: root.tr("privacy_icon"); textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.space(12) }
        Row {
            width: parent.width; spacing: Style.space(5)
            Repeater {
                model: Appearance.icons
                delegate: Button {
                    required property string modelData
                    width: (parent.width - parent.spacing * (Appearance.icons.length - 1)) / Appearance.icons.length
                    text: root.tr("icon_" + modelData)
                    tooltipText: modelData === "custom" ? root.tr("asset_preview_hint") : (root.draft.variant === "error404" || root.draft.variant === "anonymous") && modelData !== "none" ? root.tr("art_icon_hint") : ""
                    selected: (root.draft.eye ? root.draft.icon : "none") === modelData
                    bordered: true; focusable: true; enabled: !root.busy && (root.assetsSupported || modelData !== "custom")
                    fontFamily: root.fontFamily; fontSize: Style.space(11)
                    onClicked: {
                        root.customIconEditor = modelData === "custom"
                        if (modelData === "custom") {
                            if (iconPath.changedByUser && !Appearance.validPath(iconPath.text, false)) return
                            iconPath.commit()
                        } else {
                            root.builtinIconPicked(modelData)
                            iconPath.discard(root.draft.icon_path)
                            return
                        }
                        if (root.draft.icon_path !== "")
                            root.editedPatch({icon: modelData, eye: modelData !== "none"})
                    }
                }
            }
        }
        LocalPath {
            id: iconPath
            objectName: "customIconPath"
            width: parent.width
            visible: root.customIconEditor || root.draft.icon === "custom"
            enabled: root.assetsSupported && !root.busy
            savedValue: root.draft.icon_path
            placeholderText: root.tr("icon_path_placeholder")
            onCommitted: function(path) {
                if (path !== "") root.editedPatch({icon: "custom", icon_path: path, eye: true})
                else root.editedPatch({icon: "eye", icon_path: "", eye: true})
            }
        }
        Adjustment {
            caption: root.tr("icon_size"); value: root.draft.eye_size; minimum: 40; maximum: 128; suffix: " px"
            enabled: root.draft.eye && root.draft.icon !== "none"
            onEdited: function(next) { root.edited("eye_size", next) }
        }
        Adjustment {
            caption: root.tr("icon_opacity"); value: root.draft.icon_opacity
            enabled: root.draft.eye && root.draft.icon !== "none"
            onEdited: function(next) { root.edited("icon_opacity", next) }
        }
        Text { text: root.tr("custom_shader"); textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.space(12) }
        LocalPath {
            id: shaderPath
            objectName: "customShaderPath"
            width: parent.width
            savedValue: root.draft.shader_path
            enabled: root.assetsSupported && !root.busy
            shader: true
            placeholderText: root.tr("shader_path_placeholder")
            onCommitted: function(path) { root.edited("shader_path", path) }
        }
        Text {
            width: parent.width; height: Style.space(32)
            text: root.tr("shader_hint"); textFormat: Text.PlainText; color: Color.muted
            font.family: root.fontFamily; font.pixelSize: Style.space(11); wrapMode: Text.WordWrap
        }
    }
    Row {
        width: parent.width; spacing: Style.space(8)
        Text {
            width: (parent.width - parent.spacing) * 0.56
            height: Style.space(31)
            verticalAlignment: Text.AlignVCenter
            text: !root.colorValid ? root.tr("color_invalid") : !root.pathsValid ? root.tr("path_invalid") : root.saving ? root.tr("autosaving") : root.tr("autosave_hint")
            textFormat: Text.PlainText; color: Color.muted
            font.family: root.fontFamily; font.pixelSize: Style.space(11)
            wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight
        }
        Button {
            width: (parent.width - parent.spacing) * 0.44
            text: root.tr("reset_appearance"); focusable: true; enabled: !root.busy
            fontFamily: root.fontFamily; fontSize: Style.space(11)
            onClicked: root.resetRequested()
        }
    }
    Text {
        width: parent.width
        text: root.mode === "spoiler" ? root.tr("spoiler_only") : root.tr("spoiler_later")
        textFormat: Text.PlainText; color: Color.muted; font.family: root.fontFamily; font.pixelSize: Style.space(11); wrapMode: Text.WordWrap
    }
}
