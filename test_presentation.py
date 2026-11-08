from copy import deepcopy
import unittest

from harness import Harness, NAMES
from presentation import COUNCIL_CAPTIONS, council_caption


class CaptionTests(unittest.TestCase):
    def setUp(self):
        self.state = Harness().snapshot()
        self.state.update(id='current', busy=True)

    def assert_caption(self, key):
        self.assertEqual(council_caption(self.state), COUNCIL_CAPTIONS[key])

    def test_terminal_phases_and_restored_plan(self):
        self.state['busy'] = False
        for phase, key in [('idle', 'idle'), ('ready', 'ready'), ('review', 'review'), ('done', 'done'),
                           ('blocked', 'conditions'), ('changes_requested', 'conditions'), ('error', 'error'),
                           ('cancelled', 'interrupted'), ('interrupted', 'interrupted'), ('limit', 'limit'),
                           ('restored', 'idle'), ('unknown', 'idle')]:
            with self.subTest(phase=phase):
                self.state['phase'] = phase
                self.assert_caption(key)

    def test_proposals_votes_and_debate_follow_current_round(self):
        self.state['phase'] = 'analysis'
        self.assert_caption('receiving')
        self.state['usage']['calls'] = 1
        self.assert_caption('analysis')
        self.state['answers']['melchior']['id'] = 'previous'
        self.assert_caption('analysis')
        self.state['answers']['melchior']['id'] = 'current'
        self.assert_caption('planning')
        self.state['usage']['cycle'] = 2
        self.assert_caption('debate')
        self.state['phase'] = 'voting'
        for name in NAMES:
            self.state['answers'][name].update(id='current', activity='Aporte compartido')
        self.assert_caption('voting')
        for name in NAMES[:2]:
            self.state['answers'][name]['activity'] = 'Voto compartido'
        self.assert_caption('consensus')

    def test_collaboration_repairs_and_retry_without_modifying_state(self):
        self.state['phase'] = 'execution'
        self.assert_caption('teamwork')
        self.state['execution_report'] = 'Base y aportes compartidos'
        self.assert_caption('communication')
        self.state['usage']['repairs'] = 1
        self.assert_caption('repair')
        self.state['answers']['casper']['activity'] = 'Reintentando'
        before = deepcopy(self.state)
        self.assert_caption('retry')
        self.assertEqual(self.state, before)
        self.state.update(busy=False, phase='error')
        self.assert_caption('error')

    def test_all_captions_fit_and_have_separate_phrases_and_translations(self):
        self.assertEqual(len(COUNCIL_CAPTIONS), 21)
        for left, right, translation, box, box_translation in COUNCIL_CAPTIONS.values():
            self.assertNotEqual(left, right)
            self.assertLessEqual(max(len(left), len(right), len(box)), 4)
            self.assertTrue(translation and box_translation)


if __name__ == '__main__':
    unittest.main()
