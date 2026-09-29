import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
try:
    import fcntl
except ImportError:
    sys.modules['fcntl'] = types.SimpleNamespace(LOCK_EX=2, LOCK_NB=4, flock=lambda *a: None)
ROOT=Path(__file__).resolve().parent

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

cal=module('cal','calibration.py')
probe=module('probe','probe.py')
eligible=module('eligible','before_eligible_queue.py')

class Tests(unittest.TestCase):
    def measured(self,required=70000):
        return dict(required_mib=required,layers=[dict(accounted_peak_mib=65000),dict(accounted_peak_mib=67000)])

    def test_margin_includes_allocator_and_nonallocator_high_water(self):
        r=dict(status='passed',completed_epochs=1,optimizer_batches=250,
               current_process_mib=61000,current_reserved_mib=60000,max_reserved_mib=62000)
        got=cal.requirement(r,61500)
        self.assertEqual(got['accounted_peak_mib'],63024)
        self.assertEqual(got['required_mib'],65280)

    def test_cannot_accept_partial_epoch(self):
        with self.assertRaises(AssertionError):
            cal.requirement(dict(status='passed',completed_epochs=1,optimizer_batches=249),1)

    def test_no_76g_fallback_and_only_profile_once(self):
        q=types.SimpleNamespace(gpu=lambda phase,instruct=False:(False,dict(free_mib=77110,required_mib=77824)))
        with patch.object(cal,'ensure',return_value=self.measured(70000)) as ensure:
            cal.install(q)
            self.assertTrue(q.gpu('train',True)[0])
            self.assertTrue(q.gpu('train',True)[0])
            self.assertEqual(ensure.call_count,1)
            self.assertEqual(q.gpu('train',True)[1]['required_mib'],70000)

    def test_measured_large_requirement_is_not_forced_to_fit(self):
        q=types.SimpleNamespace(gpu=lambda phase,instruct=False:(True,dict(free_mib=77110)))
        with patch.object(cal,'ensure',return_value=self.measured(79000)):
            cal.install(q)
            self.assertFalse(q.gpu('train',True)[0])

    def test_eval_and_minigpt_gates_unchanged(self):
        calls=[]
        def gpu(phase,instruct=False):
            calls.append((phase,instruct));return ('unchanged',{'required_mib':56320})
        q=types.SimpleNamespace(gpu=gpu)
        with patch.object(cal,'ensure') as ensure:
            cal.install(q)
            self.assertEqual(q.gpu('eval',True)[0],'unchanged')
            self.assertEqual(q.gpu('train',False)[0],'unchanged')
            ensure.assert_not_called()

    def test_profile_runs_original_one_epoch_and_does_not_return_to_formal_selection(self):
        report={};calls=[]
        editor=types.SimpleNamespace(train_epoch=1,data_generator=types.SimpleNamespace(sample_count=500),train_a_batch=lambda:('loss',{}))
        def original(e,epochs):
            calls.append(epochs)
            for i in range(250):e.train_a_batch()
        runner=types.SimpleNamespace(train_with_synchronous_loading=original)
        torch=types.SimpleNamespace(cuda=types.SimpleNamespace(synchronize=lambda:None))
        probe.install_epoch_probe(runner,report,torch)
        with self.assertRaises(probe.ProfileComplete):runner.train_with_synchronous_loading(editor,50)
        self.assertEqual(calls,[1])
        self.assertEqual(report['requested_epochs'],50)
        self.assertEqual(report['optimizer_batches'],250)

    def test_queue_dependency_eval_then_profiles_then_L20_then_L17(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=Path(tmp);events=[]
            def spec(ds,m,l):return dict(dataset=ds,model=m,layer=l)
            def target(j,kind):return old/kind/j['dataset']/j['model']/('layer_%02d'%j['layer'])
            l8=spec('mmke-entity','minigpt-4-vicuna-7b',8)
            d=target(l8,'work');d.mkdir(parents=True);(d/'train.done').touch()
            def done(j):
                d=target(j,'accepted');d.mkdir(parents=True,exist_ok=True);(d/'SYNC_VERIFIED').touch()
            done(spec('mmke-entity','minigpt-4-vicuna-7b',7))
            q=types.SimpleNamespace(OLD=old,state=lambda *a,**k:None,
                gpu=lambda phase,instruct=False:(True,dict(free_mib=77110,required_mib=77824)),
                t=types.SimpleNamespace(spec=spec,layer=lambda j:target(j,'work'),validate=lambda j:None,validate_eval=lambda j,d:None))
            def execute(ds,m,layers):
                for layer in layers:
                    j=spec(ds,m,layer)
                    if m=='instructblip-vicuna-7b':
                        q.CURRENT=j;q.gate('train');events.append('train%d'%layer)
                    elif layer==8:events.append('eval8')
                    done(j)
            q.execute_group=execute
            def ensure(q):
                self.assertIn('eval8',events)
                self.assertTrue((target(l8,'accepted')/'SYNC_VERIFIED').exists())
                events.extend(['profile20','profile17'])
                return self.measured()
            with patch.object(cal,'ensure',side_effect=ensure),patch.object(eligible.time,'sleep',return_value=None):
                eligible.install(q);cal.install(q)
                q.execute_group('mmke-entity','minigpt-4-vicuna-7b',[7,8])
            self.assertEqual(events,['eval8','profile20','profile17','train20','train17'])

if __name__=='__main__':unittest.main(verbosity=2)
