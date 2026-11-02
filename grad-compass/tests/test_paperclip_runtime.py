"""Service bootstrap regressions without contacting agents or a real supervisor."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('paperclip_runtime', Path(__file__).resolve().parents[1]/'scripts/paperclip_runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.settings=root/'launch.local.json'
        self.value={key:str(root/key) for key in ('node','entrypoint','config')}
        for key in self.value:Path(self.value[key]).write_text('Invented executable/configuration')
        self.value.update(codex_home=str(root),port=3100,runtime_environment={'HTTPS_PROXY':'http://127.0.0.1:1234'})
        self.save();self.settings.chmod(0o600)
        self.addCleanup(patch.stopall)
        patch.object(runtime,'SETTINGS',self.settings).start()
        patch('builtins.print').start()
        patch.object(runtime.os,'umask').start()
        self.exec=patch.object(runtime.os,'execve').start()
        self.socket=patch.object(runtime.socket,'socket').start()
    def save(self):self.settings.write_text(json.dumps(self.value))
    def invoke(self,args):
        with patch.object(runtime.sys,'argv',['paperclip_runtime.py',*args]):return runtime.main()
    def test_native_service_command_and_pinned_runtime_do_not_copy_credentials(self):
        self.invoke(['service','status','--json'])
        executable,args,environment=self.exec.call_args.args
        self.assertEqual(str(executable),self.value['node'])
        self.assertEqual(args[-3:],['service','status','--json'])
        self.assertEqual(environment['CODEX_HOME'],self.value['codex_home'])
        self.assertEqual(environment['HTTPS_PROXY'],'http://127.0.0.1:1234')
        self.socket.assert_not_called()
    def test_run_fails_closed_on_occupied_port_instead_of_starting_parallel_controller(self):
        self.socket.return_value.__enter__.return_value.bind.side_effect=OSError('Port occupied')
        self.assertEqual(self.invoke(['run','--instance','default']),1)
        self.exec.assert_not_called()
    def test_planned_restart_drains_legacy_executions(self):
        self.invoke(['service','restart','--json'])
        self.assertEqual(self.exec.call_args.args[1][-4:],['service','restart','--json','--wait'])
    def test_run_pins_port_config_node_path_and_private_umask(self):
        self.invoke(['run','--instance','default'])
        _,args,environment=self.exec.call_args.args
        self.assertEqual(args[-3:],['--no-repair','--config',self.value['config']])
        self.assertEqual(environment['PORT'],'3100')
        self.assertTrue(environment['PATH'].startswith(str(Path(self.value['node']).parent)))
        runtime.os.umask.assert_called_once_with(0o077)
    def test_force_repairs_credentials_and_nonprivate_bootstrap_are_rejected(self):
        for args in [['run','--force'],['run','--repair'],['run','--config','/different']]:
            self.assertEqual(self.invoke(args),1)
        self.value['runtime_environment']={'OPENAI_API_KEY':'Not a real secret'};self.save()
        self.assertEqual(self.invoke(['service','status']),1)
        self.value['runtime_environment']={};self.save();self.settings.chmod(0o644)
        self.assertEqual(self.invoke(['service','start']),1)
        self.exec.assert_not_called()
