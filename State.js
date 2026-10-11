.import "Appearance.js" as Appearance
.import "I18n.js" as I18n
// Pure state parser, shared with the adversarial-input tests. Never retain
// arbitrary status fields or future client metadata. Only the explicit local
// asset paths needed by the editor are retained.
var modes = ["omit", "black", "color", "spoiler", "image"];
var assetFields = ["mask_color", "image_fit", "shader_path", "icon_path"];

function unknown() {
    return { known: false, loaded: false, enabled: false, loadSupported: false, persistenceSupported: false, assetsSupported: false,
             mode: "unknown", desiredMode: "black", spoilerFallback: false, appearance: Appearance.defaults() };
}

function parse(text) {
    if (typeof text !== "string" || text.length > 32768) return unknown();
    try {
        var raw = JSON.parse(text);
        if (!raw || typeof raw !== "object" || Array.isArray(raw) ||
            typeof raw.loaded !== "boolean" || typeof raw.enabled !== "boolean" ||
            (raw.load_supported !== undefined && typeof raw.load_supported !== "boolean") ||
            (raw.persistence_supported !== undefined && typeof raw.persistence_supported !== "boolean") ||
            modes.indexOf(raw.desired_mode) < 0) return unknown();
        var appearance = Appearance.parse(raw.appearance);
        if (!appearance) return unknown();
        for (var i = 0; i < Appearance.extraFields.length; ++i) {
            var key = Appearance.extraFields[i];
            var outer = raw[key] === undefined ? appearance[key] : raw[key];
            if (raw.loaded && raw.status && raw.status[key] !== undefined && raw.status[key] !== outer) return unknown();
            appearance[key] = outer;
        }
        appearance = Appearance.parse(appearance);
        if (!appearance) return unknown();
        if (!raw.loaded) {
            if (raw.status !== null) return unknown();
            return { known: true, loaded: false, enabled: raw.enabled,
                     loadSupported: raw.load_supported !== false, persistenceSupported: raw.persistence_supported !== false, assetsSupported: false,
                     mode: "native", desiredMode: raw.desired_mode, spoilerFallback: false, appearance: appearance };
        }
        var s = raw.status;
        if (!s || typeof s !== "object" || Array.isArray(s) ||
            s.session !== "live" || s.local_dump !== "disabled-in-live" ||
            modes.indexOf(s.mode) < 0) return unknown();
        var nativeAppearance = Appearance.parse(s.appearance);
        if (!nativeAppearance) return unknown();
        for (var j = 0; j < Appearance.extraFields.length; ++j) nativeAppearance[Appearance.extraFields[j]] = appearance[Appearance.extraFields[j]];
        if (!Appearance.equal(appearance, nativeAppearance)) return unknown();
        if (s.mode === "spoiler" && ["not-loaded", "pending", "ready", "custom-ready", "black-fallback", "color-fallback"].indexOf(s.spoiler_status) < 0)
            return unknown();
        // The new client supplies defaults for old native releases. Only
        // explicit, agreeing native fields prove rendering support.
        var assetsSupported = assetFields.every(function(key) {
            return raw[key] !== undefined && s[key] !== undefined && raw[key] === s[key];
        });
        return { known: true, loaded: true, enabled: raw.enabled,
                 loadSupported: raw.load_supported !== false, persistenceSupported: raw.persistence_supported !== false, assetsSupported: assetsSupported,
                 mode: s.mode, desiredMode: raw.desired_mode,
                 spoilerFallback: s.mode === "spoiler" && ["black-fallback", "color-fallback"].indexOf(s.spoiler_status) >= 0, appearance: appearance };
    } catch (e) {
        return unknown();
    }
}

function label(mode, spoilerFallback, locale) {
    if (mode === "spoiler" && spoilerFallback) return I18n.text("spoiler_fallback", locale);
    var key = {spoiler: "spoiler", omit: "omit", black: "legacy_black", color: "solid_color", image: "custom_image", native: "unloaded"};
    return I18n.text(Object.prototype.hasOwnProperty.call(key, mode) ? key[mode] : "unknown", locale);
}

function allowed(action, state) {
    if (!state || !state.known) return false;
    if (action === "start" || action === "enable") return !state.loaded && state.loadSupported;
    if (action === "color" && !state.assetsSupported) return false;
    return state.loaded && ["black", "color", "image", "omit", "spoiler", "reload-config"].indexOf(action) >= 0;
}

function command(action, state, appearance) {
    if (!allowed(action, state)) return [];
    if (action !== "image" && action !== "color") return [action];
    var value = Appearance.parse(appearance);
    if (!value) return [];
    if (action === "color") return ["color", value.mask_color];
    if (!value.image_path) return [];
    return state.assetsSupported ? ["image", value.image_path, "--fit", value.image_fit] : ["image", value.image_path];
}
