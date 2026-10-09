.pragma library
// Presentation only. No strings enter commands, status parsing or privacy checks.
var strings = {
    "autosave_hint": ["Changes save automatically", "Изменения сохраняются автоматически"],
    "autosaving": ["Saving…", "Сохраняем…"],
    "color_invalid": ["Enter a six-digit color", "Введите цвет из шести цифр"],
    "setup_native": ["Set up / repair Hyprveil…", "Установить / восстановить Hyprveil…"],
    "signal": ["Signal", "Сигнал"],
    "aurora": ["Aurora", "Аврора"],
    "contour": ["Contour", "Контуры"],
    "radar": ["Radar", "Радар"],
    "error404": ["404", "404"],
    "matrix": ["Matrix", "Матрица"],
    "anonymous": ["Anonymous", "Аноним"],
    "glass": ["Liquid Glass", "Стекло"],
    "matte": ["Matte", "Матовая"],
    "hyprpm_enable_hint": [
        "Click Set up to build the native core in a terminal. It shows changes and asks first.",
        "Нажмите «Установить»: терминал покажет изменения и запросит подтверждение."
    ],
    "runtime_only": [
        "These settings affect this session. Add native Lua settings to keep them after login.",
        "Эти настройки действуют в текущем сеансе. Для сохранения после входа добавьте нативные настройки Lua."
    ],
    "status_unconfirmed": [
        "Could not confirm state. Refresh to check again.",
        "Не удалось подтвердить состояние. Обновите проверку."
    ],
    "appearance_applied": [
        "Appearance applied.",
        "Оформление применено."
    ],
    "appearance_applied_dirty": [
        "Appearance applied. New edits are still unapplied.",
        "Оформление применено. Новые изменения ещё не применены."
    ],
    "appearance_unconfirmed": [
        "Appearance unconfirmed. Your preview draft is preserved.",
        "Оформление не подтверждено. Изменения сохранены в предпросмотре."
    ],
    "loaded": [
        "Hyprveil loaded.",
        "Hyprveil загружен."
    ],
    "lua_reloaded_dirty": [
        "Lua reloaded. Your draft is still unapplied.",
        "Lua перечитана. Изменения в черновике ещё не применены."
    ],
    "lua_reloaded": [
        "Lua reloaded. Current settings are shown.",
        "Lua перечитана. Текущие настройки показаны."
    ],
    "setting_applied": [
        "Setting applied.",
        "Настройка применена."
    ],
    "state_changed": [
        "State changed after the command. Current style is shown above.",
        "Состояние изменилось после команды. Текущий стиль показан выше."
    ],
    "controller_timeout": [
        "Controller timed out. A fresh check is needed.",
        "Контроллер не ответил вовремя. Состояние требует новой проверки."
    ],
    "appearance_failed": [
        "Could not save appearance. Check Lua settings, then change a value to retry.",
        "Не удалось сохранить оформление. Проверьте Lua и измените настройку для повтора."
    ],
    "lua_failed": [
        "Could not reload Lua. Check your Hyprland configuration.",
        "Не удалось перечитать Lua. Проверьте конфигурацию Hyprland."
    ],
    "action_unconfirmed": [
        "Change unconfirmed. Check state or the controller log.",
        "Переключение не подтверждено. Проверьте состояние или журнал контроллера."
    ],
    "command_checking": [
        "Command completed. Confirming state…",
        "Команда выполнена. Проверяем состояние…"
    ],
    "query_timeout": [
        "State check timed out. Please try again.",
        "Проверка не ответила вовремя. Повторите её."
    ],
    "privacy": [
        "Privacy",
        "Приватность"
    ],
    "capture_subtitle": [
        "Hyprveil · screen capture",
        "Hyprveil · захват экрана"
    ],
    "changing": [
        "Changing…",
        "Смена…"
    ],
    "checking_short": [
        "Checking",
        "Проверка"
    ],
    "offline": [
        "No connection",
        "Нет связи"
    ],
    "spoiler": [
        "Spoiler",
        "Спойлер"
    ],
    "hidden_short": [
        "Omitted",
        "Скрыто"
    ],
    "mask_short": [
        "Black",
        "Маска"
    ],
    "image_short": [
        "Image",
        "Картинка"
    ],
    "unloaded_short": [
        "Not loaded",
        "Не загружен"
    ],
    "hiding": [
        "Hiding",
        "Скрытие"
    ],
    "appearance": [
        "Appearance",
        "Оформление"
    ],
    "changing_style": [
        "Changing style…",
        "Переключаем стиль…"
    ],
    "checking": [
        "Checking state…",
        "Проверяем состояние…"
    ],
    "hidden_style": [
        "Protected window style",
        "Вид скрытого окна"
    ],
    "spoiler_detail": [
        "Soft shimmer on a dark surface",
        "Мягкое мерцание на тёмной поверхности"
    ],
    "omit": [
        "Omit window",
        "Полностью скрыть"
    ],
    "omit_detail": [
        "Exclude the window from capture",
        "Окно полностью исключается из захвата"
    ],
    "black": [
        "Black mask",
        "Обычная маска"
    ],
    "black_detail": [
        "Plain opaque black fill",
        "Ровная чёрная заливка"
    ],
    "desktop_unchanged": [
        "Windows look unchanged on your own screen.",
        "На вашем экране окна выглядят как прежде."
    ],
    "load": [
        "Load Hyprveil",
        "Загрузить Hyprveil"
    ],
    "enable": [
        "Enable Hyprveil",
        "Включить Hyprveil"
    ],
    "reset_hiding": [
        "Restore omission",
        "Вернуть исходное скрытие"
    ],
    "refresh": [
        "Refresh state",
        "Обновить состояние"
    ],
    "omit_note": [
        "Protected windows are excluded from capture.",
        "Окна полностью исключаются из захвата."
    ],
    "lua_settings": [
        "Hyprland settings · Lua",
        "Настройки Hyprland · Lua"
    ],
    "reload_lua": [
        "Reload Lua",
        "Перечитать Lua"
    ],
    "reload_lua_hint": [
        "Apply ~/.config/hypr/hyprveil-settings.lua\nYour appearance draft is preserved.",
        "Применить изменения из ~/.config/hypr/hyprveil-settings.lua\nЧерновик оформления сохранится."
    ],
    "prism": [
        "Prism",
        "Призма"
    ],
    "grain": [
        "Grain",
        "Зернистость"
    ],
    "speed": [
        "Speed",
        "Скорость"
    ],
    "darkness": [
        "Darkness",
        "Затемнение"
    ],
    "art_icon_hint": ["This theme has a central motif. Advanced → None removes the overlay icon.", "В этой теме есть центральный рисунок. «Дополнительно» → «Без значка» убирает значок поверх него."],
    "privacy_icon": ["Privacy icon", "Значок приватности"],
    "icon_eye": ["Eye", "Глаз"],
    "icon_lock": ["Lock", "Замок"],
    "icon_shield": ["Shield", "Щит"],
    "icon_none": ["None", "Без значка"],
    "icon_size": ["Icon size", "Размер значка"],
    "icon_opacity": ["Icon opacity", "Непрозрачность значка"],
    "advanced": ["Advanced", "Дополнительно"],
    "crossed_eye": [
        "Crossed-out eye",
        "Перечёркнутый глаз"
    ],
    "eye_size": [
        "Eye size",
        "Размер глаза"
    ],
    "applying": [
        "Applying…",
        "Применяем…"
    ],
    "apply": [
        "Apply changes",
        "Применить изменения"
    ],
    "applied": [
        "Applied",
        "Применено"
    ],
    "reset_appearance": [
        "Reset appearance",
        "Сбросить оформление"
    ],
    "spoiler_only": [
        "Only the spoiler appearance changes. The hiding mode is preserved.",
        "Настройки меняют только спойлер. Выбранный способ скрытия сохраняется."
    ],
    "spoiler_later": [
        "Select Spoiler to see this appearance. The hiding mode is preserved.",
        "Оформление появится при выборе «Спойлер». Текущий способ скрытия сохранится."
    ],
    "window_hidden": [
        "Window hidden from capture",
        "Окно скрыто от захвата"
    ],
    "window_visible": [
        "Window visible in capture",
        "Окно видно в захвате"
    ],
    "window_none": [
        "No focused window",
        "Активное окно не выбрано"
    ],
    "window_unknown": [
        "Window state unavailable",
        "Статус окна недоступен"
    ],
    "inherited_hint": [
        "Inherited protection; toggle disabled",
        "Защита унаследована; переключение отключено"
    ],
    "window_click_hint": [
        "Left or middle click the bar icon",
        "ЛКМ или средняя кнопка по значку"
    ],
    "waiting": [
        "Waiting…",
        "Ждём…"
    ],
    "show": [
        "Show",
        "Показать"
    ],
    "hide": [
        "Hide",
        "Скрыть"
    ],
    "target_changed": [
        "Selected window changed. Please toggle again.",
        "Выбранное окно изменилось. Повторите переключение."
    ],
    "focus_changed": [
        "Focus changed. The new window state is shown.",
        "Выбрано другое окно. Его состояние показано."
    ],
    "privacy_dispatch_failed": [
        "Could not send the window privacy change.",
        "Не удалось отправить переключение приватности окна."
    ],
    "privacy_unconfirmed": [
        "Window change unconfirmed. Check state and try again.",
        "Переключение окна не подтверждено. Проверьте состояние и повторите."
    ],
    "tooltip_hidden": [
        "window hidden from capture",
        "окно скрыто от захвата"
    ],
    "tooltip_visible": [
        "window visible in capture",
        "окно видно в захвате"
    ],
    "tooltip_none": [
        "no focused window",
        "окно не выбрано"
    ],
    "tooltip_unknown": [
        "window state unavailable",
        "статус окна недоступен"
    ],
    "tooltip_inherited": [
        "\nInherited protection; toggling is disabled",
        "\nОкно наследует защиту; переключение отключено"
    ],
    "last_check": [
        "\nLast check: ",
        "\nПоследняя проверка: "
    ],
    "left_hint": [
        "\nLeft or middle click — show/hide window",
        "\nЛКМ или средняя кнопка — показать/скрыть окно"
    ],
    "right_hint": [
        "\nRight click — styles and appearance",
        "\nПКМ — стили и оформление"
    ],
    "spoiler_fallback": [
        "Spoiler unavailable: using a black mask",
        "Спойлер недоступен: используется чёрная маска"
    ],
    "custom_image": [
        "Custom image",
        "Своя картинка"
    ],
    "unloaded": [
        "Hyprveil is not loaded",
        "Hyprveil не загружен"
    ],
    "unknown": [
        "State unconfirmed",
        "Состояние не подтверждено"
    ],
    "prerequisite": [
        "Requires native Hyprveil 0.5.0. Install and enable the core with hyprpm, then reload its plugins.",
        "Нужен нативный Hyprveil 0.5.0. Установите и включите ядро через hyprpm, затем перечитайте его плагины."
    ],
    "setup_guide": [
        "Native setup guide",
        "Инструкция по установке ядра"
    ]
};

function language(locale) {
    return typeof locale === "string" && /^ru(?:[_-]|$)/i.test(locale.trim()) ? "ru" : "en";
}

function selectLanguage(setting, locale) {
    return setting === "en" || setting === "ru" ? setting : language(locale);
}

function text(key, locale) {
    if (typeof key !== "string" || !Object.prototype.hasOwnProperty.call(strings, key)) return "";
    return strings[key][language(locale) === "ru" ? 1 : 0];
}
