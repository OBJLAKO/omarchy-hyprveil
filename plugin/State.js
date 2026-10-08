.import "Appearance.js" as Appearance
// Pure state parser, shared with the adversarial-input tests. Never retain
// arbitrary status fields: they can contain paths or future client metadata.
var modes = ["omit", "black", "spoiler", "image"];

function unknown() {
    return { known: false, loaded: false, enabled: false, mode: "unknown", desiredMode: "black", spoilerFallback: false, appearance: Appearance.defaults() };
}

function parse(text) {
    if (typeof text !== "string" || text.length > 32768) return unknown();
    try {
        var raw = JSON.parse(text);
        if (!raw || typeof raw !== "object" || Array.isArray(raw) ||
            typeof raw.loaded !== "boolean" || typeof raw.enabled !== "boolean" ||
            modes.indexOf(raw.desired_mode) < 0) return unknown();
        var appearance = Appearance.parse(raw.appearance);
        if (!appearance) return unknown();
        if (!raw.loaded) {
            if (raw.status !== null) return unknown();
            return { known: true, loaded: false, enabled: raw.enabled,
                     mode: "native", desiredMode: raw.desired_mode, spoilerFallback: false, appearance: appearance };
        }
        var s = raw.status;
        if (!s || typeof s !== "object" || Array.isArray(s) ||
            s.session !== "live" || s.local_dump !== "disabled-in-live" ||
            modes.indexOf(s.mode) < 0 || !Appearance.equal(appearance, s.appearance)) return unknown();
        if (s.mode === "spoiler" && ["not-loaded", "ready", "black-fallback"].indexOf(s.spoiler_status) < 0)
            return unknown();
        return { known: true, loaded: true, enabled: raw.enabled,
                 mode: s.mode, desiredMode: raw.desired_mode,
                 spoilerFallback: s.mode === "spoiler" && s.spoiler_status === "black-fallback", appearance: appearance };
    } catch (e) {
        return unknown();
    }
}

function label(mode, spoilerFallback) {
    if (mode === "spoiler" && spoilerFallback) return "Спойлер недоступен: используется чёрная маска";
    if (mode === "spoiler") return "Спойлер";
    if (mode === "omit") return "Полностью скрыть";
    if (mode === "black") return "Обычная маска";
    if (mode === "image") return "Своя картинка";
    if (mode === "native") return "Hyprveil не загружен";
    return "Состояние не подтверждено";
}

function allowed(action, state) {
    if (!state || !state.known) return false;
    if (action === "start" || action === "enable") return !state.loaded;
    return state.loaded && ["black", "omit", "spoiler", "reload-config"].indexOf(action) >= 0;
}
