from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import Event
import time
import unittest
from unittest.mock import patch

import ai
from harness import DEFAULT_CONFIG, Harness, parse_route, parse_vote
from workspaces import WorkspaceStore


class AdaptiveTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.config = deepcopy(DEFAULT_CONFIG)
        self.config['workspace'] = str(self.folder)
        for name, node in self.config['nodes'].items():
            node['model'] = name
        cli = patch('ai.command_for', return_value=(['unused'], {}))
        cli.start()
        self.addCleanup(cli.stop)

    def wait(self, engine):
        deadline = time.monotonic() + 5
        while engine.snapshot()['busy'] and time.monotonic() < deadline:
            Event().wait(.01)
        self.assertFalse(engine.snapshot()['busy'])
        return engine.snapshot()

    def test_auto_question_answers_in_one_read_only_call_without_a_plan(self):
        calls = []
        def runner(node, prompt, workspace, cancel, writable=False):
            calls.append((prompt, writable))
            return '{"route":"answer","reply":"Un harness coordina herramientas y modelos."}'
        engine = Harness(runner, self.folder / 'history')
        engine.submit('¿Qué es un harness?', self.config, engine.snapshot()['id'])
        state = self.wait(engine)
        self.assertEqual(len(calls), 1)
        self.assertFalse(calls[0][1])
        self.assertEqual(state['plan'], '')
        self.assertEqual(state['task_id'], '')
        self.assertEqual(state['dialogue'][-1]['status'], 'answer')
        restored = Harness(runner, self.folder / 'history')
        self.assertEqual(restored.snapshot()['dialogue'][-1]['reply'], state['dialogue'][-1]['reply'])
        self.assertEqual(len(calls), 1)

    def test_ask_preserves_the_exact_approved_task_and_its_authorization(self):
        calls = []
        def runner(node, prompt, workspace, cancel, writable=False):
            calls.append((prompt, writable))
            if 'MENSAJE DEL USUARIO' in prompt:
                return 'El plan cambia solo el título.'
            return '{"vote":"yes","reason":"OK"}' if 'Devuelve solo JSON' in prompt else 'PLAN ORIGINAL'
        engine = Harness(runner)
        engine.start('Cambia el título', self.config)
        state = self.wait(engine)
        before = deepcopy(engine.state)
        engine.submit('¿Qué vas a cambiar?', self.config, state['id'], 'ask')
        self.wait(engine)
        self.assertEqual(engine.state, before)
        self.assertIn('PLAN ORIGINAL', calls[-1][0])
        self.assertFalse(calls[-1][1])
        engine.execute(state['id'], state['request'], self.config)
        self.assertEqual(self.wait(engine)['phase'], 'done')

    def test_bad_routing_cannot_start_a_task_or_write(self):
        for response in ('Plan', '{"route":"work","reply":"Cambiar","plan":"Modificar"}',
                         '{"route":"unknown","reply":"No"}'):
            engine = Harness(lambda *args, **kwargs: response)
            engine.submit('Explícame este proyecto', self.config, engine.snapshot()['id'])
            state = self.wait(engine)
            self.assertEqual(state['dialogue'][-1]['status'], 'error')
            self.assertEqual(state['task_id'], '')
            self.assertEqual(state['plan'], '')

    def test_small_change_has_one_writer_and_one_independent_reviewer(self):
        self.config['automation']['mode'] = 'autonomous'
        calls = []
        def runner(node, prompt, workspace, cancel, writable=False):
            calls.append((node['model'], writable, prompt))
            if 'DECISION DE RUTA' in prompt:
                return '{"route":"work","reply":"Cambio local","edit_requested":true,"plan":"Crear title.txt"}'
            if writable:
                (Path(workspace) / 'title.txt').write_text('MAGI', encoding='utf-8')
                return 'Archivo creado y leído.'
            self.assertEqual((Path(workspace) / 'title.txt').read_text(), 'MAGI')
            return '{"vote":"yes","reason":"Comprobado","suggestions":["Podría añadirse otro color más adelante"]}'
        engine = Harness(runner)
        engine.submit('Crea title.txt', self.config, engine.snapshot()['id'])
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'done')
        self.assertEqual(state['workflow'], 'direct')
        self.assertEqual([(name, write) for name, write, _ in calls], [('melchior', False), ('melchior', True), ('balthasar', False)])
        self.assertEqual(state['usage']['repairs'], 0)
        self.assertEqual(state['answers']['casper']['status'], 'info')

    def test_manual_small_change_needs_explicit_execution(self):
        writes = []
        def runner(node, prompt, *args, writable=False):
            if writable:
                writes.append(prompt)
            if 'DECISION DE RUTA' in prompt:
                return '{"route":"work","reply":"Cambio local","edit_requested":true,"plan":"Cambiar título"}'
            return '{"vote":"yes","reason":"OK"}' if 'Devuelve solo JSON' in prompt else 'Hecho'
        engine = Harness(runner)
        engine.submit('Cambia el título', self.config, engine.snapshot()['id'])
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'ready')
        self.assertFalse(writes)
        engine.execute(state['id'], state['request'], self.config)
        self.assertEqual(self.wait(engine)['phase'], 'done')
        self.assertEqual(len(writes), 1)

    def test_routing_can_leave_a_stale_plan_discussion_and_enable_only_execution_writes(self):
        for mode in ('auto', 'work', 'council'):
            with self.subTest(mode=mode):
                calls = []
                target = self.folder / f'{mode}.html'
                def runner(node, prompt, workspace, cancel, writable=False):
                    calls.append(writable)
                    if 'DECISION DE RUTA' in prompt:
                        self.assertIn(f'Modo de solicitud seleccionado en MAGI: {mode}', prompt)
                        self.assertIn('Build en OpenCode', prompt)
                        self.assertIn('workspace-write en Codex', prompt)
                        self.assertIn('No pidas al usuario cambiar de agente', prompt)
                        self.assertIn('portafolio azul navy', prompt)
                        self.assertFalse(writable)
                        return '{"route":"work","reply":"Implementar el diseño acordado","edit_requested":true,"plan":"Crear el HTML del portafolio con placeholders"}'
                    if writable:
                        target.write_text('<h1>Tu nombre</h1>', encoding='utf-8')
                        return 'Portafolio guardado.'
                    return '{"vote":"yes","reason":"Comprobado"}' if 'Devuelve solo JSON' in prompt else 'Crear el HTML del portafolio.'
                engine = Harness(runner)
                engine.dialogue.append({'question': 'Construye mi portafolio azul navy con placeholders',
                    'reply': 'Estoy en modo plan y solo lectura. Cambia al agente de edición.',
                    'status': 'answer', 'node': 'melchior', 'mode': 'council', 'after_iteration': 0,
                    'calls': 4, 'activity': 'Respuesta lista', 'at': '2026-10-19T21:00:00Z'})
                engine.submit('Listo, comienza a trabajar', self.config, engine.snapshot()['id'], mode)
                state = self.wait(engine)
                self.assertEqual(state['phase'], 'ready', state['dialogue'][-1])
                self.assertFalse(any(calls))
                self.assertFalse(target.exists())
                engine.execute(state['id'], state['request'], self.config)
                self.assertEqual(self.wait(engine)['phase'], 'done')
                self.assertEqual(target.read_text(encoding='utf-8'), '<h1>Tu nombre</h1>')

    def test_council_question_gets_three_opinions_and_no_implementation(self):
        calls = []
        def runner(node, prompt, *args, writable=False):
            calls.append((node['model'], writable))
            return '{"route":"answer","reply":"Depende del contexto."}' if 'DECISION DE RUTA' in prompt else 'Respuesta breve'
        engine = Harness(runner)
        engine.submit('¿Qué opinan los tres?', self.config, engine.snapshot()['id'], 'council')
        state = self.wait(engine)
        self.assertEqual(len(calls), 4)
        self.assertFalse(any(writable for _, writable in calls))
        self.assertEqual(set(state['dialogue'][-1]['opinions']), {'melchior', 'balthasar', 'casper'})
        self.assertEqual(state['task_id'], '')

    def test_complex_work_escalates_to_the_three_original_votes(self):
        calls = []
        def runner(node, prompt, *args, writable=False):
            calls.append((node['model'], writable))
            if 'DECISION DE RUTA' in prompt:
                return '{"route":"council","reply":"Necesita al equipo","edit_requested":true,"plan":"Evaluar arquitectura"}'
            return '{"vote":"yes","reason":"OK","suggestions":["Mejora futura opcional"]}' if 'Devuelve solo JSON' in prompt else 'PLAN COMUN'
        engine = Harness(runner)
        engine.submit('Implementa autenticación', self.config, engine.snapshot()['id'])
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'ready')
        self.assertEqual(state['workflow'], 'council')
        self.assertEqual(len(calls), 8)
        self.assertTrue(all(answer['status'] == 'yes' for answer in state['answers'].values()))
        self.assertFalse(any(write for _, write in calls))

    def test_a_small_change_with_a_real_review_blocker_stops(self):
        self.config['automation']['mode'] = 'manual'
        def runner(node, prompt, *args, writable=False):
            if 'DECISION DE RUTA' in prompt:
                return '{"route":"work","reply":"Cambio local","edit_requested":true,"plan":"Cambiar título"}'
            return 'No fue posible guardar' if writable else '{"vote":"conditional","reason":"Falta el archivo requerido"}'
        engine = Harness(runner)
        engine.submit('Cambia el título', self.config, engine.snapshot()['id'])
        state = self.wait(engine)
        engine.execute(state['id'], state['request'], self.config)
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'changes_requested')
        self.assertEqual(state['status'], 'conditional')

    def test_busy_query_blocks_deletion_and_failed_save_prevents_inference(self):
        entered, release = Event(), Event()
        def runner(*args, **kwargs):
            entered.set()
            release.wait(3)
            return 'Respuesta'
        store = WorkspaceStore(self.folder / '.magi', self.config, runner)
        chat_id = store.data['selected']
        engine = store.engine(chat_id)
        config = store.chat(chat_id)['config']
        with patch.object(engine, 'persist_dialogue', side_effect=OSError('Disco lleno')):
            with self.assertRaises(OSError):
                store.perform(chat_id, engine.snapshot()['id'], 'start', 'Pregunta', config, request_mode='ask')
        self.assertFalse(entered.is_set())
        self.assertFalse(engine.dialogue)
        try:
            store.perform(chat_id, engine.snapshot()['id'], 'start', 'Pregunta', config, request_mode='ask')
            self.assertTrue(entered.wait(1))
            with self.assertRaisesRegex(ValueError, 'trabajando'):
                store.delete_chat(chat_id)
        finally:
            release.set()
            self.wait(engine)

    def test_cancelled_query_leaves_the_work_state_untouched(self):
        entered = Event()
        def runner(node, prompt, workspace, cancel):
            entered.set()
            cancel.wait(3)
            raise ai.Cancelled()
        engine = Harness(runner)
        before = deepcopy(engine.state)
        engine.submit('Pregunta', self.config, engine.snapshot()['id'], 'ask')
        self.assertTrue(entered.wait(1))
        engine.cancel()
        self.assertEqual(self.wait(engine)['dialogue'][-1]['status'], 'cancelled')
        self.assertEqual(engine.state, before)

    def test_real_blockers_are_not_converted_to_optional_suggestions(self):
        vote = parse_vote('{"vote":"conditional","reason":"No se guardó el archivo","suggestions":["Cambiar el color"]}')
        self.assertEqual(vote['status'], 'conditional')
        with self.assertRaises(ValueError):
            parse_route('{"route":"work","reply":"Falta autorización","edit_requested":false,"plan":"Editar"}')

    def test_corrupt_question_history_is_not_overwritten(self):
        path = self.folder / 'conversation' / 'messages.json'
        path.parent.mkdir()
        path.write_text('{broken', encoding='utf-8')
        engine = Harness(lambda *args: 'No', self.folder)
        with self.assertRaisesRegex(ValueError, 'conserva'):
            engine.submit('Pregunta', self.config, engine.snapshot()['id'])
        self.assertEqual(path.read_text(), '{broken')


class LiveEventsTests(unittest.TestCase):
    def test_progress_is_delivered_before_process_completion(self):
        received = []
        program = ("import sys,json,time; sys.stdin.read(); "
                   "print(json.dumps({'type':'item.started','item':{'type':'command_execution'}}),flush=True); "
                   "time.sleep(.8); "
                   "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'Final'}}),flush=True); "
                   "print(json.dumps({'type':'turn.completed'}),flush=True)")
        with tempfile.TemporaryDirectory() as folder, patch('ai.command_for', return_value=([sys.executable, '-c', program], os.environ.copy())):
            result = ai.run_agent({'provider': 'codex'}, 'Test', folder, Event(), on_event=lambda event: received.append((event, time.monotonic())))
        self.assertEqual(result, 'Final')
        self.assertEqual(received[0][0]['activity'], 'Ejecutando una comprobación…')
        self.assertEqual(received[-1][0]['text'], 'Final')
        self.assertGreater(received[-1][1] - received[0][1], .1)
        self.assertNotIn('command', received[0][0])


if __name__ == '__main__':
    unittest.main()
