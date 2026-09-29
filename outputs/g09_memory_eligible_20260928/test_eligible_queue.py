import types
import unittest
from unittest.mock import patch

import eligible_queue as e


class FakePath:
    def __init__(self, value, files):
        self.value, self.files = value, files

    def __truediv__(self, tail):
        return FakePath(self.value + '/' + str(tail), self.files)

    def is_file(self):
        return self.value in self.files

    def exists(self):
        return self.is_file()


class QueueTests(unittest.TestCase):
    def make_queue(self, free):
        q = types.SimpleNamespace()
        q.files, q.calls, q.events, q.free = set(), [], [], free
        q.OLD = FakePath('old', q.files)
        q.state = lambda name, **kw: q.events.append((name, kw))
        q.t = types.SimpleNamespace(spec=lambda ds, m, l: dict(dataset=ds, model=m, layer=l),
                                    validate_eval=lambda job, path: None,
                                    validate=lambda job: None,
                                    layer=lambda job: FakePath('layer/' + str(job['layer']), q.files))
        q.gpu = lambda phase, instruct=False: (False, dict(free_mib=q.free,
            required_mib=(77824 if instruct else 73728) if phase == 'train' else 56320,
            unexpected=[dict(pid=123, memory=8000)]))

        def execute(ds, model, layers):
            for layer in layers:
                q.calls.append((ds, model, layer))
                q.files.add('old/accepted/%s/%s/layer_%02d/SYNC_VERIFIED' % (ds, model, layer))
                if layer == 8:
                    q.free = 80000
        q.execute_group = execute
        return q

    def test_lower_memory_layer_does_not_wait_behind_instruct(self):
        q = self.make_queue(72350)
        e.install(q)
        q.execute_group('mmke-entity', 'minigpt-4-vicuna-7b', [7, 8])
        self.assertEqual([x[2] for x in q.calls], [7, 8, 20, 17])
        q.execute_group('evqa-pilot500', 'instructblip-vicuna-7b', [17, 20])
        self.assertEqual(len(q.calls), 4)

    def test_all_fit_keep_fast_first(self):
        q = self.make_queue(80000)
        e.install(q)
        q.execute_group('mmke-entity', 'minigpt-4-vicuna-7b', [7, 8])
        self.assertEqual([x[2] for x in q.calls], [7, 20, 17, 8])
        with self.assertRaises(AssertionError):
            q.execute_group('mmke-entity', 'minigpt-4-vicuna-7b', [7, 8])

    def test_memory_margin_and_eval_gate(self):
        q = self.make_queue(72165)
        e.install(q)
        self.assertFalse(q.gpu('train')[0])
        q.free = 72166
        ready, info = q.gpu('train')
        self.assertTrue(ready)
        self.assertEqual(info['margin_mib'], 2048)
        self.assertFalse(q.gpu('train', instruct=True)[0])
        q.free = 56320
        self.assertTrue(q.gpu('eval')[0])
        q.free = 56319
        self.assertFalse(q.gpu('eval')[0])

    def test_changed_gate_reselects_before_launch(self):
        q = self.make_queue(70000)
        e.install(q)
        q.CURRENT = dict(model='minigpt-4-vicuna-7b')
        with self.assertRaises(e.ReconsiderEligibility):
            q.gate('train')
        self.assertFalse(q.calls)

    def test_train_requires_three_successful_checks(self):
        q = self.make_queue(72350)
        e.install(q)
        q.CURRENT = dict(model='minigpt-4-vicuna-7b')
        with patch.object(e.time, 'sleep') as sleep:
            q.gate('train')
        self.assertEqual([event[1]['stable'] for event in q.events], [1, 2, 3])
        self.assertEqual(sleep.call_count, 2)

    def test_completed_skipped_and_unknown_task_rejected(self):
        q = self.make_queue(72350)
        for ds, model, layer in e.ORDER:
            q.files.add('old/accepted/%s/%s/layer_%02d/SYNC_VERIFIED' % (ds, model, layer))
        e.install(q)
        q.execute_group('mmke-entity', 'minigpt-4-vicuna-7b', [7, 8])
        self.assertEqual([x[2] for x in q.calls], [7])
        with self.assertRaises(RuntimeError):
            q.execute_group('evqa-pilot500', 'llava-v1.5-7b', [4])

    def test_all_blocked_wait_then_select_fit(self):
        q = self.make_queue(60000)
        e.install(q)
        with patch.object(e.time, 'sleep', side_effect=lambda _: setattr(q, 'free', 72350)):
            q.execute_group('mmke-entity', 'minigpt-4-vicuna-7b', [7, 8])
        self.assertEqual(q.events[0][0], 'WAITING_FOR_ANY_ELIGIBLE_LAYER')
        self.assertEqual([x[2] for x in q.calls], [7, 8, 20, 17])

    def test_pending_eval_precedes_new_train(self):
        q = self.make_queue(72350)
        q.files.add('layer/20/train.done')
        e.install(q)
        q.execute_group('mmke-entity', 'minigpt-4-vicuna-7b', [7, 8])
        self.assertEqual([x[2] for x in q.calls], [7, 20, 8, 17])


if __name__ == '__main__':
    unittest.main()
