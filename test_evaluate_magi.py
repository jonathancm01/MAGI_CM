from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from evaluate_magi import compare


class EvaluationTests(unittest.TestCase):
    def test_identical_check_measures_real_artifacts_without_claiming_general_quality(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            single, council = root / 'single', root / 'council'
            single.mkdir()
            council.mkdir()
            (council / 'keyboard.txt').write_text('verified')
            check = root / 'check.py'
            check.write_text('from pathlib import Path\nimport sys\nassert (Path(sys.argv[1]) / "keyboard.txt").read_text() == "verified"\n')
            report = compare(single, council, [check])
            self.assertEqual(report['results']['single']['passed'], 0)
            self.assertEqual(report['results']['council']['passed'], 1)
            self.assertEqual(report['passed_difference'], 1)
            self.assertIn('no mide', report['scope'])
            with patch('evaluate_magi.subprocess.run', side_effect=subprocess.TimeoutExpired('check', 120)):
                limited = compare(single, council, [check])
            self.assertTrue(all(not result['checks'][0]['passed'] and 'error' in result['checks'][0]
                                for result in limited['results'].values()))
            with self.assertRaises(ValueError):
                compare(single, single, [check])
            with self.assertRaises(ValueError):
                compare(single, council, [])
