pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Ui
import "Notifications.js" as Notifications
import "Appearance.js" as Appearance
import "I18n.js" as I18n

Column {
    id: root
    property string language: "en"
    property var profile: null
    property bool externalBusy: false
    property bool active: false
    property var draft: Notifications.defaults()
    property var edits: ({})
    property var submitted: null
    property int revision: 0
    property bool blocked: false
    property string error: ""
    property string fontFamily: "Adwaita Sans"
    readonly property bool supported: profile !== null
    readonly property bool dirty: Object.keys(edits).length > 0
    readonly property bool saving: submitted !== null
    signal saveRequested(var arguments)
    signal closeRequested()
    function tr(key) { return I18n.text(key, language) }
    function sync() {
        if (!profile) return
        var next = Notifications.parse(profile)
        if (!next) return
        Object.keys(edits).forEach(function(k) { next[k] = root.edits[k].value })
        draft = Notifications.parse(next)
    }
    onProfileChanged: sync()
    onExternalBusyChanged: if (!externalBusy) Qt.callLater(flush)
    function edit(patch) {
        var next = Notifications.update(draft,patch)
        if (!next) return
        var pending = Object.assign({},edits)
        revision++
        Object.keys(patch).forEach(function(k) { pending[k]={value:next[k],revision:root.revision} })
        edits=pending; draft=next; blocked=false; error=""; debounce.restart()
    }
    function flush() {
        if (!dirty || blocked || !supported || externalBusy || saving || debounce.running) return
        submitted=Object.assign({},edits)
        saveRequested(Notifications.command(draft,Object.keys(submitted)))
    }
    function failed(message) {
        blocked=true; error=message; submitted=null
    }
    function confirm(value) {
        var confirmed=Notifications.parse(value), pending=Object.assign({},edits)
        if (!submitted) return
        var keys=Object.keys(submitted)
        if (!confirmed || keys.some(function(k) { return confirmed[k] !== root.submitted[k].value })) {
            failed(root.tr("notification_unconfirmed")); return
        }
        keys.forEach(function(k) {
            if (pending[k] && pending[k].revision === root.submitted[k].revision) delete pending[k]
        })
        edits=pending; submitted=null; sync(); Qt.callLater(flush)
    }
    function commitInputs() {
        notificationColor.commit()
        notificationImage.commit()
        notificationAppearance.commitPaths()
        if (!notificationAppearance.colorValid) notificationAppearance.syncColor()
        debounce.stop()
        Qt.callLater(flush)
    }
    component DraftField: SafeTextField {
        property string savedValue: ""
        property bool modified: false
        property bool path: false
        signal committed(string value)
        text:savedValue
        onSavedValueChanged:if (!activeFocus && !modified) text=savedValue
        onTextEdited:modified=true
        function commit() {
            if (!modified) return
            var valid=path ? Appearance.validPath(text,false) && text!=="" : /^#[0-9a-fA-F]{6}$/.test(text)
            if (valid) { modified=false; committed(path ? text : text.toLowerCase()) }
        }
        onEditingFinished:commit()
        onAccepted:commit()
    }
    Timer { id:debounce; interval:240; onTriggered:root.flush() }
    spacing: Style.space(12)
    Text {
        width:parent.width; wrapMode:Text.WordWrap; textFormat:Text.PlainText
        text:root.tr("notification_hint")
        color:Color.muted; font.family:root.fontFamily; font.pixelSize:Style.space(11)
    }
    Text {
        visible:!root.supported; width:parent.width; wrapMode:Text.WordWrap
        text:root.tr("notification_core_required")
        color:Color.muted; font.family:root.fontFamily; font.pixelSize:Style.space(12)
    }
    Button {
        width:parent.width; visible:root.supported; selected:root.draft.enabled; focusable:true
        text:root.draft.enabled ? root.tr("notification_enabled") : root.tr("notification_disabled")
        fontFamily:root.fontFamily; fontSize:Style.space(12)
        enabled:!root.externalBusy || root.saving
        onClicked:root.edit({enabled:!root.draft.enabled})
    }
    Flow {
        width:parent.width; spacing:Style.space(6); visible:root.supported
        Repeater {
            model:[{mode:"omit",label:"omit"},{mode:"color",label:"solid_color"},{mode:"spoiler",label:"spoiler"},{mode:"image",label:"custom_image"}]
            delegate:Button {
                required property var modelData
                text:root.tr(modelData.label); selected:root.draft.mode===modelData.mode
                fontFamily:root.fontFamily; fontSize:Style.space(11); focusable:true
                enabled:!root.externalBusy || root.saving
                onClicked:root.edit({mode:modelData.mode})
            }
        }
    }
    DraftField {
        id:notificationColor
        width:parent.width; visible:root.supported && root.draft.mode==="color"
        language:root.language; savedValue:root.draft.mask_color; foreground:Color.popups.text
        font.family:root.fontFamily; font.pixelSize:Style.space(12)
        onCommitted:function(value) { root.edit({mask_color:value}) }
    }
    DraftField {
        id:notificationImage
        width:parent.width; visible:root.supported && root.draft.mode==="image"
        placeholderText:root.tr("image_path_placeholder")
        language:root.language; path:true; savedValue:root.draft.image_path; foreground:Color.popups.text
        font.family:root.fontFamily; font.pixelSize:Style.space(12)
        onCommitted:function(value) { root.edit({image_path:value}) }
    }
    Flow {
        width:parent.width; spacing:Style.space(6); visible:root.supported && root.draft.mode==="image"
        Repeater {
            model:Appearance.imageFits
            delegate:Button {
                required property string modelData
                text:root.tr("image_"+modelData); selected:root.draft.image_fit===modelData; focusable:true
                fontFamily:root.fontFamily; fontSize:Style.space(11)
                onClicked:root.edit({image_fit:modelData})
            }
        }
    }
    AppearanceEditor {
        id:notificationAppearance
        width:parent.width; visible:root.supported && root.draft.mode==="spoiler"
        language:root.language; draft:Notifications.appearance(root.draft); assetsSupported:true; mode:root.draft.mode
        dirty:root.dirty; busy:root.externalBusy && !root.saving; saving:root.saving
        animate:root.active && visible; fontFamily:root.fontFamily
        onEdited:function(key,value) { var patch={};patch[key]=value;root.edit(patch) }
        onEditedPatch:function(patch) { root.edit(patch) }
        onVariantPicked:function(variant) { root.edit({variant:variant}) }
        onBuiltinIconPicked:function(icon) { root.edit({icon:icon,icon_path:"",eye:icon!=="none"}) }
        onResetRequested:root.edit(Appearance.defaults())
        onCloseRequested:{root.commitInputs();root.closeRequested()}
    }
    Text {
        width:parent.width; wrapMode:Text.WordWrap; visible:root.error!=="" || root.dirty
        text:root.error || root.tr("notification_saving")
        color:root.error!=="" ? Color.urgent : Color.muted
        font.family:root.fontFamily; font.pixelSize:Style.space(11)
    }
    Button {
        visible:root.blocked; text:root.tr("notification_retry"); focusable:true
        fontFamily:root.fontFamily; fontSize:Style.space(11)
        onClicked:{root.blocked=false;root.error="";root.flush()}
    }
}
