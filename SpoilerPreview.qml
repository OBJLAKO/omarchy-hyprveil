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
            var colors = {
                prism: [13, 12, 22], signal: [24, 10, 5], aurora: [6, 11, 20],
                contour: [35, 17, 14], radar: [5, 16, 15], matte: [29, 30, 31],
                error404: [7, 6, 17], matrix: [1, 8, 4], anonymous: [7, 10, 16], glass: [9, 20, 44]
            }
            var color = colors[root.p.variant]
            c.fillStyle = field(color[0], color[1], color[2]); c.fillRect(0, 0, width, height)
            if (root.p.variant === "prism") {
                var shift = Math.sin(phase * 0.7) * width * 0.13
                var spectrum = c.createLinearGradient(shift, height, width + shift, 0)
                spectrum.addColorStop(0, field(13, 67, 65))
                spectrum.addColorStop(0.25, field(36, 67, 25))
                spectrum.addColorStop(0.48, field(76, 43, 19))
                spectrum.addColorStop(0.7, field(81, 20, 65))
                spectrum.addColorStop(1, field(22, 31, 81))
                c.fillStyle = spectrum; c.fillRect(0, 0, width, height)
                c.globalAlpha = 0.25; c.fillStyle = "#000000"
                c.beginPath(); c.moveTo(0, height * 0.15); c.lineTo(width * 0.6, 0)
                c.lineTo(width, height * 0.8); c.lineTo(width * 0.4, height); c.closePath(); c.fill()
                c.globalAlpha = 0.7; c.strokeStyle = field(66, 78, 87); c.lineWidth = 1.1
                c.beginPath(); c.moveTo(0, height * (0.05 + 0.1 * Math.sin(phase)))
                c.lineTo(width, height * (0.9 + 0.1 * Math.sin(phase))); c.stroke()
                c.globalAlpha = 1
            } else if (root.p.variant === "signal") {
                c.fillStyle = field(32, 13, 6); c.globalAlpha = 0.5
                for (var y = 0; y < height; y += 5) c.fillRect(0, y, width, 1)
                var beam = (phase / (Math.PI * 2) * height + height * 0.5) % height
                var scan = c.createLinearGradient(0, beam - height * 0.25, 0, beam + height * 0.25)
                scan.addColorStop(0, "transparent"); scan.addColorStop(0.5, field(76, 34, 10)); scan.addColorStop(1, "transparent")
                c.globalAlpha = 0.85; c.fillStyle = scan
                c.fillRect(0, beam - height * 0.25, width, height * 0.5)
                c.globalAlpha = 0.3; c.fillStyle = field(99, 45, 14); c.fillRect(0, beam, width, 1)
                c.globalAlpha = 1
            } else if (root.p.variant === "aurora") {
                c.lineWidth = height * 0.27
                for (var ribbon = 0; ribbon < 3; ++ribbon) {
                    c.strokeStyle = ribbon === 1 ? field(158, 82, 241) : field(40, 226, 207)
                    c.globalAlpha = ribbon === 1 ? 0.35 : 0.27
                    var y = height * (0.2 + ribbon * 0.27) + Math.sin(phase + ribbon) * height * 0.17
                    c.beginPath(); c.moveTo(-width * 0.1, y)
                    c.bezierCurveTo(width * 0.25, y - height * 0.7, width * 0.65, y + height * 0.65, width * 1.1, y - height * 0.25)
                    c.stroke()
                }
                c.globalAlpha = 1
            } else if (root.p.variant === "contour") {
                c.lineWidth = 0.9; c.strokeStyle = field(100, 53, 33); c.globalAlpha = 0.7
                for (var line = 1; line < 13; ++line) {
                    c.beginPath()
                    for (var a = 0; a <= 80; ++a) {
                        var theta = a / 80 * Math.PI * 2
                        var r = line * 0.055 * (1 + 0.16 * Math.sin(theta * 3 + phase) + 0.1 * Math.cos(theta * 5 - phase))
                        var x = width * (0.52 + Math.cos(theta) * r)
                        var y = height * (0.52 + Math.sin(theta) * r * 1.3)
                        if (a === 0) c.moveTo(x, y); else c.lineTo(x, y)
                    }
                    c.stroke()
                }
                c.globalAlpha = 1
            } else if (root.p.variant === "radar") {
                var cx = width * 0.5, cy = height * 0.5, radius = height * 0.8
                c.lineWidth = 0.7; c.strokeStyle = field(16, 47, 42); c.globalAlpha = 0.5
                c.beginPath()
                for (var x = 0; x < width; x += 32) { c.moveTo(x, 0); c.lineTo(x, height) }
                for (var y = 0; y < height; y += 32) { c.moveTo(0, y); c.lineTo(width, y) }
                c.stroke()
                c.globalAlpha = 0.55
                for (var ring = 1; ring <= 4; ++ring) {
                    c.beginPath(); c.arc(cx, cy, radius * ring / 4, 0, Math.PI * 2); c.stroke()
                }
                c.fillStyle = field(18, 103, 69); c.globalAlpha = 0.45
                c.beginPath(); c.moveTo(cx, cy); c.arc(cx, cy, radius, phase - 0.7, phase); c.closePath(); c.fill()
                c.globalAlpha = 0.85; c.beginPath(); c.moveTo(cx, cy)
                c.lineTo(cx + radius * Math.cos(phase), cy + radius * Math.sin(phase)); c.stroke()
                c.globalAlpha = 1
            } else if (root.p.variant === "error404") {
                // The same original 5x7 digit columns as the native shader.
                var digitWidth = height * 0.2856, digitHeight = height * 0.39
                c.fillStyle = field(166, 189, 232)
                for (var digit = 0; digit < 3; ++digit) {
                    var bits = digit === 1 ? 0x8b268be : 0xfe48a18
                    var last = digit === 1 ? 0x3e : 0x10
                    var left = width * 0.5 - height * 0.51 + digit * height * 0.34
                    for (var column = 0; column < 5; ++column) {
                        var data = column === 4 ? last : bits >> (column * 7)
                        for (var row = 0; row < 7; ++row) if ((data >> row) & 1)
                            c.fillRect(left + (column + 0.06) * digitWidth / 5,
                                       height * 0.28 + (row + 0.06) * digitHeight / 7,
                                       digitWidth / 5 * 0.88, digitHeight / 7 * 0.88)
                    }
                }
                c.font = Math.round(height * 0.065) + "px monospace"
                c.textAlign = "center"; c.textBaseline = "middle"; c.fillStyle = field(69, 148, 184)
                c.fillText("H I D D E N", width * 0.5, height * 0.78)
                c.globalAlpha = 0.3; c.fillRect(0, phase / (Math.PI * 2) * height, width, 1); c.globalAlpha = 1
            } else if (root.p.variant === "matrix") {
                c.font = "9px monospace"; c.textAlign = "center"; c.textBaseline = "middle"
                var glyphs = "01XYZ#$%+<>"
                for (var column = 0; column < width / 12; ++column) {
                    var head = (phase * 30 + column * 37) % (height + 60)
                    for (var tail = 0; tail < 10; ++tail) {
                        var y = head - tail * 11
                        if (y < 0 || y > height) continue
                        c.fillStyle = tail === 0 ? field(146, 236, 164) : field(9, 95 - tail * 7, 35 - tail * 2)
                        c.fillText(glyphs.charAt((column * 7 + tail * 3 + Math.floor(phase * 2)) % glyphs.length), column * 12 + 6, y)
                    }
                }
            } else if (root.p.variant === "anonymous") {
                c.save(); c.translate(width * 0.5, height * 0.51)
                var face = Math.min(height * 0.4, width * 0.22)
                c.scale(face / 32, face / 32)
                c.fillStyle = field(173, 181, 191)
                c.beginPath(); c.moveTo(-25, -28); c.bezierCurveTo(-36, -8, -26, 24, 0, 34)
                c.bezierCurveTo(26, 24, 36, -8, 25, -28); c.quadraticCurveTo(0, -38, -25, -28); c.fill()
                c.strokeStyle = field(12, 18, 25); c.lineWidth = 3; c.lineCap = "round"
                c.beginPath(); c.moveTo(-21, -13); c.quadraticCurveTo(-13, -20, -5, -13)
                c.moveTo(5, -13); c.quadraticCurveTo(13, -20, 21, -13); c.stroke()
                c.beginPath(); c.moveTo(-20, 8); c.quadraticCurveTo(0, 25, 20, 8); c.stroke()
                c.lineWidth = 2; c.beginPath(); c.moveTo(-6, 7); c.quadraticCurveTo(0, 3, 6, 7); c.stroke()
                c.beginPath(); c.moveTo(0, 21); c.lineTo(0, 28); c.stroke()
                c.restore()
                c.fillStyle = field(65, 94, 132); c.globalAlpha = 0.3
                c.fillRect(0, phase / (Math.PI * 2) * height, width, 2); c.globalAlpha = 1
            } else if (root.p.variant === "glass") {
                var environment = c.createLinearGradient(0, 0, width, height)
                environment.addColorStop(0, field(108, 155, 190)); environment.addColorStop(0.48, field(97, 124, 180)); environment.addColorStop(1, field(174, 111, 180))
                c.fillStyle = environment; c.fillRect(0, 0, width, height)
                var lenses = [[-.24, -.06, .20, .28, -.25], [.23, .08, .18, .22, .3], [.08, -.275, .1, .1, 0]]
                for (var lens = 0; lens < lenses.length; ++lens) {
                    var spec = lenses[lens]
                    var lx = width * 0.5 + (spec[0] + Math.sin(phase + lens) * 0.04) * height
                    var ly = height * (0.5 + spec[1] + Math.cos(phase + lens) * 0.035)
                    var ex = height * spec[2], ey = height * spec[3], r = Math.min(ex, ey) * 0.65
                    c.save(); c.translate(lx, ly); c.rotate(spec[4] + Math.sin(phase * 0.6) * 0.1)
                    var glass = c.createLinearGradient(-ex, -ey, ex, ey)
                    glass.addColorStop(0, field(162, 195, 224)); glass.addColorStop(0.35, field(115, 158, 204))
                    glass.addColorStop(0.7, field(151, 141, 202)); glass.addColorStop(1, field(95, 129, 183))
                    c.fillStyle = glass
                    c.beginPath(); c.moveTo(-ex + r, -ey); c.lineTo(ex - r, -ey)
                    c.quadraticCurveTo(ex, -ey, ex, -ey + r); c.lineTo(ex, ey - r)
                    c.quadraticCurveTo(ex, ey, ex - r, ey); c.lineTo(-ex + r, ey)
                    c.quadraticCurveTo(-ex, ey, -ex, ey - r); c.lineTo(-ex, -ey + r)
                    c.quadraticCurveTo(-ex, -ey, -ex + r, -ey); c.closePath(); c.fill()
                    c.strokeStyle = field(218, 232, 250); c.globalAlpha = 0.8; c.lineWidth = 0.9; c.stroke()
                    c.globalAlpha = 0.65; c.beginPath(); c.moveTo(-ex + r, -ey + 2); c.lineTo(ex - r, -ey + 2); c.stroke()
                    c.restore()
                }
            }
            var amount = root.p.grain / 100
            var signal = root.p.variant === "signal"
            var count = Math.round(380 * amount)
            for (var i = 0; i < count; ++i) {
                var t = root.p.variant === "matte" ? 0 : phase
                var px = ((i * 43.37 + Math.sin(t + i) * (signal ? 1.8 : 0.5)) % width + width) % width
                var py = ((i * 29.21 + Math.cos(t * 0.6 + i) * (signal ? 1.8 : 0.5)) % height + height) % height
                var alpha = 0.01 + 0.02 * (0.5 + 0.5 * Math.sin(i + t))
                c.fillStyle = field(255, 255, 255)
                c.globalAlpha = alpha
                c.beginPath(); c.arc(px, py, signal ? 0.25 + (i % 3) * 0.15 : 0.2 + (i % 3) * 0.08, 0, Math.PI * 2); c.fill()
            }
            c.globalAlpha = 1
        }
        // This small procedural UI preview needs no more than 24 paints/s.
        // Hidden tabs, static thumbnails, speed zero and Matte do no animation work.
        Timer {
            interval: 42; repeat: true
            running: root.animate && root.p.speed > 0 && root.p.variant !== "matte"
            onTriggered: canvas.phase = (canvas.phase + Math.PI * 2 * interval / 14000 * root.p.speed / 100) % (Math.PI * 2)
        }
    }
    PrivacyIcon {
        anchors.centerIn: parent
        width: Math.min(root.width * 0.28, 34) * root.p.eye_size / 80
        height: width
        kind: root.p.icon
        ink: "#ebf0f5"
        opacity: root.p.icon_opacity / 100
        visible: root.p.eye && root.p.icon !== "none"
    }
}
