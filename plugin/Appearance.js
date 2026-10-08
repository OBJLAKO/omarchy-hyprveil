// Exact controller/native appearance contract. No opacity or client-data field.
var fields = ["variant", "color", "grain", "speed", "darkness", "eye", "eye_size"];
function defaults() {
    return { variant: "satin", color: "#ffffff", grain: 50, speed: 100, darkness: 50, eye: true, eye_size: 80 };
}
function integer(value, minimum, maximum) {
    return typeof value === "number" && isFinite(value) && Math.floor(value) === value && value >= minimum && value <= maximum;
}
function parse(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    var keys = Object.keys(value);
    if (keys.length !== fields.length) return null;
    for (var i = 0; i < keys.length; ++i) if (fields.indexOf(keys[i]) < 0) return null;
    if (["satin", "telegram"].indexOf(value.variant) < 0 ||
        typeof value.color !== "string" || !/^#[0-9a-f]{6}$/.test(value.color) ||
        !integer(value.grain, 0, 100) || !integer(value.speed, 0, 200) || !integer(value.darkness, 0, 100) ||
        typeof value.eye !== "boolean" || !integer(value.eye_size, 40, 128)) return null;
    return { variant: value.variant, color: value.color, grain: value.grain, speed: value.speed,
             darkness: value.darkness, eye: value.eye, eye_size: value.eye_size };
}
function equal(left, right) {
    var a = parse(left), b = parse(right);
    if (!a || !b) return false;
    for (var i = 0; i < fields.length; ++i) if (a[fields[i]] !== b[fields[i]]) return false;
    return true;
}
function update(value, key, next) {
    var result = parse(value);
    if (!result || fields.indexOf(key) < 0) return null;
    if (key === "color" && typeof next === "string" && /^#[0-9a-fA-F]{6}$/.test(next)) next = next.toLowerCase();
    result[key] = next;
    return parse(result);
}
function command(value) {
    var p = parse(value);
    if (!p) return [];
    return ["configure", "--variant", p.variant, "--color", p.color,
            "--grain", String(p.grain), "--speed", String(p.speed), "--darkness", String(p.darkness),
            "--eye", p.eye ? "on" : "off", "--eye-size", String(p.eye_size)];
}
