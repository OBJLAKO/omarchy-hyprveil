import QtQuick
import qs.Commons
import qs.Ui
import "Privacy.js" as Privacy

Rectangle {
    id: root
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
            text: root.privacy.state === "hidden" ? "Окно скрыто от захвата" : root.privacy.state === "visible" ? "Окно видно в захвате"
                  : root.privacy.state === "none" ? "Активное окно не выбрано" : "Статус окна недоступен"
            textFormat: Text.PlainText; color: root.foreground; font.family: root.fontFamily; font.pixelSize: Style.space(12); elide: Text.ElideRight
        }
        Text {
            width: parent.width
            text: root.privacy.inherited && !root.privacy.native_private ? "Защита сохранена при обновлении" : "ЛКМ по значку · Super+Alt+H"
            textFormat: Text.PlainText; color: Color.muted; font.family: root.fontFamily; font.pixelSize: Style.space(10); elide: Text.ElideRight
        }
    }
    Button {
        id: toggle
        anchors.right: parent.right; anchors.rightMargin: Style.space(10); anchors.verticalCenter: parent.verticalCenter
        width: Style.space(83)
        text: root.busy ? "Ждём…" : root.privacy.state === "hidden" ? "Показать" : "Скрыть"
        enabled: Privacy.toggleAllowed(root.privacy) && !root.busy
        bordered: true; focusable: true; fontFamily: root.fontFamily; fontSize: Style.space(11)
        onClicked: root.toggleRequested()
    }
}
