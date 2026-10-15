.import "Appearance.js" as Appearance
var fields = Appearance.fields.concat(["enabled", "mode", "namespace", "rounding"]);
function defaults() {
    return Object.assign(Appearance.defaults(), {enabled:false, mode:"omit", namespace:"omarchy-notifications", rounding:-1});
}
function appearance(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    var profile={};
    Appearance.fields.forEach(function(k) { profile[k]=value[k]; });
    return Appearance.parse(profile);
}
function parse(value) {
    var appearanceValue = appearance(value);
    if (!appearanceValue || typeof value.enabled !== "boolean" ||
        ["omit","black","color","image","spoiler"].indexOf(value.mode) < 0 ||
        typeof value.namespace !== "string" || !/^[a-zA-Z0-9_.-]{1,128}$/.test(value.namespace) ||
        !Appearance.integer(value.rounding,-1,64)) return null;
    return Object.assign(appearanceValue,{enabled:value.enabled,mode:value.mode,namespace:value.namespace,rounding:value.rounding});
}
function update(value, patch) {
    if (!patch || typeof patch !== "object" || Array.isArray(patch) || Object.keys(patch).some(function(k) {return fields.indexOf(k)<0;})) return null;
    return parse(Object.assign({},value,patch));
}
function command(value, keys) {
    var parsed=parse(value);
    if (!parsed || !Array.isArray(keys) || !keys.length) return [];
    var appearanceKeys=keys.filter(function(k) {return Appearance.fields.indexOf(k)>=0;});
    var args=appearanceKeys.length ? Appearance.command(appearance(parsed),appearanceKeys).slice(1) : [];
    var seen={};
    for (var i=0;i<keys.length;i++) {
        var k=keys[i];
        if (fields.indexOf(k)<0 || seen[k]) return [];
        seen[k]=true;
        if (Appearance.fields.indexOf(k)<0) args.push("--"+k,k==="enabled" ? (parsed[k]?"on":"off") : String(parsed[k]));
    }
    return ["notifications"].concat(args);
}
