import QtQuick
import qs.Commons
import qs.Ui
import "Privacy.js" as Privacy
import "I18n.js" as I18n

Rectangle {
    id: root
    property string language: I18n.language(Qt.locale().name)
    function tr(key) { return I18n.text(key, language) }
    property var privacy: Privacy.unknown()
    property bool busy: false
    property string fontFamily: "Adwaita Sans"
    property color foreground: Color.popups.text
    signal toggleRequested()
    width: parent ? parent.width : 0
    implicitHeight: Style.space(60)
    radius: Style.space(9)
    color: Qt.rgba(foreground.r, foreground.g, foreground.b, 0.025)
    Eye {
        id: statusEye
        width: Style.space(21); height: width
        anchors.left: parent.left; anchors.leftMargin: Style.space(12); anchors.verticalCenter: parent.verticalCenter
        ink: root.privacy.state === "hidden" ? Color.accent : Color.muted
        crossed: root.privacy.state === "hidden"
        uncertain: root.privacy.state === "unknown"
    }
    Column {
        anchors.left: statusEye.right; anchors.leftMargin: Style.space(11)
        anchors.right: toggle.right; anchors.rightMargin: toggle.width + Style.space(12)
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(4)
        Text {
            width: parent.width
            text: root.privacy.state === "hidden" ? root.tr("window_hidden") : root.privacy.state === "visible" ? root.tr("window_visible")
                  : root.privacy.state === "none" ? root.tr("window_none") : root.tr("window_unknown")
            textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.space(12); elide: Text.ElideRight
        }
        Text {
            width: parent.width
            text: root.privacy.inherited && !root.privacy.native_private ? root.tr("inherited_hint") : root.tr("window_click_hint")
            textFormat: Text.PlainText; color: Color.muted; font.family: root.fontFamily; font.pixelSize: Style.space(10); elide: Text.ElideRight
        }
    }
    Button {
        id: toggle
        anchors.right: parent.right; anchors.rightMargin: Style.space(10); anchors.verticalCenter: parent.verticalCenter
        width: Style.space(83)
        text: root.busy ? root.tr("waiting") : root.privacy.state === "hidden" ? root.tr("show") : root.tr("hide")
        enabled: Privacy.toggleAllowed(root.privacy) && !root.busy
        bordered: true; focusable: true; fontFamily: root.fontFamily; fontSize: Style.space(11)
        onClicked: root.toggleRequested()
    }
}
