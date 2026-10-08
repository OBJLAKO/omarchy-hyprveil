import QtQuick
import "Appearance.js" as Appearance

// Procedural, opaque illustration. It never samples client pixels or a capture.
Rectangle {
    id: root
    property var appearance: Appearance.defaults()
    property bool animate: false
    readonly property var p: Appearance.parse(appearance) || Appearance.defaults()
    radius: 8
    color: "#000000"
    border.width: 1
    border.color: "#26303a"
    clip: true

    Canvas {
        id: canvas
        anchors.fill: parent
        property real phase: 0
        onPhaseChanged: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections { target: root; function onPChanged() { canvas.requestPaint() } }
        function channel(value) { return Math.max(0, Math.min(255, Math.round(value))) }
        function rgb(r, g, b) { return "rgb(" + channel(r) + "," + channel(g) + "," + channel(b) + ")" }
        onPaint: {
            var c = getContext("2d")
            c.reset()
            var tint = Qt.color(root.p.color)
            var dark = root.p.darkness / 100
            var strength = 2 * (1 - dark)
            var base = 21.5
            function field(r, g, b) { return canvas.rgb(r * tint.r * strength, g * tint.g * strength, b * tint.b * strength) }
            var g = c.createLinearGradient(0, 0, width, height)
            g.addColorStop(0, field(base * 0.84, base * 1.06, base * 1.28))
            g.addColorStop(0.52 + Math.sin(phase) * 0.06, field(base * 0.62, base * 0.85, base * 1.08))
            g.addColorStop(1, field(base * 1.02, base * 1.19, base * 1.4))
            c.fillStyle = g; c.fillRect(0, 0, width, height)
            if (root.p.variant === "satin") {
                c.lineWidth = height * 0.22
                c.strokeStyle = field(255, 255, 255)
                c.globalAlpha = 0.025
                for (var ribbon = 0; ribbon < 4; ++ribbon) {
                    var y = (ribbon - 1) * height * 0.4 + Math.sin(phase * 0.5) * height * 0.09
                    c.beginPath(); c.moveTo(-width * 0.2, y)
                    c.bezierCurveTo(width * 0.25, y - height * 0.1, width * 0.6, y + height * 0.7, width * 1.2, y + height * 0.2)
                    c.stroke()
                }
                c.globalAlpha = 1
            }
            var amount = root.p.grain / 100
            var telegram = root.p.variant === "telegram"
            var count = Math.round((telegram ? 1600 : 380) * amount)
            for (var i = 0; i < count; ++i) {
                var px = ((i * 43.37 + Math.sin(phase + i) * (telegram ? 1.8 : 0.5)) % width + width) % width
                var py = ((i * 29.21 + Math.cos(phase * 0.6 + i) * (telegram ? 1.8 : 0.5)) % height + height) % height
                var alpha = (telegram ? 0.13 : 0.025) + (telegram ? 0.17 : 0.045) * (0.5 + 0.5 * Math.sin(i + phase))
                c.fillStyle = field(255, 255, 255)
                c.globalAlpha = alpha
                c.beginPath(); c.arc(px, py, telegram ? 0.25 + (i % 3) * 0.15 : 0.2 + (i % 3) * 0.08, 0, Math.PI * 2); c.fill()
            }
            c.globalAlpha = 1
        }
        NumberAnimation on phase {
            from: 0; to: Math.PI * 2
            duration: Math.round(14000 * 100 / Math.max(1, root.p.speed))
            loops: Animation.Infinite
            running: root.animate && root.p.speed > 0
        }
    }
    Eye {
        anchors.centerIn: parent
        width: Math.min(root.width * 0.28, 34) * root.p.eye_size / 80
        height: width
        ink: "#dbd9cf"
        opacity: 0.76
        visible: root.p.eye
    }
}
