"""Ensure strict-ablation imports reject partial/mismatched evidence."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_all_method_recommendations as catalog


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='.lga_test_', dir=catalog.ROOT / 'outputs')
        self.root = Path(self.temp.name)
        self.model, self.ds = 'blip2-opt-2.7b', 'evqa-pilot500'
        self.patches = [patch.object(catalog, 'ABLATION', self.root),
                        patch.object(catalog, 'MODELS', {self.model: ('BLIP2', 32)}),
                        patch.object(catalog, 'DATASETS', {self.ds: ('EVQA-pilot500', 500)})]
        for p in self.patches:
            p.start()
        for x in [catalog.RECS, catalog.AUDITS, catalog.SCORES, catalog.ABLATION_GROUPS]:
            x.clear()
        catalog.CHECKS.clear()
        for method in ['LGA-Param', 'LGA-Visual']:
            catalog.RECS.append(dict(method=method, dataset=self.ds, model=self.model, flavor='raw', sample_count=1))

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def fixture(self, status='done'):
        """Synthetic test data never enters the real output directory."""
        group = self.root / 'results/visual' / self.ds / self.model
        group.mkdir(parents=True)
        def write(name, value):
            content = json.dumps(value).encode()
            (group / name).write_bytes(content)
            return hashlib.sha256(content).hexdigest()
        original = catalog.RAW / 'visual' / self.ds / self.model / 'ours_direct_layer_scores.csv'
        protocol_hash = write('protocol.json', dict(source='/synthetic', files={'/synthetic/ours_direct_layer_scores.csv': hashlib.sha256(original.read_bytes()).hexdigest()}, cohort=[{'sample_id': 'synthetic'}]))
        rows = [dict(layer=l, n=1, no_old_strength=float(l), no_new_strength=float(32-l), old_norm=1., new_norm=1.) for l in range(32)]
        score_hash = write('layer_scores.json', dict(space='visual', dataset=self.ds, model=self.model, rows=rows))
        reproduction_hash = write('historical_reproduction.json', [dict(passed=True) for _ in range(32*5)])
        write('summary.json', dict(status=status, baseline_failures=0, sample_count=1, score_sha256=score_hash,
                                  protocol_sha256=protocol_hash, reproduction_sha256=reproduction_hash, updated_at='synthetic-test-only'))
        (self.root / 'sync_status.json').write_text(json.dumps(dict(records=[dict(space='visual', dataset=self.ds, model=self.model, status=status, remote_sample_reaggregation_verified=True)])), encoding='utf-8')
        return group

    def test_complete_group_has_two_distinct_rankings(self):
        self.fixture()
        catalog.cross_strength_sources()
        self.assertEqual(catalog.get('LGA-Visual-no-old-strength', self.ds, self.model)['top3'], [31, 30, 29])
        self.assertEqual(catalog.get('LGA-Visual-no-new-strength', self.ds, self.model)['top3'], [0, 1, 2])
        self.assertEqual(len(catalog.AUDITS), 2)

    def test_partial_group_remains_pending(self):
        self.fixture(status='smoke_only')
        catalog.cross_strength_sources()
        self.assertEqual(catalog.get('LGA-Visual-no-old-strength', self.ds, self.model)['top3'], [])
        self.assertEqual(len(catalog.AUDITS), 0)

    def test_changed_scores_cannot_import(self):
        group = self.fixture()
        with (group / 'layer_scores.json').open('a') as f:
            f.write(' ')
        with self.assertRaises(AssertionError):
            catalog.cross_strength_sources()

    def test_unverified_remote_sample_reaggregation_cannot_import(self):
        self.fixture()
        p = self.root / 'sync_status.json'
        status = json.loads(p.read_text())
        status['records'][0]['remote_sample_reaggregation_verified'] = False
        p.write_text(json.dumps(status))
        with self.assertRaises(AssertionError):
            catalog.cross_strength_sources()


if __name__ == '__main__':
    unittest.main()
