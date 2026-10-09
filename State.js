.import "Appearance.js" as Appearance
.import "I18n.js" as I18n
// Pure state parser, shared with the adversarial-input tests. Never retain
// arbitrary status fields: they can contain paths or future client metadata.
var modes = ["omit", "black", "spoiler", "image"];

function unknown() {
    return { known: false, loaded: false, enabled: false, loadSupported: false, persistenceSupported: false,
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
        if (!raw.loaded) {
            if (raw.status !== null) return unknown();
            return { known: true, loaded: false, enabled: raw.enabled,
                     loadSupported: raw.load_supported !== false, persistenceSupported: raw.persistence_supported !== false,
                     mode: "native", desiredMode: raw.desired_mode, spoilerFallback: false, appearance: appearance };
        }
        var s = raw.status;
        if (!s || typeof s !== "object" || Array.isArray(s) ||
            s.session !== "live" || s.local_dump !== "disabled-in-live" ||
            modes.indexOf(s.mode) < 0 || !Appearance.equal(appearance, s.appearance)) return unknown();
        if (s.mode === "spoiler" && ["not-loaded", "ready", "black-fallback"].indexOf(s.spoiler_status) < 0)
            return unknown();
        return { known: true, loaded: true, enabled: raw.enabled,
                 loadSupported: raw.load_supported !== false, persistenceSupported: raw.persistence_supported !== false,
                 mode: s.mode, desiredMode: raw.desired_mode,
                 spoilerFallback: s.mode === "spoiler" && s.spoiler_status === "black-fallback", appearance: appearance };
    } catch (e) {
        return unknown();
    }
}

function label(mode, spoilerFallback, locale) {
    if (mode === "spoiler" && spoilerFallback) return I18n.text("spoiler_fallback", locale);
    var key = {spoiler: "spoiler", omit: "omit", black: "black", image: "custom_image", native: "unloaded"};
    return I18n.text(Object.prototype.hasOwnProperty.call(key, mode) ? key[mode] : "unknown", locale);
}

function allowed(action, state) {
    if (!state || !state.known) return false;
    if (action === "start" || action === "enable") return !state.loaded && state.loadSupported;
    return state.loaded && ["black", "omit", "spoiler", "reload-config"].indexOf(action) >= 0;
}
