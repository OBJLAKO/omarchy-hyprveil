pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Ui
import "Appearance.js" as Appearance

Column {
    id: root
    property var draft: Appearance.defaults()
    property bool dirty: false
    property bool busy: false
    property bool animate: false
    property string mode: "spoiler"
    property color foreground: Color.popups.text
    property string fontFamily: "Adwaita Sans"
    readonly property bool colorValid: hex.acceptableInput
    signal edited(string key, var value)
    signal variantPicked(string variant)
    signal interactionStarted()
    signal applyRequested()
    signal resetRequested()
    signal closeRequested()
    function syncColor() { hex.text = draft.color }
    onDraftChanged: if (!hex.activeFocus) syncColor()
    Keys.onEscapePressed: closeRequested()
    spacing: Style.space(12)

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
    SpoilerPreview { width: parent.width; height: Style.space(118); appearance: root.draft; animate: root.animate; radius: Style.space(10) }
    Row {
        width: parent.width; spacing: Style.space(8)
        Button {
            width: (parent.width - parent.spacing) / 2
            text: "Сатин"; selected: root.draft.variant === "satin"; bordered: true; focusable: true
            enabled: !root.busy && root.colorValid; fontFamily: root.fontFamily; fontSize: Style.space(12)
            onClicked: root.variantPicked("satin")
        }
        Button {
            width: (parent.width - parent.spacing) / 2
            text: "Telegram"; selected: root.draft.variant === "telegram"; bordered: true; focusable: true
            enabled: !root.busy && root.colorValid; fontFamily: root.fontFamily; fontSize: Style.space(12)
            onClicked: root.variantPicked("telegram")
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
            width: Math.max(Style.space(86), parent.width - Style.space(198))
            font.family: root.fontFamily; font.pixelSize: Style.space(11)
            text: root.draft.color; maximumLength: 7; placeholderText: "#ffffff"
            validator: RegularExpressionValidator { regularExpression: /#[0-9a-fA-F]{6}/ }
            onTextEdited: {
                root.interactionStarted()
                if (acceptableInput) root.edited("color", text.toLowerCase())
            }
            onEditingFinished: if (acceptableInput) root.edited("color", text.toLowerCase())
        }
    }
    Adjustment { caption: "Зернистость"; value: root.draft.grain; onEdited: function(next) { root.edited("grain", next) } }
    Adjustment { caption: "Скорость"; value: root.draft.speed; maximum: 200; onEdited: function(next) { root.edited("speed", next) } }
    Adjustment { caption: "Затемнение"; value: root.draft.darkness; onEdited: function(next) { root.edited("darkness", next) } }
    Row {
        width: parent.width
        Text { width: parent.width - eyeToggle.implicitWidth; anchors.verticalCenter: parent.verticalCenter; text: "Перечёркнутый глаз"; textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.space(12) }
        ToggleSwitch {
            id: eyeToggle
            checked: root.draft.eye; rounded: true; trackHeight: Style.space(18); busy: root.busy
            activeFocusOnTab: true
            Keys.onSpacePressed: root.edited("eye", !root.draft.eye)
            onToggled: root.edited("eye", !root.draft.eye)
        }
    }
    Adjustment { caption: "Размер глаза"; value: root.draft.eye_size; minimum: 40; maximum: 128; suffix: " px"; enabled: root.draft.eye; onEdited: function(next) { root.edited("eye_size", next) } }
    Row {
        width: parent.width; spacing: Style.space(8)
        Button {
            width: (parent.width - parent.spacing) * 0.56
            text: root.busy ? "Применяем…" : root.dirty ? "Применить изменения" : "Применено"
            selected: root.dirty; bordered: true; focusable: true
            enabled: root.dirty && root.colorValid && !root.busy
            fontFamily: root.fontFamily; fontSize: Style.space(12)
            onClicked: root.applyRequested()
        }
        Button {
            width: (parent.width - parent.spacing) * 0.44
            text: "Сбросить оформление"; focusable: true; enabled: !root.busy
            fontFamily: root.fontFamily; fontSize: Style.space(11)
            onClicked: root.resetRequested()
        }
    }
    Text {
        width: parent.width
        text: root.mode === "spoiler" ? "Настройки меняют только спойлер. Выбранный способ скрытия сохраняется."
            : "Оформление появится при выборе «Спойлер». Текущий способ скрытия сохранится."
        textFormat: Text.PlainText; color: Color.muted; font.family: root.fontFamily; font.pixelSize: Style.space(11); wrapMode: Text.WordWrap
    }
}
