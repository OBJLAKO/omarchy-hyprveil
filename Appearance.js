// Exact controller/native appearance contract. Mask opacity is fixed; icon_opacity affects only the icon.
var baseFields = ["variant", "color", "grain", "speed", "darkness", "eye", "eye_size", "icon", "icon_opacity"];
var extraFields = ["mask_color", "image_fit", "shader_path", "icon_path", "image_path"];
var fields = baseFields.concat(extraFields);
var imageFits = ["fill", "fit", "tile", "stretch"];
var variants = ["prism", "signal", "aurora", "contour", "radar", "matte", "error404", "matrix", "anonymous", "glass"];
var icons = ["eye", "lock", "shield", "none", "custom"];
var aliases = {satin: "prism", telegram: "signal", grid: "radar", "404": "error404",
               cmatrix: "matrix", anon: "anonymous", "liquid-glass": "glass", liquidglass: "glass"};
function defaults() {
    return { variant: "prism", color: "#ffffff", grain: 50, speed: 100, darkness: 50, eye: true, eye_size: 80, icon: "eye", icon_opacity: 75,
             mask_color: "#000000", image_fit: "stretch", shader_path: "", icon_path: "", image_path: "" };
}
function integer(value, minimum, maximum) {
    return typeof value === "number" && isFinite(value) && Math.floor(value) === value && value >= minimum && value <= maximum;
}
function validPath(value, shader) {
    if (typeof value !== "string" || /[\x00-\x1f\x7f]/.test(value)) return false;
    if (value === "") return true;
    if (value.charAt(0) !== "/" || (shader && !/\.frag$/i.test(value))) return false;
    try { return encodeURIComponent(value).replace(/%[0-9a-f]{2}|./gi, "x").length <= 4096; }
    catch (e) { return false; }
}
function localUrl(value) {
    return validPath(value, false) && value !== "" ? "file://" + value.split("/").map(encodeURIComponent).join("/") : "";
}
function parse(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    var keys = Object.keys(value);
    if (keys.length !== fields.length && keys.length !== baseFields.length && keys.length !== baseFields.length - 2) return null;
    var extended = keys.length === fields.length;
    if (!extended && extraFields.some(function(key) { return value[key] !== undefined; })) return null;
    for (var i = 0; i < keys.length; ++i) if (fields.indexOf(keys[i]) < 0) return null;
    if (typeof value.variant !== "string") return null;
    var variant = aliases[value.variant] || value.variant;
    var legacy = keys.length === baseFields.length - 2;
    var icon = legacy ? "eye" : value.icon;
    var iconOpacity = legacy ? 75 : value.icon_opacity;
    if (legacy && (value.icon !== undefined || value.icon_opacity !== undefined)) return null;
    if (variants.indexOf(variant) < 0 ||
        typeof value.color !== "string" || !/^#[0-9a-f]{6}$/.test(value.color) ||
        !integer(value.grain, 0, 100) || !integer(value.speed, 0, 200) || !integer(value.darkness, 0, 100) ||
        typeof value.eye !== "boolean" || !integer(value.eye_size, 40, 128) ||
        icons.indexOf(icon) < 0 || !integer(iconOpacity, 0, 100)) return null;
    var extra = defaults();
    if (extended) {
        if (typeof value.mask_color !== "string" || !/^#[0-9a-f]{6}$/.test(value.mask_color) ||
            imageFits.indexOf(value.image_fit) < 0 || !validPath(value.shader_path, true) ||
            !validPath(value.icon_path, false) || !validPath(value.image_path, false)) return null;
        for (var e = 0; e < extraFields.length; ++e) extra[extraFields[e]] = value[extraFields[e]];
    }
    return { variant: variant, color: value.color, grain: value.grain, speed: value.speed,
             darkness: value.darkness, eye: value.eye, eye_size: value.eye_size, icon: icon, icon_opacity: iconOpacity,
             mask_color: extra.mask_color, image_fit: extra.image_fit, shader_path: extra.shader_path, icon_path: extra.icon_path, image_path: extra.image_path };
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
    if ((key === "color" || key === "mask_color") && typeof next === "string" && /^#[0-9a-fA-F]{6}$/.test(next)) next = next.toLowerCase();
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
        if ((keys[i] === "color" || keys[i] === "mask_color") && typeof next === "string") next = next.toLowerCase();
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
                 eye: "--eye", eye_size: "--eye-size", icon: "--icon", icon_opacity: "--icon-opacity",
                 mask_color: "--mask-color", image_fit: "--image-fit", shader_path: "--shader-path", icon_path: "--icon-path", image_path: "--image-path"};
    var result = ["configure"], seen = {};
    for (var i = 0; i < keys.length; ++i) {
        var key = keys[i];
        if (fields.indexOf(key) < 0 || seen[key]) return [];
        seen[key] = true;
        result.push(names[key], key === "eye" ? (p.eye ? "on" : "off") : String(p[key]));
    }
    return result;
}
