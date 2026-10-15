#!/usr/bin/python3
"""Exercise notification drafts offscreen, without compositor or desktop data."""
import os
from pathlib import Path
import subprocess
import tempfile

PLUGIN=Path(__file__).resolve().parents[1]
QML='''import QtQuick
import Quickshell
import "plugin" as Plugin
import "plugin/Notifications.js" as Notifications
ShellRoot {
 id: test
 property int stage:0
 property int sends:0
 property var sent:[]
 property var snapshot:null
 function expect(value,message) { if (!value) throw new Error(message) }
 Plugin.NotificationEditor {
  id:editor; width:470; profile:Notifications.defaults()
  onSaveRequested:function(args) {
   test.sends++; test.sent=args; test.snapshot=Object.assign({},draft)
   externalBusy=true
  }
 }
 Component.onCompleted:{editor.edit({enabled:true,mode:"spoiler",variant:"matrix"})}
 Timer {
  interval:30;repeat:true;running:true
  onTriggered:{
   try {
    if (test.stage===0 && editor.saving) {
     test.expect(test.sends===1,"debounce emitted more than one command")
     test.expect(test.sent[0]==="notifications","wrong command")
     test.expect(test.sent.indexOf("--mode")>=0,"mode missing")
     editor.edit({variant:"anonymous"})
     editor.profile=test.snapshot;editor.confirm(test.snapshot)
     test.expect(editor.dirty && editor.draft.variant==="anonymous","late ack lost new edit")
     editor.externalBusy=false;test.stage=1
    } else if (test.stage===1 && editor.saving) {
     test.expect(test.sends===2,"latest edit not emitted exactly once")
     editor.failed("synthetic refusal");editor.externalBusy=false
     test.expect(editor.blocked && editor.dirty && !editor.saving,"failure reported saved")
     test.stage=2
    } else if (test.stage===2) {
     test.expect(test.sends===2,"failed command retried without new edit")
     editor.edit({variant:"error404"});editor.commitInputs();test.stage=3
    } else if (test.stage===3 && editor.saving) {
     test.expect(test.sends===3,"retry not sent")
     editor.profile=test.snapshot;editor.confirm(test.snapshot);editor.externalBusy=false
     test.expect(!editor.dirty && !editor.blocked,"ack did not settle")
     editor.externalBusy=true;editor.edit({mask_color:"#123456"})
     editor.profile=Object.assign({},editor.profile,{speed:37})
     test.expect(editor.draft.speed===37 && editor.draft.mask_color==="#123456","external state reset pending edit")
     editor.profile=null
     test.expect(!editor.supported && editor.dirty,"old core exposed controls or lost draft")
     console.log("HYPRVEIL_NOTIFICATION_DRAFT_OK");Qt.quit()
    }
   } catch(e) { console.log("HYPRVEIL_NOTIFICATION_ERROR",String(e));Qt.quit() }
  }
 }
 Timer {interval:8000;running:true;onTriggered:{console.log("HYPRVEIL_NOTIFICATION_TIMEOUT");Qt.quit()}}
}
'''
with tempfile.TemporaryDirectory(prefix='hyprveil-notifications-qml-') as directory:
 root=Path(directory);(root/'runtime').mkdir(mode=0o700)
 (root/'Commons').symlink_to('/usr/share/omarchy/shell/Commons')
 (root/'Ui').symlink_to('/usr/share/omarchy/shell/Ui')
 (root/'plugin').symlink_to(PLUGIN)
 (root/'shell.qml').write_text(QML)
 env=dict(os.environ,HOME=directory,XDG_RUNTIME_DIR=str(root/'runtime'),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QT_QPA_PLATFORMTHEME='',QT_STYLE_OVERRIDE='Fusion')
 for key in ('WAYLAND_DISPLAY','DISPLAY','HYPRLAND_INSTANCE_SIGNATURE','DBUS_SESSION_BUS_ADDRESS'):env.pop(key,None)
 result=subprocess.run(['/usr/bin/quickshell','--no-color','-p',str(root)],env=env,capture_output=True,text=True,timeout=12)
 output=result.stdout+result.stderr
 if result.returncode or 'HYPRVEIL_NOTIFICATION_DRAFT_OK' not in output or any(x in output for x in ('TypeError','ReferenceError','Cannot assign','Unable to assign')):
  print(output);raise SystemExit('notification editor test failed')
 print('passed notification debounce, late acknowledgement, failure/retry, external update and old-core gating')
