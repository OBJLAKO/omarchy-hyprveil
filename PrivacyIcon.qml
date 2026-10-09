import QtQuick

// Exact synthetic native icon paths, expressed in the same 128-unit tile.
Canvas {
    id: root
    property string kind: "eye"
    property color ink: "#ebf0f5"
    implicitWidth: 32
    implicitHeight: 32
    onKindChanged: requestPaint()
    onInkChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        var c = getContext("2d")
        c.reset(); c.scale(width / 128, height / 128)
        c.strokeStyle = ink; c.fillStyle = ink
        c.lineWidth = 3.4; c.lineCap = "round"; c.lineJoin = "round"
        if (kind === "eye") {
            c.beginPath(); c.moveTo(24, 64)
            c.bezierCurveTo(40, 42, 52, 38, 64, 38)
            c.bezierCurveTo(76, 38, 88, 42, 104, 64)
            c.bezierCurveTo(88, 86, 76, 90, 64, 90)
            c.bezierCurveTo(52, 90, 40, 86, 24, 64); c.closePath(); c.stroke()
            c.beginPath(); c.arc(64, 64, 11.5, 0, Math.PI * 2); c.stroke()
        } else if (kind === "lock") {
            c.beginPath(); c.moveTo(46, 55); c.lineTo(46, 44)
            c.bezierCurveTo(46, 20, 82, 20, 82, 44); c.lineTo(82, 55); c.stroke()
            c.beginPath(); c.moveTo(45, 55); c.lineTo(83, 55)
            c.bezierCurveTo(87, 55, 90, 58, 90, 62); c.lineTo(90, 91)
            c.bezierCurveTo(90, 95, 87, 98, 83, 98); c.lineTo(45, 98)
            c.bezierCurveTo(41, 98, 38, 95, 38, 91); c.lineTo(38, 62)
            c.bezierCurveTo(38, 58, 41, 55, 45, 55); c.closePath(); c.stroke()
            c.beginPath(); c.arc(64, 73, 3.5, 0, Math.PI * 2); c.fill()
            c.beginPath(); c.moveTo(64, 76); c.lineTo(64, 83); c.stroke()
        } else if (kind === "shield") {
            c.beginPath(); c.moveTo(64, 26)
            c.bezierCurveTo(75, 34, 87, 39, 98, 42); c.lineTo(94, 70)
            c.bezierCurveTo(91, 86, 79, 99, 64, 106)
            c.bezierCurveTo(49, 99, 37, 86, 34, 70); c.lineTo(30, 42)
            c.bezierCurveTo(41, 39, 53, 34, 64, 26); c.closePath(); c.stroke()
            c.beginPath(); c.moveTo(48, 64); c.lineTo(60, 76); c.lineTo(81, 54); c.stroke()
        }
    }
}
