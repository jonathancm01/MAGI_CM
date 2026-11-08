from copy import deepcopy
import json
from pathlib import Path
import tempfile
from threading import Event
import time
import unittest
from unittest.mock import patch

from harness import DEFAULT_CONFIG, Harness, write_json
from workspaces import WorkspaceStore


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        self.config = deepcopy(DEFAULT_CONFIG)
        self.config["workspace"] = str(self.folder)
        self.calls = []

        def runner(node, prompt, workspace, cancel, writable=False):
            self.calls.append((prompt, workspace, writable))
            return '{"vote":"yes","reason":"Comprobado"}' if 'Devuelve solo JSON' in prompt else 'PLAN PROPIO'

        self.runner = runner
        commands = patch('ai.command_for', return_value=(['unused'], {}))
        commands.start()
        self.addCleanup(commands.stop)
        self.store = WorkspaceStore(self.folder / '.magi', self.config, runner)
        self.chat_id = self.store.data['selected']
        self.config = self.store.chat(self.chat_id)['config']
        self.project_id = self.store.chat(self.chat_id)['project_id']

    def wait(self, chat_id):
        engine = self.store.engine(chat_id)
        deadline = time.monotonic() + 4
        while engine.snapshot()['busy'] and time.monotonic() < deadline:
            Event().wait(.01)
        self.assertFalse(engine.snapshot()['busy'])
        return engine.snapshot()

    def send(self, chat_id, task):
        engine = self.store.engine(chat_id)
        self.store.perform(chat_id, engine.snapshot()['id'], 'start', task, self.store.chat(chat_id)['config'])
        return self.wait(chat_id)

    def test_chats_have_independent_memory_and_continue_their_own_work(self):
        self.send(self.chat_id, 'OBJETIVO ALFA')
        second = self.store.new_chat(self.project_id)
        self.assertEqual(len(self.calls), 7)
        self.assertEqual(self.store.engine(second).snapshot()['task'], '')
        self.send(second, 'OBJETIVO BETA')
        self.assertTrue(all('OBJETIVO ALFA' not in prompt for prompt, _, _ in self.calls[7:]))
        self.store.select(self.chat_id, second, 'BORRADOR BETA')
        self.send(self.chat_id, 'CORRIGE SOLO ALFA')
        self.assertTrue(all('OBJETIVO BETA' not in prompt for prompt, _, _ in self.calls[14:]))
        self.assertTrue(any('OBJETIVO ALFA' in prompt and 'CORRIGE SOLO ALFA' in prompt for prompt, _, _ in self.calls[14:]))
        self.assertEqual(self.store.engine(self.chat_id).snapshot()['iteration'], 2)
        self.assertEqual(self.store.engine(second).snapshot()['iteration'], 1)
        self.assertEqual(self.store.chat(second)['draft'], 'BORRADOR BETA')

    def test_independent_chats_create_folders_and_inherit_selected_models(self):
        config = deepcopy(self.config)
        config['nodes']['melchior']['model'] = 'chosen-model'
        self.store.perform(self.chat_id, self.store.engine(self.chat_id).snapshot()['id'], 'save', '', config)
        second = self.store.new_chat(source=self.chat_id)
        for chat_id in (self.chat_id, second):
            folder = Path(self.store.chat(chat_id)['config']['workspace'])
            self.assertTrue(folder.is_dir())
            self.assertEqual(folder.parent, self.folder / 'projects')
            self.assertEqual(folder.name, f'chat-{chat_id}')
        self.assertNotEqual(self.store.chat(second)['project_id'], self.project_id)
        self.assertEqual(self.store.chat(second)['config']['nodes'], config['nodes'])
        self.assertFalse(self.calls)
        reopened = WorkspaceStore(self.folder / '.magi', self.config, self.runner)
        self.assertEqual(reopened.chat(second), self.store.chat(second))

    def test_implementation_writes_in_new_and_existing_project_folders(self):
        def runner(node, prompt, workspace, cancel, writable=False):
            if writable:
                target = Path(workspace) / 'assets'
                target.mkdir(exist_ok=True)
                (target / 'created.txt').write_text('written', encoding='utf-8')
            return self.runner(node, prompt, workspace, cancel, writable)

        self.store.runner = runner
        existing = self.folder / 'existing'
        existing.mkdir()
        (existing / 'keep.txt').write_text('original', encoding='utf-8')
        project = self.store.add_project(str(existing))
        other = self.store.new_chat(project)
        for chat_id in (self.chat_id, other):
            state = self.send(chat_id, 'Crear un archivo sin borrar lo existente')
            self.store.perform(chat_id, state['id'], 'execute', '', self.store.chat(chat_id)['config'])
            self.assertEqual(self.wait(chat_id)['phase'], 'done')
            folder = Path(self.store.chat(chat_id)['config']['workspace'])
            self.assertEqual((folder / 'assets' / 'created.txt').read_text(), 'written')
        self.assertEqual((existing / 'keep.txt').read_text(), 'original')
        self.assertFalse((self.folder / 'assets').exists())

    def test_new_folder_is_removed_if_index_cannot_be_saved(self):
        before = self.store.path.read_bytes()
        folders = set((self.folder / 'projects').iterdir())
        with patch('workspaces.write_json', side_effect=OSError('Disco lleno')):
            with self.assertRaisesRegex(OSError, 'Disco lleno'):
                self.store.new_chat(source=self.chat_id)
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(self.store.data['selected'], self.chat_id)
        self.assertEqual(set((self.folder / 'projects').iterdir()), folders)

    def test_delete_and_restore_preserve_history_draft_models_and_project_files(self):
        state = self.send(self.chat_id, 'CONVERSACION PARA RESTAURAR')
        self.store.save_draft(self.chat_id, 'Borrador conservado')
        file = Path(self.config['workspace']) / 'keep.txt'
        file.write_text('conservar', encoding='utf-8')
        history = self.store.storage / 'chats' / self.chat_id / f"{state['task_id']}.json"
        original = history.read_bytes()
        second = self.store.new_chat(self.project_id)
        self.store.select(self.chat_id)
        before = len(self.calls)
        self.store.delete_chat(self.chat_id)
        self.assertNotIn(self.chat_id, self.store.data['chats'])
        self.assertNotIn(self.chat_id, self.store.engines)
        self.assertEqual(self.store.data['selected'], second)
        self.assertEqual(history.read_bytes(), original)
        self.assertEqual(file.read_text(), 'conservar')
        with self.assertRaises(ValueError):
            self.store.perform(self.chat_id, state['id'], 'execute', '', self.config)
        self.store = WorkspaceStore(self.folder / '.magi', self.config, self.runner)
        self.store.restore_chat(self.chat_id)
        self.assertEqual(self.store.data['selected'], self.chat_id)
        self.assertEqual(self.store.chat(self.chat_id)['draft'], 'Borrador conservado')
        self.assertEqual(self.store.chat(self.chat_id)['config'], self.config)
        self.assertEqual(self.store.engine(self.chat_id).snapshot()['phase'], 'restored')
        self.assertEqual(len(self.calls), before)

    def test_deleting_last_chat_leaves_a_fresh_chat_in_the_same_folder(self):
        self.store.delete_chat(self.chat_id)
        replacement = self.store.data['selected']
        self.assertNotEqual(replacement, self.chat_id)
        self.assertEqual(self.store.chat(replacement)['config'], self.config)
        self.assertEqual(self.store.engine(replacement).snapshot()['task'], '')
        self.assertEqual(len(list((self.folder / 'projects').iterdir())), 1)
        self.assertIn(self.chat_id, self.store.data['trash'])

    def test_delete_rejects_busy_chat_and_invalid_ids(self):
        engine = self.store.engine(self.chat_id)
        engine.state['busy'] = True
        with self.assertRaisesRegex(ValueError, 'trabajando'):
            self.store.delete_chat(self.chat_id)
        self.assertIn(self.chat_id, self.store.data['chats'])
        for bad_id in ('../history', 'f' * 32, None):
            with self.assertRaises(ValueError):
                self.store.delete_chat(bad_id)
            with self.assertRaises(ValueError):
                self.store.restore_chat(bad_id)
        self.assertFalse(self.calls)

    def test_failed_delete_and_restore_keep_the_previous_index_and_engine(self):
        engine = self.store.engine(self.chat_id)
        original = self.store.path.read_bytes()
        with patch('workspaces.write_json', side_effect=OSError('Disco lleno')):
            with self.assertRaises(OSError):
                self.store.delete_chat(self.chat_id)
        self.assertEqual(self.store.path.read_bytes(), original)
        self.assertIs(self.store.engine(self.chat_id), engine)
        self.store.delete_chat(self.chat_id)
        deleted = self.store.path.read_bytes()
        with patch('workspaces.write_json', side_effect=OSError('Disco lleno')):
            with self.assertRaises(OSError):
                self.store.restore_chat(self.chat_id)
        self.assertEqual(self.store.path.read_bytes(), deleted)
        self.assertNotIn(self.chat_id, self.store.data['chats'])

    def test_projects_keep_folders_and_chat_settings_separate_across_restart(self):
        other_folder = self.folder / 'otro-proyecto'
        other_folder.mkdir()
        other_project = self.store.add_project(str(other_folder), 'Otro proyecto')
        second = self.store.new_chat(other_project)
        config = self.store.chat(second)['config']
        config['nodes']['melchior']['model'] = 'modelo-elegido'
        self.store.perform(second, self.store.engine(second).snapshot()['id'], 'save', '', config)
        self.store.save_draft(second, 'Borrador independiente')
        self.store.select(second)
        reopened = WorkspaceStore(self.folder / '.magi', self.config, self.runner)
        self.assertEqual(reopened.data['selected'], second)
        self.assertEqual(reopened.chat(second)['draft'], 'Borrador independiente')
        self.assertEqual(reopened.chat(second)['config']['nodes']['melchior']['model'], 'modelo-elegido')
        self.assertEqual(reopened.chat(self.chat_id)['config']['nodes']['melchior']['model'], '')
        self.assertEqual(reopened.chat(second)['config']['workspace'], str(other_folder))
        self.assertEqual(len(self.calls), 0)
        self.assertEqual(self.store.add_project(str(other_folder), 'Duplicado'), other_project)

    def test_navigation_while_busy_keeps_worker_in_its_chat_and_blocks_another_operation(self):
        entered, release = Event(), Event()
        def runner(*args, **kwargs):
            entered.set()
            release.wait(4)
            return self.runner(*args, **kwargs)
        self.store.runner = runner
        engine = self.store.engine(self.chat_id)
        try:
            self.store.perform(self.chat_id, engine.snapshot()['id'], 'start', 'TRABAJO ACTIVO', self.config)
            self.assertTrue(entered.wait(2))
            second = self.store.new_chat(self.project_id)
            self.store.select(second)
            self.assertEqual(self.store.engine(second).snapshot()['task'], '')
            self.assertTrue(self.store.navigation()['chats'][self.chat_id]['busy'])
            with self.assertRaisesRegex(ValueError, 'chat trabajando'):
                self.store.perform(second, self.store.engine(second).snapshot()['id'], 'start', 'OTRA', self.config)
            self.assertEqual(self.store.engine(second).snapshot()['task'], '')
        finally:
            release.set()
            self.wait(self.chat_id)

    def test_run_authorization_cannot_cross_chat_or_accept_an_unsubmitted_draft(self):
        state = self.send(self.chat_id, 'PLAN ALFA')
        second = self.store.new_chat(self.project_id)
        with self.assertRaisesRegex(ValueError, 'cambió'):
            self.store.perform(second, state['id'], 'execute', '', self.config)
        with self.assertRaisesRegex(ValueError, 'borrador'):
            self.store.perform(self.chat_id, state['id'], 'execute', 'Nueva instrucción', self.config)
        self.assertEqual(len(self.calls), 7)
        self.store.perform(self.chat_id, state['id'], 'execute', '', self.config)
        result = self.wait(self.chat_id)
        self.assertEqual(result['phase'], 'done')
        self.assertEqual(sum(writable for _, _, writable in self.calls), 3)

    def test_migration_preserves_original_records_and_imports_history_without_inference(self):
        legacy = self.folder / 'old' / 'tasks'
        engine = Harness(self.runner, legacy)
        engine.start('HISTORIA ANTIGUA', self.config)
        deadline = time.monotonic() + 4
        while engine.snapshot()['busy'] and time.monotonic() < deadline:
            Event().wait(.01)
        self.assertFalse(engine.snapshot()['busy'])
        task_id = engine.snapshot()['task_id']
        original = (legacy / f'{task_id}.json').read_bytes()
        before = len(self.calls)
        migrated = WorkspaceStore(legacy.parent, self.config, self.runner)
        self.assertEqual(migrated.data['selected'], task_id)
        self.assertEqual(migrated.engine(task_id).snapshot()['task'], 'HISTORIA ANTIGUA')
        self.assertEqual(migrated.engine(task_id).snapshot()['phase'], 'restored')
        self.assertEqual((legacy / f'{task_id}.json').read_bytes(), original)
        self.assertEqual(len(self.calls), before)
        again = WorkspaceStore(legacy.parent, self.config, self.runner)
        self.assertEqual(len(again.data['chats']), 1)

    def test_failed_metadata_write_prevents_inference_and_preserves_existing_index(self):
        before = self.store.path.read_bytes()
        engine = self.store.engine(self.chat_id)
        with patch('workspaces.write_json', side_effect=OSError('Disco lleno')):
            with self.assertRaises(OSError):
                self.store.perform(self.chat_id, engine.snapshot()['id'], 'start', 'NUEVO', self.config)
        self.assertEqual(self.store.path.read_bytes(), before)
        self.assertEqual(self.store.chat(self.chat_id)['title'], 'Nuevo chat')
        self.assertFalse(self.calls)

    def test_invalid_ids_and_project_changes_are_rejected(self):
        for key in ('../config', '', 'a' * 32, None):
            with self.assertRaises(ValueError):
                self.store.engine(key)
        config = deepcopy(self.config)
        other = self.folder / 'other'
        other.mkdir()
        config['workspace'] = str(other)
        with self.assertRaisesRegex(ValueError, 'pertenece al proyecto'):
            self.store.perform(self.chat_id, self.store.engine(self.chat_id).snapshot()['id'], 'save', '', config)

    def test_corrupt_index_is_preserved_instead_of_overwritten(self):
        self.store.path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError):
            WorkspaceStore(self.folder / '.magi', self.config)
        self.assertEqual(self.store.path.read_text(), '{broken')


if __name__ == '__main__':
    unittest.main()
