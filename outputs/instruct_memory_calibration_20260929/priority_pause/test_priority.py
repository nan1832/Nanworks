import importlib.util
from pathlib import Path
import sys
import types
import unittest
try:
    import fcntl
except ImportError:
    sys.modules['fcntl']=types.SimpleNamespace()
path=Path(__file__).with_name('controller.py')
spec=importlib.util.spec_from_file_location('priority',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Tests(unittest.TestCase):
    def test_order_profiles_before_resume(self):
        events=[]
        m.profile_then_resume(lambda layer:events.append('profile%d'%layer) or {'layer':layer},
                              lambda receipts,failures:events.append('resume_L8'))
        self.assertEqual(events,['profile20','profile17','resume_L8'])
    def test_probe_failure_still_restores_L8(self):
        events=[]
        def profile(layer):
            events.append(layer)
            if layer==20:raise RuntimeError('measured OOM')
            return {'layer':layer}
        receipts,failures=m.profile_then_resume(profile,lambda r,f:events.append('resume'))
        self.assertEqual(events,[20,17,'resume'])
        self.assertEqual([x['layer'] for x in receipts],[17])
        self.assertEqual([x['layer'] for x in failures],[20])
    def test_resume_only_changes_checkpoint(self):
        args=['python','-u','runner.py','--epochs','50','--layers','8','--batch-size','2','--resume-checkpoint','old','--resume-layer','8']
        new=m.resume_command(args,'new')
        self.assertEqual(new[:10],args[:10])
        self.assertEqual(new[10],'new')
        self.assertEqual(new[11:],args[11:])
        self.assertEqual(args[10],'old')
    def test_resume_rejects_wrong_budget(self):
        with self.assertRaises(AssertionError):
            m.resume_command(['--epochs','49','--layers','8','--resume-checkpoint','old'],'new')
if __name__=='__main__':unittest.main(verbosity=2)
