// Exact controller/native appearance contract. Mask opacity is fixed; icon_opacity affects only the icon.
var fields = ["variant", "color", "grain", "speed", "darkness", "eye", "eye_size", "icon", "icon_opacity"];
var variants = ["prism", "signal", "aurora", "contour", "radar", "matte", "error404", "matrix", "anonymous", "glass"];
var icons = ["eye", "lock", "shield", "none"];
var aliases = {satin: "prism", telegram: "signal", grid: "radar", "404": "error404",
               cmatrix: "matrix", anon: "anonymous", "liquid-glass": "glass", liquidglass: "glass"};
function defaults() {
    return { variant: "prism", color: "#ffffff", grain: 50, speed: 100, darkness: 50, eye: true, eye_size: 80, icon: "eye", icon_opacity: 75 };
}
function integer(value, minimum, maximum) {
    return typeof value === "number" && isFinite(value) && Math.floor(value) === value && value >= minimum && value <= maximum;
}
function parse(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    var keys = Object.keys(value);
    if (keys.length !== fields.length && keys.length !== fields.length - 2) return null;
    for (var i = 0; i < keys.length; ++i) if (fields.indexOf(keys[i]) < 0) return null;
    if (typeof value.variant !== "string") return null;
    var variant = aliases[value.variant] || value.variant;
    var legacy = keys.length === fields.length - 2;
    var icon = legacy ? "eye" : value.icon;
    var iconOpacity = legacy ? 75 : value.icon_opacity;
    if (legacy && (value.icon !== undefined || value.icon_opacity !== undefined)) return null;
    if (variants.indexOf(variant) < 0 ||
        typeof value.color !== "string" || !/^#[0-9a-f]{6}$/.test(value.color) ||
        !integer(value.grain, 0, 100) || !integer(value.speed, 0, 200) || !integer(value.darkness, 0, 100) ||
        typeof value.eye !== "boolean" || !integer(value.eye_size, 40, 128) ||
        icons.indexOf(icon) < 0 || !integer(iconOpacity, 0, 100)) return null;
    return { variant: variant, color: value.color, grain: value.grain, speed: value.speed,
             darkness: value.darkness, eye: value.eye, eye_size: value.eye_size, icon: icon, icon_opacity: iconOpacity };
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
function updateMany(value, patch) {
    var result = parse(value);
    if (!result || !patch || typeof patch !== "object" || Array.isArray(patch)) return null;
    var keys = Object.keys(patch);
    for (var i = 0; i < keys.length; ++i) {
        if (fields.indexOf(keys[i]) < 0) return null;
        var next = patch[keys[i]];
        if (keys[i] === "color" && typeof next === "string") next = next.toLowerCase();
        result[keys[i]] = next;
    }
    return parse(result);
}
function command(value, keys) {
    var p = parse(value);
    if (!p) return [];
    keys = keys === undefined ? fields : keys;
    if (!Array.isArray(keys) || !keys.length) return [];
    var names = {variant: "--variant", color: "--color", grain: "--grain", speed: "--speed", darkness: "--darkness",
                 eye: "--eye", eye_size: "--eye-size", icon: "--icon", icon_opacity: "--icon-opacity"};
    var result = ["configure"], seen = {};
    for (var i = 0; i < keys.length; ++i) {
        var key = keys[i];
        if (fields.indexOf(key) < 0 || seen[key]) return [];
        seen[key] = true;
        result.push(names[key], key === "eye" ? (p.eye ? "on" : "off") : String(p[key]));
    }
    return result;
}
