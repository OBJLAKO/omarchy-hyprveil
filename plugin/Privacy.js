function validSignature(signature) {
    return typeof signature === "string" && signature.length <= 160 && signature !== "." && signature !== ".." && /^[A-Za-z0-9_.-]+$/.test(signature);
}
function validStableId(value) {
    // Comparing two canonical decimal strings avoids JavaScript's 53-bit
    // number limit. Equal-length ASCII digit strings have numeric order.
    return typeof value === "string" && /^[1-9][0-9]{0,19}$/.test(value) &&
        (value.length < 20 || value <= "18446744073709551615");
}
// Interpolate only a canonical hex address and decimal stable identity.
// The public native setter checks active focus and both IDs atomically.
function command(signature, target) {
    var p = normalized(target);
    if (!validSignature(signature) || !toggleAllowed(p)) return [];
    var expression = 'local p=hl.plugin.hyprveil; assert(p,"Hyprveil unavailable"); local r,e=p.set_hidden("' + p.address +
        '","' + p.stable_id + '",' + (p.state === "visible" ? "true" : "false") +
        '); assert(r and r.address == "' + p.address + '" and r.stable_id == "' + p.stable_id +
        '" and r.state == "' + (p.state === "visible" ? "hidden" : "visible") + '",e or "Hyprveil privacy not confirmed")';
    return ["/usr/bin/hyprctl", "-i", signature, "eval", expression];
}

function unknown() { return { state: "unknown", address: "", stable_id: "", native_private: false, inherited: false }; }
function normalized(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw) || Object.keys(raw).length !== 5 ||
        ["hidden", "visible", "none", "unknown"].indexOf(raw.state) < 0 || typeof raw.address !== "string" ||
        typeof raw.stable_id !== "string" || typeof raw.native_private !== "boolean" || typeof raw.inherited !== "boolean") return unknown();
    if (raw.state === "none" || raw.state === "unknown") {
        if (raw.address !== "" || raw.stable_id !== "" || raw.native_private || raw.inherited) return unknown();
    } else {
        if (!/^0x[0-9a-fA-F]{1,16}$/.test(raw.address)) return unknown();
        if (!validStableId(raw.stable_id)) return unknown();
        if (raw.state === "visible" && (raw.native_private || raw.inherited)) return unknown();
        if (raw.state === "hidden" && !raw.native_private && !raw.inherited) return unknown();
        if (raw.native_private && raw.inherited) return unknown();
    }
    return { state: raw.state, address: raw.address.toLowerCase(), stable_id: raw.stable_id, native_private: raw.native_private, inherited: raw.inherited };
}
function parse(text) {
    if (typeof text !== "string" || text.length > 2048) return unknown();
    try { return normalized(JSON.parse(text)); } catch (e) { return unknown(); }
}
function toggleAllowed(value) {
    var p = normalized(value);
    return (p.state === "hidden" || p.state === "visible") && (!p.inherited || p.native_private);
}
function allowed(signature, privacyBusy, modeBusy, privacy) {
    var p = normalized(privacy);
    return !privacyBusy && !modeBusy && command(signature, p).length === 5;
}
