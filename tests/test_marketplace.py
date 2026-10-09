"""Root package contract plus isolated stock plugin-add integration.

The stock CLI case uses its installed primary source with fake git transport
and shell IPC. It never contacts a repository or starts the real shell.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "io.github.objlako.hyprveil"
STOCK = Path("/usr/share/omarchy/bin")


class PackageTests(unittest.TestCase):
    def test_marketplace_metadata_and_entrypoint_are_at_repository_root(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["id"], PLUGIN_ID)
        self.assertEqual(manifest["version"], "1.6.1")
        self.assertEqual(manifest["author"], "OBJLAKO")
        self.assertEqual(manifest["name"], "Hyprveil")
        self.assertEqual(manifest["kinds"], ["bar-widget"])
        self.assertEqual(manifest["entryPoints"], {"barWidget": "BarWidget.qml"})
        self.assertEqual(manifest["barWidget"]["defaultSection"], "right")
        self.assertFalse(re.search(r"[А-Яа-яЁё]", manifest["description"]))
        for name in ("README.md", "LICENSE", "BarWidget.qml", "privacy-watch", "I18n.js", "docs/GUIDE.md"):
            self.assertTrue((ROOT / name).is_file(), name)
        self.assertFalse((ROOT / "plugin").exists())

    def test_only_one_manifest_and_no_symlinks_ship_outside_git_or_artifacts(self):
        files = [path for path in ROOT.rglob("*") if not any(part in (".git", "artifacts", "__pycache__") for part in path.relative_to(ROOT).parts)]
        self.assertEqual([path for path in files if path.name == "manifest.json"], [ROOT / "manifest.json"])
        self.assertFalse(any(path.is_symlink() for path in files))

    def test_relative_runtime_imports_resolve_inside_the_root_package(self):
        for path in [*ROOT.glob("*.qml"), *ROOT.glob("*.js")]:
            for relative in re.findall(r'^\.?import\s+"([^"]+)"', path.read_text(), re.MULTILINE):
                target = path.parent / relative
                self.assertTrue(target.exists(), (path.name, relative))
                self.assertTrue(target.resolve().is_relative_to(ROOT))
        bar = (ROOT / "BarWidget.qml").read_text()
        self.assertIn('Qt.resolvedUrl("privacy-watch")', bar)
        self.assertIn('["/usr/bin/python3", root.privacyWatcherPath, "watch"]', bar)

    def test_install_and_locale_text_do_not_enter_privacy_commands(self):
        for name in ("Panel.qml", "BarWidget.qml", "Privacy.js"):
            text = (ROOT / name).read_text()
            self.assertNotIn("tools/install.py", text)
            self.assertNotIn("postinstall", text.lower())
        privacy = (ROOT / "Privacy.js").read_text()
        self.assertNotIn("I18n", privacy)
        self.assertNotIn("language", privacy)
        self.assertIn('moduleName: "' + PLUGIN_ID + '"', (ROOT / "Panel.qml").read_text())
        self.assertIn('ipcTarget: "' + PLUGIN_ID + '"', (ROOT / "Panel.qml").read_text())
        setup_url = "https://github.com/OBJLAKO/omarchy-hyprveil#install"
        self.assertIn('Qt.openUrlExternally("' + setup_url + '")', (ROOT / "Panel.qml").read_text())
        self.assertIn(setup_url, (ROOT / "docs/GUIDE.md").read_text())


@unittest.skipUnless((STOCK / "omarchy-plugin-add").is_file() and shutil.which("jq"), "stock Omarchy CLI and jq required for local integration")
class StockPluginAddTests(unittest.TestCase):
    def test_stock_add_installs_and_enables_root_package_without_postinstall(self):
        with tempfile.TemporaryDirectory(prefix="hyprveil-marketplace-") as temporary:
            fixture = Path(temporary)
            home = fixture / "home"
            home.mkdir()
            commands = fixture / "bin"
            commands.mkdir()
            log = fixture / "ipc.jsonl"
            def script(name, text):
                path = commands / name
                path.write_text("#!/usr/bin/python3\n" + text)
                path.chmod(0o700)
            script("git", "import sys,shutil,pathlib\nassert sys.argv[1:3]==['clone','--']\ntarget=pathlib.Path(sys.argv[-1]);target.mkdir()\nsource=pathlib.Path(" + repr(str(ROOT)) + ")\nfor p in source.iterdir():\n if p.is_file() and p.suffix in ('.qml','.js','.py') or p.name in ('manifest.json','native-release.json','native-cli-provenance.json','panel-controller','privacy-watch','install.sh','uninstall.sh','README.md','LICENSE'):\n  shutil.copyfile(p,target/p.name)\nshutil.copytree(source/'assets/presets',target/'assets/presets')\nshutil.copytree(source/'tools',target/'tools',ignore=shutil.ignore_patterns('__pycache__'))\n(target/'.git').mkdir()\n")
            script("omarchy-plugin-catalog", "import json,os,pathlib\nplugins=pathlib.Path(os.environ['HOME'])/'.config/omarchy/plugins'\nitems=[]\nfor p in plugins.glob('*/manifest.json'):\n if not p.parent.name.startswith('.'):\n  item=json.loads(p.read_text());item['manifestPath']=str(p);items.append(item)\nprint(json.dumps(items))\n")
            script("omarchy-plugin-list", "import subprocess\nprint(subprocess.check_output(['omarchy-plugin-catalog'],text=True))\n")
            script("omarchy-shell", "import json,sys,pathlib\nwith pathlib.Path(" + repr(str(log)) + ").open('a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')\nprint('ok')\n")
            for name in ("omarchy-plugin-validate", "omarchy-git-url-check", "omarchy-plugin-enable"):
                (commands / name).symlink_to(STOCK / name)
            # The controller trap must never be executed by installation.
            cli = home / ".local/bin/hyprveil"
            cli.parent.mkdir(parents=True)
            cli.write_text("#!/bin/sh\nprintf 'controller executed' > " + str(fixture / "unexpected-controller") + "\nexit 1\n")
            cli.chmod(0o700)
            env = {"PATH": str(commands) + ":/usr/bin:/bin", "HOME": str(home), "LANG": "C.UTF-8"}
            result = subprocess.run([str(STOCK / "omarchy-plugin-add"), "https://example.invalid/hyprveil.git", "--yes", "--enable"],
                                    env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout)
            target = home / ".config/omarchy/plugins" / PLUGIN_ID
            for name in ("manifest.json", "BarWidget.qml", "Panel.qml", "I18n.js", "privacy-watch", "panel-controller", "native_cli.py", "native_service.py", "README.md", "LICENSE"):
                self.assertEqual((target / name).read_bytes(), (ROOT / name).read_bytes())
            self.assertFalse((fixture / "unexpected-controller").exists())
            ipc = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(ipc, [["shell", "rescanPlugins"], ["shell", "enablePlugin", PLUGIN_ID, "{}"]])
