#!/usr/bin/python3
"""Verify notification autosave through the real panel and delayed CLI child."""
import importlib.util
import json
from pathlib import Path

spec=importlib.util.spec_from_file_location('autosave',Path(__file__).with_name('qml-autosave.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
defaults=dict(fixture.DEFAULTS,api=1,enabled=False,mode='omit',namespace='omarchy-notifications',rounding=-1)
fixture.CONTROLLER=fixture.CONTROLLER.replace('extras = ("mask_color"', 'state.setdefault("notifications", '+repr(defaults)+')\nextras = ("notifications", "mask_color"')
marker='elif action == "configure":'
branch='''elif action == "notifications":
    time.sleep(.36)
    for flag,value in zip(sys.argv[2::2],sys.argv[3::2]):
        key=flag[2:].replace("-","_")
        state["notifications"][key] = value == "on" if key in ("enabled","eye") else int(value) if key in ("rounding","speed","grain","darkness","eye_size","icon_opacity") else value
    (home / "state.json").write_text(json.dumps(state))
    print("{}")
'''
fixture.CONTROLLER=fixture.CONTROLLER.replace(marker,branch+marker)
fixture.QML='''import QtQuick
import Quickshell
import "./plugin" as Plugin
ShellRoot {
 Item {id:host;property bool privacyBusy:false;property bool privacyDispatching:false;property var focusPrivacy:({state:"unknown",address:"",stable_id:"",native_private:false,inherited:false})}
 Window {width:510;height:900;visible:true
  Plugin.Panel {id:panel;manageIpc:false;hostWidget:host;controllerCommand:[Quickshell.env("HOME")+"/.local/bin/hyprveil"]}
 }
 property int stage:0
 property int ticks:0
 property var editor:null
 function find(item) {
  if (typeof item.confirm==="function" && typeof item.commitInputs==="function") return item
  for (var i=0;i<item.children.length;i++) {var result=find(item.children[i]);if(result)return result}
  return null
 }
 function expect(value,message) {if(!value)throw new Error(message)}
 Component.onCompleted:panel.open()
 Timer {interval:20;repeat:true;running:true
  onTriggered:{
   try {
    ticks++
    if(stage===0 && panel.current.known && !panel.querying) {
     panel.setTab("notifications");editor=find(panel)
     expect(panel.tab==="notifications" && editor && editor.supported,"notification section unavailable")
     editor.edit({enabled:true,mode:"spoiler",variant:"matrix"});stage=1
    } else if(stage===1 && panel.acting) {
     expect(panel.actionName==="notifications" && panel.current.known && editor.visible && editor.supported,"saving collapsed notification controls")
     editor.edit({variant:"anonymous"});stage=2
    } else if(stage===2 && !panel.acting && !panel.querying && !editor.dirty && !editor.saving) {
     expect(panel.current.notifications.variant==="anonymous" && panel.current.appearance.variant==="prism","late edit lost or window profile changed")
     panel.editAppearance("grain",17);stage=3
    } else if(stage===3 && !panel.acting && !panel.querying && !panel.appearanceDirty) {
     expect(panel.current.appearance.grain===17 && panel.current.notifications.variant==="anonymous","window edit reset notification profile")
     panel.close();console.log("HYPRVEIL_AUTOSAVE_OK notifications-panel");Qt.callLater(Qt.quit)
    }
    if(ticks>250)throw new Error("notification panel timeout stage="+stage)
   } catch(e){console.error(String(e));Qt.callLater(Qt.quit)}
  }
 }
}
'''
result=fixture.run_case('notifications-panel')
notifications=[row for row in result['commands'] if row['action']=='notifications']
result['ok'] &= len(notifications)==2 and result['final']['notifications']['variant']=='anonymous' and result['final']['grain']==17
if not result['ok']:
 print(json.dumps(result,indent=2));raise SystemExit(1)
print('passed real notification tab, delayed subprocess autosave, steady controls, queued edits and cross-profile persistence')
