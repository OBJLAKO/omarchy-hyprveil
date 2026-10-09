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
        c.moveTo(2, 12)
        c.bezierCurveTo(4.6, 8.1, 8, 6, 12, 6)
        c.bezierCurveTo(16, 6, 19.4, 8.1, 22, 12)
        c.bezierCurveTo(19.4, 15.9, 16, 18, 12, 18)
        c.bezierCurveTo(8, 18, 4.6, 15.9, 2, 12)
        c.closePath(); c.stroke()
        c.beginPath()
        c.arc(12, 12, 2.7, 0, Math.PI * 2)
        c.stroke()
        if (crossed) {
            c.beginPath()
            c.moveTo(3.5, 3.5)
            c.lineTo(20.5, 20.5)
            c.stroke()
        }
    }
}
