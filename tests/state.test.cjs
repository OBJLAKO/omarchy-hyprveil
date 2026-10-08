const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {spawnSync} = require('node:child_process');
const appearance = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'Appearance.js'), 'utf8'), appearance);
const i18n = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "I18n.js"), "utf8").replace(/^\.pragma[^\n]*\n/, ""), i18n);
const model = vm.createContext({Appearance: appearance, I18n: i18n});
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'State.js'), 'utf8').replace(/^\.import[^\n]*\n/gm, ''), model);
const parse = value => JSON.parse(JSON.stringify(model.parse(typeof value === 'string' ? value : JSON.stringify(value))));
const defaults = () => JSON.parse(JSON.stringify(appearance.defaults()));
const sample = mode => ({enabled: true, loaded: true, desired_mode: mode, appearance: defaults(),
    status: {session: 'live', local_dump: 'disabled-in-live', mode, spoiler_status: 'ready', appearance: defaults()}});
let count = 0;
function test(name, fn) { fn(); console.log('ok', ++count, name); }
test('all live modes require attested status', () => {
    for (const mode of ['omit', 'black', 'spoiler', 'image']) {
        const state = parse(sample(mode));
        assert.equal(state.known, true);
        assert.equal(state.loaded, true);
        assert.equal(state.mode, mode);
    }
});
test('native status is a known unloaded state', () => {
    assert.deepEqual(parse({enabled: true, loaded: false, desired_mode: 'black', status: null, appearance: defaults()}),
        {known: true, loaded: false, enabled: true, mode: 'native', desiredMode: 'black', spoilerFallback: false, appearance: defaults()});
});
test('spoiler allocation failure honestly reports safe black fallback', () => {
    const raw = sample('spoiler');
    raw.status.spoiler_status = 'black-fallback';
    const state = parse(raw);
    assert.equal(state.known, true);
    assert.equal(state.spoilerFallback, true);
    assert.equal(model.label(state.mode, state.spoilerFallback), 'Spoiler unavailable: using a black mask');
    raw.status.spoiler_status = 'unknown';
    assert.equal(parse(raw).known, false);
});
test('bad JSON, huge output and wrong shape cannot grant actions', () => {
    for (const raw of ['', '{', 'null', '[]', 'true', '"spoiler"', ' '.repeat(32769), {},
        {enabled: true, loaded: 'false', desired_mode: 'black'},
        {enabled: true, loaded: false, desired_mode: 'black', status: {}},
        {...sample('spoiler'), status: {session: 'lab', local_dump: 'disabled-in-live', mode: 'spoiler'}},
        {...sample('black'), status: {session: 'live', local_dump: 'saved', mode: 'black'}},
        {...sample('black'), enabled: 1}, sample('unknown')]) {
        const state = parse(raw);
        assert.equal(state.known, false);
        for (const action of ['black', 'omit', 'spoiler', 'reload-config', 'stop', 'start', 'enable']) assert.equal(model.allowed(action, state), false);
    }
});
test('arbitrary future fields are not retained or displayed', () => {
    const raw = sample('spoiler');
    raw.status.title = '<b>secret</b>';
    raw.status.image_path = '/secret/path';
    raw.credentials = 'secret';
    assert.equal(JSON.stringify(parse(raw)).includes('secret'), false);
});
test('only allowlisted actions can be dispatched', () => {
    const live = parse(sample('spoiler'));
    for (const action of ['black', 'omit', 'spoiler', 'reload-config']) assert.equal(model.allowed(action, live), true);
    for (const action of ['stop', 'start', 'enable', 'image', 'disable', 'sh', 'spoiler;true', '__proto__']) assert.equal(model.allowed(action, live), false);
    const native = parse({enabled: false, loaded: false, desired_mode: 'spoiler', status: null, appearance: defaults()});
    for (const action of ['start', 'enable']) assert.equal(model.allowed(action, native), true);
    for (const action of ['black', 'omit', 'spoiler', 'reload-config', 'stop']) assert.equal(model.allowed(action, native), false);
});
test('actual native mode and appearance win over stale saved manifest values', () => {
    const raw = sample('spoiler');
    raw.desired_mode = 'omit';
    raw.appearance = {...defaults(), variant: 'telegram', grain: 65};
    raw.status.appearance = raw.appearance;
    raw.saved_appearance = defaults();
    raw.config_file = '/path/not/displayed/hyprveil-settings.lua';
    const state = parse(raw);
    assert.equal(state.known, true);
    assert.equal(state.mode, 'spoiler');
    assert.equal(state.desiredMode, 'omit');
    assert.equal(state.appearance.variant, 'telegram');
    assert.equal(state.appearance.grain, 65);
    assert.equal(JSON.stringify(state).includes('/path/'), false);
    assert.equal(model.allowed('reload-config;sh', state), false);
});
const privacy = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'Privacy.js'), 'utf8'), privacy);
test('privacy command uses public native API with a bounded address and stable identity', () => {
    const signature = 'synthetic-instance-123';
    const hidden = {state: 'hidden', address: '0x123', stable_id: '402653184', native_private: true, inherited: false};
    const command = JSON.parse(JSON.stringify(privacy.command(signature, hidden)));
    assert.deepEqual(command, ['/usr/bin/hyprctl', '-i', signature, 'eval',
        'local p=hl.plugin.hyprveil; assert(p,"Hyprveil unavailable"); local r,e=p.set_hidden("0x123","402653184",false); assert(r and r.address == "0x123" and r.stable_id == "402653184" and r.state == "visible",e or "Hyprveil privacy not confirmed")']);
    const visible = {...hidden, state: 'visible', native_private: false};
    assert.equal(privacy.command(signature, visible)[4].includes('p.set_hidden("0x123","402653184",true)'), true);
    assert.equal(privacy.allowed(signature, false, false, hidden), true);
    assert.equal(privacy.allowed(signature, true, false, hidden), false);
    assert.equal(privacy.allowed(signature, false, true, hidden), false);
    for (const invalid of ['', '.', '..', '../other', 'x/y', 'x;sh', '$(id)', 'x\n', 'x'.repeat(161), null, 12]) {
        assert.equal(privacy.validSignature(invalid), false);
        assert.equal(privacy.command(invalid, hidden).length, 0);
        assert.equal(privacy.allowed(invalid, false, false), false);
    }
    for (const invalid of ['', '0x', '0x' + 'a'.repeat(17), '0x123";error("x")', '0x123\n', null, 12])
        assert.equal(privacy.command(signature, {...hidden, address: invalid}).length, 0);
    for (const invalid of ['none', 'unknown', 'visible;sh', null])
        assert.equal(privacy.command(signature, {...hidden, state: invalid}).length, 0);
    for (const invalid of ['', '0', '01', '1.0', '1e6', '1' + '0'.repeat(20), '18446744073709551616', '9'.repeat(20), '1";error("x")', 402653184, null])
        assert.equal(privacy.command(signature, {...hidden, stable_id: invalid}).length, 0);
    assert.equal(privacy.command(signature, {...hidden, native_private: false, inherited: true}).length, 0);
    assert.equal(privacy.command(signature, {...hidden, address: '0xABC'})[4].includes('"0xabc"'), true);
    assert.equal(privacy.validSignature(signature), true);
    assert.equal(privacy.command(signature).length, 0);
});
test('watcher privacy parser rejects ambiguous states and inherited-only toggles', () => {
    const inherited = {state: 'hidden', address: '0x123', stable_id: '402653184', native_private: false, inherited: true};
    assert.equal(privacy.parse(JSON.stringify(inherited)).state, 'hidden');
    assert.equal(privacy.toggleAllowed(inherited), false);
    const visible = {state: 'visible', address: '0x123', stable_id: '402653184', native_private: false, inherited: false};
    assert.equal(privacy.toggleAllowed(visible), true);
    for (const raw of ['{}', 'null', '{', JSON.stringify({...visible, title: 'secret'}),
        JSON.stringify({...inherited, native_private: true}), JSON.stringify({...visible, address: '0x123;sh'}),
        JSON.stringify({...visible, stable_id: undefined}), JSON.stringify({...visible, stable_id: 402653184})])
        assert.equal(privacy.parse(raw).state, 'unknown');
});
test('native Lua setter is idempotent and rejects focus, identity and inherited state changes', () => {
    for (const clicked of ['visible', 'hidden']) {
        const expression = privacy.command('synthetic-instance', {state: clicked, address: '0x123', stable_id: '402653184',
            native_private: clicked === 'hidden', inherited: false})[4];
        for (const [focused, actual, stable, inherited] of [['0x123', false, 402653184, false], ['0x123', true, 402653184, false],
            ['0x456', false, 402653184, false], [null, true, null, false], ['0x123', false, 402653185, false],
            ['0x123', true, 402653185, false], ['0x123', true, 402653184, true]]) {
            const lua = `local window=${focused === null ? 'nil' : '{address=' + JSON.stringify(focused) + ',stable_id=' + stable + ',hidden=' + actual + ',inherited=' + inherited + '}'}
local called=0
local module={}
function module.set_hidden(address, stable_id, hidden)
  assert(type(address)=='string' and type(stable_id)=='string' and type(hidden)=='boolean')
  if not window or window.address~=address or tostring(window.stable_id)~=stable_id or window.inherited then return nil,'window changed' end
  called=called+1; window.hidden=hidden
  return {state=hidden and 'hidden' or 'visible',address=address,stable_id=stable_id,native_private=hidden,inherited=false}
end
hl={plugin={hyprveil=module}}
function require() error('private user modules must not be required') end
local ok=pcall(function() ${expression} end)
if ${focused === '0x123' && stable === 402653184 && !inherited} then assert(ok and called==1 and window.hidden==${clicked === 'visible'})
else assert(not ok and called==0) end
print('passed')`;
            const result = spawnSync('/usr/bin/lua', ['-e', lua], {encoding: 'utf8', timeout: 2000,
                env: {PATH: '/usr/bin:/bin', LANG: 'C.UTF-8'}});
            assert.equal(result.status, 0, result.stderr || String(result.error || ''));
            assert.equal(result.stdout.trim(), 'passed');
        }
        const malformed = `hl={plugin={hyprveil={set_hidden=function() return {state='${clicked}',address='0x123',stable_id='402653184'} end}}}
assert(not pcall(function() ${expression} end))`;
        assert.equal(spawnSync('/usr/bin/lua', ['-e', malformed], {encoding: 'utf8', timeout: 2000,
            env: {PATH: '/usr/bin:/bin', LANG: 'C.UTF-8'}}).status, 0);
    }
});
test('full uint64 identities preserve decimal strings through parsing and executable Lua', () => {
    const target = {state: 'visible', address: '0x123', stable_id: '18446744073709551615', native_private: false, inherited: false};
    for (const id of ['1', '9007199254740993', '10000000000000000000', target.stable_id]) {
        assert.equal(privacy.validStableId(id), true);
        assert.equal(privacy.parse(JSON.stringify({...target, stable_id: id})).stable_id, id);
        assert.equal(privacy.command('synthetic-instance', {...target, stable_id: id})[4].includes('"' + id + '"'), true);
    }
    for (const id of ['0', '00', '018446744073709551615', '18446744073709551616', '184467440737095516150',
        '1e19', '١', 18446744073709551615n, Number('18446744073709551615')]) {
        assert.equal(privacy.validStableId(id), false);
        assert.equal(privacy.command('synthetic-instance', {...target, stable_id: id}).length, 0);
    }
    for (const clicked of ['visible', 'hidden']) for (const actualId of [target.stable_id, '18446744073709551614']) {
        const expression = privacy.command('synthetic-instance', {...target, state: clicked, native_private: clicked === 'hidden'})[4];
        const lua = `local called=0; local actual_id='${actualId}'
hl={plugin={hyprveil={set_hidden=function(address,id,hidden)
  assert(type(id)=='string' and id=='18446744073709551615')
  if actual_id~=id then return nil,'identity changed' end
  called=called+1
  return {state=hidden and 'hidden' or 'visible',address=address,stable_id=id,native_private=hidden,inherited=false}
end}}}
local ok=pcall(function() ${expression} end)
assert(ok==${actualId === target.stable_id} and called==${actualId === target.stable_id ? 1 : 0})`;
        const result = spawnSync('/usr/bin/lua', ['-e', lua], {encoding: 'utf8', timeout: 2000,
            env: {PATH: '/usr/bin:/bin', LANG: 'C.UTF-8'}});
        assert.equal(result.status, 0, result.stderr || String(result.error || ''));
    }
});
test('appearance is exact, canonical, bounded and cannot carry opacity or commands', () => {
    assert.equal(appearance.parse(defaults()).variant, 'satin');
    for (const [key, low, high] of [['grain', 0, 100], ['speed', 0, 200], ['darkness', 0, 100], ['eye_size', 40, 128]]) {
        for (const good of [low, high]) assert.equal(appearance.parse({...defaults(), [key]: good})[key], good);
        for (const bad of [low - 1, high + 1, 50.5, '50', true, null, NaN, Infinity])
            assert.equal(appearance.parse({...defaults(), [key]: bad}), null);
    }
    for (const bad of [{...defaults(), opacity: 0.5}, {...defaults(), eye: 'false'}, {...defaults(), variant: 'satin;sh'},
        {...defaults(), color: '#FFFFFF'}, {...defaults(), color: '#ffffff;sh'}, {...defaults(), color: '#fff'}])
        assert.equal(appearance.command(bad).length, 0);
    assert.equal(appearance.update(defaults(), 'color', '#AABBCD').color, '#aabbcd');
    assert.equal(appearance.update(defaults(), '__proto__', {}), null);
    const changed = appearance.update(defaults(), 'variant', 'telegram');
    assert.equal(changed.grain, 50); assert.equal(changed.speed, 100); assert.equal(changed.eye_size, 80);
    assert.deepEqual(JSON.parse(JSON.stringify(appearance.command(changed))), ['configure', '--variant', 'telegram', '--color', '#ffffff',
        '--grain', '50', '--speed', '100', '--darkness', '50', '--eye', 'on', '--eye-size', '80']);
});
test('controller and native appearance must match before UI reports healthy status', () => {
    const raw = sample('spoiler');
    raw.status.appearance.grain = 51;
    assert.equal(parse(raw).known, false);
    raw.appearance.grain = 51;
    assert.equal(parse(raw).known, true);
});
console.log(`passed ${count} state, appearance and privacy tests`);
test('English is the fallback and Russian locales select complete presentation text', () => {
    for (const locale of ['ru', 'ru_RU', 'ru-RU', 'RU_RU.UTF-8', ' ru_BY ']) assert.equal(i18n.language(locale), 'ru');
    for (const locale of [undefined, null, {}, 42, '', 'C', 'en_US', 'de_DE', 'rust', '__proto__', 'ru<script>']) assert.equal(i18n.language(locale), 'en');
    for (const [key, translations] of Object.entries(i18n.strings)) {
        assert.equal(translations.length, 2);
        for (const value of translations) assert.equal(typeof value === 'string' && value.length > 0, true, key);
        assert.equal(i18n.text(key, 'en_US'), translations[0]);
        assert.equal(i18n.text(key, 'ru_RU'), translations[1]);
        assert.equal(i18n.text(key, 'unknown'), translations[0]);
    }
    for (const key of ['__proto__', 'constructor', 'not_a_key', null, {}]) assert.equal(i18n.text(key, 'ru'), '');
    for (const setting of [undefined, null, {}, [], '', 'auto', 'RU', 'unknown', '__proto__']) {
        assert.equal(i18n.selectLanguage(setting, 'ru_RU'), 'ru');
        assert.equal(i18n.selectLanguage(setting, 'en_US'), 'en');
    }
    assert.equal(i18n.selectLanguage('en', 'ru_RU'), 'en');
    assert.equal(i18n.selectLanguage('ru', 'en_US'), 'ru');
    assert.equal(model.label('spoiler', true, 'ru_RU'), 'Спойлер недоступен: используется чёрная маска');
    assert.equal(model.label('__proto__', false), 'State unconfirmed');
});
test('localization is complete and leaves native parsing and command data untouched', () => {
    for (const file of ['Panel.qml', 'BarWidget.qml', 'WindowPrivacy.qml', 'AppearanceEditor.qml']) {
        const qml = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
        assert.equal(/[А-Яа-яЁё]/u.test(qml), false, file);
        for (const match of qml.matchAll(/\.tr\("([a-z_]+)"\)/g)) assert.equal(Object.hasOwn(i18n.strings, match[1]), true, match[1]);
    }
    const raw = sample('spoiler'), before = JSON.stringify(raw), parsed = parse(raw);
    for (const locale of ['en', 'ru']) {
        model.label(parsed.mode, parsed.spoilerFallback, locale);
        i18n.text('prerequisite', locale);
        assert.equal(JSON.stringify(raw), before);
        assert.equal(JSON.stringify(parse(raw)), JSON.stringify(parsed));
        assert.equal(model.allowed('spoiler', parsed), true);
    }
});
console.log('passed 2 locale completeness and presentation-only tests');
