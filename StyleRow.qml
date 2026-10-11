import QtQuick
import qs.Commons
import qs.Ui
import "Appearance.js" as Appearance

BorderSurface {
    id: root
    property string mode: "black"
    property string title: ""
    property string detail: ""
    property bool selected: false
    property bool hasCursor: false
    property bool animate: false
    property var appearance: Appearance.defaults()
    property color foreground: Color.popups.text
    property string fontFamily: Style.font.family
    signal picked()
    signal hovered()

    width: parent ? parent.width : implicitWidth
    implicitWidth: Style.space(420)
    implicitHeight: Style.space(68)
    radius: Math.max(Style.cornerRadius, Style.space(10))
    opacity: enabled ? 1 : 0.55
    color: selected ? Qt.rgba(foreground.r, foreground.g, foreground.b, 0.06)
         : mouse.containsMouse || hasCursor ? Qt.rgba(foreground.r, foreground.g, foreground.b, 0.035)
         : "transparent"
    border.width: 1
    border.color: selected ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.35)
                : mouse.containsMouse || hasCursor ? Qt.rgba(foreground.r, foreground.g, foreground.b, 0.18)
                : Qt.rgba(foreground.r, foreground.g, foreground.b, 0.07)
    Behavior on color { ColorAnimation { duration: 160 } }

    // A synthetic thumbnail. It never reads a window, screenshot, title or
    // texture. Animation is limited to this small preview while the panel opens.
    Rectangle {
        id: preview
        x: Style.space(13)
        anchors.verticalCenter: parent.verticalCenter
        width: Style.space(66)
        height: Style.space(48)
        radius: Style.space(7)
        color: root.mode === "black" ? "#000000" : root.mode === "color" || root.mode === "image" ? root.appearance.mask_color : "#12181f"
        border.color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.09)
        border.width: 1
        clip: true

        Canvas {
            anchors.fill: parent
            visible: root.mode === "omit"
            onPaint: {
                var c = getContext("2d")
                c.reset(); c.strokeStyle = "rgba(195,207,220,0.18)"; c.lineWidth = 0.75
                var pad = 13, arm = 6
                c.beginPath()
                c.moveTo(pad, pad + arm); c.lineTo(pad, pad); c.lineTo(pad + arm, pad)
                c.moveTo(width - pad - arm, pad); c.lineTo(width - pad, pad); c.lineTo(width - pad, pad + arm)
                c.moveTo(pad, height - pad - arm); c.lineTo(pad, height - pad); c.lineTo(pad + arm, height - pad)
                c.moveTo(width - pad - arm, height - pad); c.lineTo(width - pad, height - pad); c.lineTo(width - pad, height - pad - arm)
                c.stroke()
            }
        }
        Item {
            objectName: "imageAssetPlaceholder"
            anchors.fill: parent
            visible: root.mode === "image"
            // User paths are never opened by Qt. Native validation/rendering
            // owns PNG files, including paths edited before a save is accepted.
            Canvas {
                anchors.horizontalCenter: parent.horizontalCenter
                y: Style.space(7); width: Style.space(27); height: Style.space(22)
                onPaint: {
                    var c = getContext("2d")
                    c.reset(); c.strokeStyle = "#c3cfdc"; c.lineWidth = 1.1
                    c.strokeRect(1.5, 1.5, width - 3, height - 3)
                    c.beginPath(); c.arc(width * 0.72, height * 0.29, 2, 0, Math.PI * 2); c.stroke()
                    c.beginPath(); c.moveTo(3, height - 5); c.lineTo(width * 0.35, height * 0.42)
                    c.lineTo(width * 0.59, height * 0.7); c.lineTo(width - 3, height * 0.48); c.stroke()
                }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom; anchors.bottomMargin: Style.space(5)
                text: "PNG"; textFormat: Text.PlainText; color: "#c3cfdc"
                font.family: root.fontFamily; font.pixelSize: Style.space(9)
            }
        }
        SpoilerPreview {
            anchors.fill: parent
            visible: root.mode === "spoiler"
            appearance: root.appearance
            animate: root.animate && visible
            radius: Style.space(7)
        }
    }

    Column {
        anchors.left: preview.right
        anchors.leftMargin: Style.space(15)
        anchors.right: marker.left
        anchors.rightMargin: Style.space(10)
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(4)
        Text {
            width: parent.width
            text: root.title
            textFormat: Text.PlainText
            color: root.foreground
            font.family: root.fontFamily
            font.pixelSize: Style.space(13)
            font.weight: Font.Medium
            wrapMode: Text.WordWrap
        }
        Text {
            width: parent.width
            text: root.detail
            textFormat: Text.PlainText
            color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.52)
            font.family: root.fontFamily
            font.pixelSize: Style.space(11)
            wrapMode: Text.WordWrap
        }
    }
    Rectangle {
        id: marker
        width: Style.space(12)
        height: width
        radius: width / 2
        anchors.right: parent.right
        anchors.rightMargin: Style.space(17)
        anchors.verticalCenter: parent.verticalCenter
        color: "transparent"
        border.width: 1
        border.color: root.selected ? Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.7) : Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.2)
        Rectangle {
            anchors.centerIn: parent
            width: Style.space(4)
            height: width
            radius: width / 2
            color: Color.accent
            visible: root.selected
        }
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabled
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onEntered: root.hovered()
        onClicked: root.picked()
    }
}
