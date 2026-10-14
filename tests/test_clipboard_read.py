"""Adversarial clipboard stream tests; never touch the user's clipboard."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('clipboard_read', str(ROOT / 'clipboard-read'))
spec = importlib.util.spec_from_loader(loader.name, loader)
clipboard = importlib.util.module_from_spec(spec)
loader.exec_module(clipboard)


class ClipboardTests(unittest.TestCase):
    def read(self, source):
        return clipboard.read_clipboard([sys.executable, '-c', source])

    def test_finite_utf8(self):
        self.assertEqual(self.read("import os;os.write(1, '/tmp/Моя иконка.png'.encode())"), '/tmp/Моя иконка.png')

    def test_exact_byte_limit(self):
        self.assertEqual(len(self.read('import os;os.write(1,b"a"*16384)')), 16384)

    def test_large_and_infinite_stream_refused(self):
        started = time.monotonic()
        with self.assertRaisesRegex(clipboard.Refused, 'too-large'):
            self.read('import os\nwhile True: os.write(1,b"x"*4096)')
        self.assertLess(time.monotonic() - started, 2)

    def test_stalled_provider_has_deadline(self):
        started = time.monotonic()
        with self.assertRaisesRegex(clipboard.Refused, 'timeout'):
            self.read('import time;time.sleep(10)')
        self.assertLess(time.monotonic() - started, 2)

    def test_slow_stream_not_renewing_deadline(self):
        with self.assertRaisesRegex(clipboard.Refused, 'timeout'):
            self.read('import os,time\nwhile True: os.write(1,b"a");time.sleep(.05)')

    def test_eof_without_process_exit_has_deadline(self):
        with self.assertRaisesRegex(clipboard.Refused, 'timeout'):
            self.read('import os,time;os.close(1);time.sleep(10)')

    def test_nonzero_exit_refuses_partial_text(self):
        with self.assertRaisesRegex(clipboard.Refused, 'unavailable'):
            self.read('import os;os.write(1,b"/tmp/partial.png");raise SystemExit(1)')

    def test_invalid_utf8_refused(self):
        with self.assertRaisesRegex(clipboard.Refused, 'invalid-text'):
            self.read('import os;os.write(1,b"\\xff")')

    def test_control_characters_refused(self):
        for char in ('\x00', '\n', '\r', '\t', '\x7f', '\x85'):
            with self.subTest(char=repr(char)), self.assertRaisesRegex(clipboard.Refused, 'single-line-only'):
                self.read('import os;os.write(1,' + repr('a'+char+'b') + '.encode())')

    def test_reader_limits_and_clean_environment(self):
        source = 'import os,resource,json;print(json.dumps([resource.getrlimit(resource.RLIMIT_AS)[0],"LD_PRELOAD" in os.environ,"PYTHONPATH" in os.environ]),end="")'
        old = os.environ.get('PYTHONPATH')
        os.environ['PYTHONPATH'] = '/untrusted'
        try:
            self.assertEqual(json.loads(self.read(source)), [128*1024*1024, False, False])
        finally:
            if old is None: os.environ.pop('PYTHONPATH', None)
            else: os.environ['PYTHONPATH'] = old

    def test_helper_death_kills_reader(self):
        with tempfile.TemporaryDirectory() as temporary:
            pid_file = Path(temporary) / 'reader.pid'
            child = 'import os,time;open('+repr(str(pid_file))+',"w").write(str(os.getpid()));time.sleep(10)'
            source = 'import importlib.machinery;module=importlib.machinery.SourceFileLoader("guard",'+repr(str(ROOT/'clipboard-read'))+').load_module();module.read_clipboard(['+repr(sys.executable)+',"-c",'+repr(child)+'])'
            process = subprocess.Popen([sys.executable, '-c', source], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic()+2
                while not pid_file.exists() and time.monotonic()<deadline: time.sleep(.01)
                self.assertTrue(pid_file.exists())
                pid = int(pid_file.read_text())
                process.kill(); process.wait()
                for _ in range(100):
                    try:
                        state = Path('/proc', str(pid), 'stat').read_text().rsplit(')',1)[1].split()[0]
                        if state == 'Z': break
                    except (FileNotFoundError, ProcessLookupError): break
                    time.sleep(.01)
                else: self.fail('clipboard reader survived its owner')
            finally:
                if process.poll() is None: process.kill()
                process.wait()

    def test_all_editable_runtime_fields_use_guard(self):
        for name in ('Panel.qml', 'AppearanceEditor.qml'):
            source = (ROOT/name).read_text()
            self.assertNotRegex(source, r'(?m)^\s*(?:component\s+\w+:\s*)?Text(?:Field|Input|Edit|Area)\s*\{')
        guard = (ROOT/'SafeTextField.qml').read_text()
        self.assertIn('readOnly: true', guard)
        self.assertNotIn('readOnly: false', guard)
        self.assertNotIn('canPaste', '\n'.join(line for line in guard.splitlines() if not line.strip().startswith('//')))
        self.assertNotIn('.paste()', guard)


if __name__ == '__main__':
    unittest.main()
