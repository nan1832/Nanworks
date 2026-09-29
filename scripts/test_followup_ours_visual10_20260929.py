"""Safety and integrity checks for the delayed, bounded GPU rerun."""
import copy
import tempfile
from pathlib import Path
from unittest import TestCase, main, mock
import followup_ours_visual10_20260929 as f


class FollowupTests(TestCase):
    def test_gate_requires_finished_computation_and_both_original_processes_gone(self):
        self.assertTrue(f.gate_ready('FINISHED_WITH_PENDING','done',False,False))
        self.assertTrue(f.gate_ready('FINISHED_WITH_PENDING','needs_reproduction_review',False,False))
        for state,summary,controller,child in [
            ('RUNNING_OURS_VISUAL10','done',False,False),
            ('FINISHED_WITH_PENDING','failed',False,False),
            ('FINISHED_WITH_PENDING','done',True,False),
            ('FINISHED_WITH_PENDING','done',False,True)]:
            self.assertFalse(f.gate_ready(state,summary,controller,child))

    def test_reused_pid_does_not_count_as_original_process(self):
        old=dict(pid=20,start_ticks='100',cmd='original queue',state='S')
        self.assertTrue(f.same_live_process(old,dict(old)))
        self.assertFalse(f.same_live_process(old,dict(old,start_ticks='200')))
        self.assertFalse(f.same_live_process(old,dict(old,state='Z')))

    def test_original_tolerances_retained_including_near_zero(self):
        row=dict(layer=0,dot=0,cos=.001,old_norm=2,new_norm=3,no_direction=6)
        h={'layer':'0', **{c:str(row[k]) for k,c in f.FIELDS.items()}}
        self.assertTrue(all(x['passed'] for x in f.mean_checks([row],[h])))
        altered=dict(row,cos=.001002,dot=2e-8)
        failed={x['field'] for x in f.mean_checks([altered],[h]) if not x['passed']}
        self.assertEqual(failed,{'cos','dot'})

    def test_input_hash_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source';p.write_text('frozen')
            protocol={'files':{str(p):f.sha(p)}}
            f.verify_inputs(protocol)
            p.write_text('changed')
            with self.assertRaises(AssertionError):f.verify_inputs(protocol)

    def test_wrong_targets_missing_layers_and_duplicate_samples_rejected(self):
        protocol={'cohort':[dict(sample_id='s',sample_i=0,old='old',new='new')]}
        r=dict(protocol['cohort'][0],layers={'0':{'value':1},'1':{'value':2}})
        f.validate_records([r],protocol,2,lambda pair:None)
        variants=[dict(r,old='different'),dict(r,layers={'0':{}})]
        for bad in variants:
            with self.assertRaises(AssertionError):f.validate_records([bad],protocol,2,lambda pair:None)
        with self.assertRaises(AssertionError):f.validate_records([r,copy.deepcopy(r)],protocol,2,lambda pair:None)

    def test_failed_verifier_cannot_write_official_artifacts(self):
        mod=mock.Mock()
        mod.verify_full.side_effect=AssertionError('Historical reproduction failed')
        with mock.patch.object(f,'original',return_value=mod),mock.patch.object(f,'write') as write:
            with self.assertRaises(AssertionError):f.publish_retry(*f.TARGETS[0])
            write.assert_not_called()

    def test_only_authorized_three_groups_are_in_scope(self):
        self.assertEqual(set(f.TARGETS),{('mmke-entity','paligemma-3b'),
                                      ('evqa-pilot500','qwen2.5-vl-3b'),
                                      ('mmke-visual','qwen2.5-vl-3b')})


if __name__=='__main__':main()
