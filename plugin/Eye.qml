import QtQuick

Canvas {
    id: root
    property color ink: "white"
    property bool crossed: true
    property bool uncertain: false
    property real weight: 1.25
    implicitWidth: 24
    implicitHeight: 24
    onInkChanged: requestPaint()
    onCrossedChanged: requestPaint()
    onUncertainChanged: requestPaint()
    onWeightChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        var c = getContext("2d")
        c.reset()
        c.scale(width / 24, height / 24)
        c.strokeStyle = ink
        c.lineWidth = root.weight
        c.lineCap = "round"
        c.lineJoin = "round"
        if (uncertain) {
            c.font = "17px sans-serif"
            c.textAlign = "center"
            c.fillStyle = ink
            c.fillText("?", 12, 18)
            return
        }
        c.beginPath()
        c.moveTo(2.5, 12)
        c.bezierCurveTo(7.25, 5.6, 16.75, 5.6, 21.5, 12)
        c.bezierCurveTo(16.75, 18.4, 7.25, 18.4, 2.5, 12)
        c.stroke()
        c.beginPath()
        c.arc(12, 12, 2.45, 0, Math.PI * 2)
        c.stroke()
        if (crossed) {
            c.beginPath()
            c.moveTo(4, 4.5)
            c.lineTo(20, 19.5)
            c.stroke()
        }
    }
}
