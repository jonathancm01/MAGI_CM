from copy import deepcopy
from collections import Counter
import json
from pathlib import Path
import tempfile
from threading import Barrier, Event, Lock
import time
import unittest
from unittest.mock import patch

import ai
from harness import DEFAULT_CONFIG, Harness, NAMES, validate_config
from presentation import readable_entry, text_blocks


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = deepcopy(DEFAULT_CONFIG)
        self.config['workspace'] = self.directory.name
        for name in NAMES:
            self.config['nodes'][name]['model'] = name
        commands = patch('ai.command_for', return_value=(['unused'], {}))
        commands.start()
        self.addCleanup(commands.stop)

    def wait(self, engine):
        deadline = time.monotonic() + 5
        while engine.snapshot()['busy'] and time.monotonic() < deadline:
            Event().wait(.01)
        self.assertFalse(engine.snapshot()['busy'], engine.snapshot()['message'])
        return engine.snapshot()

    @staticmethod
    def answer(prompt):
        return '{"vote":"yes","reason":"Comprobado"}' if 'Devuelve solo JSON' in prompt else 'PLAN ORIGINAL'

    def test_conditions_are_shared_and_resolved_in_a_second_deliberation(self):
        calls = []
        def runner(node, prompt, *args, **kwargs):
            calls.append((node['model'], prompt, kwargs.get('writable', False)))
            cycle = engine.snapshot()['usage']['cycle']
            if 'Devuelve solo JSON' in prompt:
                return json.dumps({'vote': 'conditional' if cycle == 1 and node['model'] == 'casper' else 'yes',
                                   'reason': 'FALTA VALIDAR EL TECLADO' if cycle == 1 else 'Condición resuelta'})
            return f'PLAN CICLO {cycle} DE {node["model"]}'
        engine = Harness(runner)
        engine.start('OBJETIVO', self.config)
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'ready')
        self.assertEqual(len(calls), 14)
        self.assertFalse(any(writable for _, _, writable in calls))
        self.assertTrue(all('FALTA VALIDAR EL TECLADO' in prompt for _, prompt, _ in calls[7:11]))
        self.assertEqual(state['plan'], 'PLAN CICLO 2 DE melchior')
        self.assertTrue(any(entry['sender'] == 'system' for entry in state['communications']))
        self.assertFalse(any(entry['text'].startswith('{"vote"') for entry in state['communications']))

    def test_cycles_and_budget_stop_without_unlimited_inference(self):
        for limit, expected_phase, expected_calls in ((24, 'blocked', 14), (6, 'limit', 0), (7, 'limit', 7)):
            with self.subTest(limit=limit):
                config = deepcopy(self.config)
                config['automation'].update(max_cycles=2, max_calls=limit)
                calls = []
                def runner(node, prompt, *args):
                    calls.append(prompt)
                    return '{"vote":"conditional","reason":"Pendiente"}' if 'Devuelve solo JSON' in prompt else 'Plan'
                engine = Harness(runner)
                engine.start('TAREA', config)
                state = self.wait(engine)
                self.assertEqual(state['phase'], expected_phase)
                self.assertEqual(len(calls), expected_calls)
                self.assertEqual(state['usage']['calls'], expected_calls)

    def test_retry_only_the_transiently_failed_nucleus(self):
        attempts = Counter()
        def runner(node, prompt, *args):
            attempts[node['model']] += 1
            if node['model'] == 'casper' and attempts['casper'] == 1:
                raise RuntimeError('503 service unavailable')
            return self.answer(prompt)
        engine = Harness(runner)
        engine.start('TAREA', self.config)
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'ready')
        self.assertEqual(attempts, {'melchior': 3, 'balthasar': 2, 'casper': 3})
        self.assertEqual(state['usage']['calls'], 8)
        self.assertEqual(state['answers']['casper']['error'], '')
        self.assertTrue(any(entry.get('retry') for entry in state['answers']['casper']['history']))

    def test_model_auth_and_quota_errors_do_not_retry_or_skip_a_vote(self):
        for diagnostic, kind in [('Invalid model reference', 'model'), ('401 unauthorized', 'auth'), ('429 quota exceeded', 'quota')]:
            with self.subTest(kind=kind):
                calls = []
                def runner(node, prompt, *args):
                    calls.append(node['model'])
                    if node['model'] == 'casper':
                        raise RuntimeError(diagnostic)
                    return self.answer(prompt)
                engine = Harness(runner)
                engine.start('TAREA', self.config)
                state = self.wait(engine)
                self.assertEqual(state['phase'], 'error')
                self.assertEqual(len(calls), 3)
                self.assertEqual(state['answers']['casper']['error_info']['kind'], kind)
                self.assertIn('CASPER', state['message'])

    def test_three_agents_contribute_with_parallel_preparation_and_exclusive_writes(self):
        barrier, lock, writes = Barrier(3), Lock(), []
        concurrent = 0
        peak = 0
        def runner(node, prompt, workspace, cancel, writable=False):
            nonlocal concurrent, peak
            name = node['model']
            if engine.snapshot()['phase'] == 'execution':
                if not writable or name == 'melchior':
                    barrier.wait(2)
                if writable:
                    with lock:
                        concurrent += 1
                        peak = max(peak, concurrent)
                    try:
                        if name != 'melchior':
                            self.assertIn('INFORME melchior', prompt)
                        Path(workspace, f'{name}.txt').write_text(name)
                        writes.append(name)
                    finally:
                        with lock:
                            concurrent -= 1
                    return 'INFORME ' + name
                return 'APORTE ' + name
            return self.answer(prompt)
        engine = Harness(runner)
        engine.start('Implementa el plan', self.config)
        state = self.wait(engine)
        engine.execute(state['id'], state['request'], self.config)
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'done', state['message'])
        self.assertEqual(peak, 1)
        self.assertEqual(writes, list(NAMES))
        self.assertEqual(state['usage']['calls'], 8)
        self.assertTrue(all(Path(self.directory.name, f'{name}.txt').exists() for name in NAMES))
        self.assertTrue(all('INFORME ' + name in state['execution_report'] for name in NAMES))

    def test_integrated_plan_is_voted_and_each_writer_has_a_cross_reviewer(self):
        integrated = 'PLAN INTEGRADO: base + teclado + presentación. Reparto: MELCHIOR base; BALTHASAR teclado; CASPER presentación.'
        reviews = {}
        def runner(node, prompt, workspace, cancel, writable=False):
            name = node['model']
            if 'PROPUESTAS INDEPENDIENTES:' in prompt:
                self.assertFalse(writable)
                for other in NAMES:
                    self.assertIn('PROPUESTA ' + other, prompt)
                return integrated
            if 'Devuelve solo JSON' in prompt:
                if engine.snapshot()['phase'] == 'voting':
                    self.assertIn('PLAN EXACTO A VOTAR:\n' + integrated, prompt)
                else:
                    target = NAMES[(NAMES.index(name) + 1) % 3]
                    self.assertIn('REVISIÓN CRUZADA: verifica especialmente el entregable de ' + target.upper(), prompt)
                    self.assertTrue(Path(workspace, target + '.txt').exists())
                    reviews[name] = target
                return '{"vote":"yes","reason":"Archivo comprobado"}'
            if writable:
                self.assertIn('ENCARGO EXCLUSIVO DE ' + name.upper(), prompt)
                self.assertIn(integrated, prompt)
                self.assertIn('Verificaciones ejecutadas y resultados', prompt)
                Path(workspace, name + '.txt').write_text(name)
                return f'Archivos afectados: {name}.txt. Verificación: archivo guardado.'
            return 'PROPUESTA ' + name
        engine = Harness(runner)
        engine.start('Construir base, teclado y presentación', self.config)
        state = self.wait(engine)
        self.assertEqual(state['plan'], integrated)
        self.assertTrue(any(item['phase'] == 'Síntesis del plan' for item in state['communications']))
        engine.execute(state['id'], state['request'], self.config)
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'done')
        self.assertEqual(len(reviews), 3)
        self.assertTrue(all(author != reviewer for reviewer, author in reviews.items()))
        for name in NAMES:
            self.assertTrue(any(item.get('writable') for item in state['answers'][name]['history']))

    def test_empty_synthesis_never_reaches_vote_or_writes(self):
        calls = []
        def runner(node, prompt, *args, **kwargs):
            calls.append((prompt, kwargs.get('writable', False)))
            return '' if 'PROPUESTAS INDEPENDIENTES:' in prompt else 'Propuesta'
        engine = Harness(runner)
        engine.start('TAREA', self.config)
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'error')
        self.assertEqual(len(calls), 4)
        self.assertFalse(any(writable or 'PLAN EXACTO A VOTAR:' in prompt for prompt, writable in calls))

    def test_review_conditions_trigger_team_repairs_inside_the_same_approved_plan(self):
        repairs = []
        def runner(node, prompt, *args, writable=False):
            state = engine.snapshot()
            if state['phase'] == 'review' and 'Devuelve solo JSON' in prompt:
                if node['model'] == 'casper' and state['usage']['repairs'] == 0:
                    return '{"vote":"conditional","reason":"CORREGIR EL RETORNO"}'
                return '{"vote":"yes","reason":"Corregido"}'
            if writable:
                if state['usage']['repairs']:
                    repairs.append(prompt)
                return 'INFORME DEL APORTE'
            return self.answer(prompt)
        engine = Harness(runner)
        engine.start('TAREA', self.config)
        state = self.wait(engine)
        engine.execute(state['id'], state['request'], self.config)
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'done')
        self.assertEqual(state['usage']['repairs'], 1)
        self.assertEqual(state['usage']['calls'], 16)
        self.assertEqual(len(repairs), 3)
        self.assertTrue(all('CORREGIR EL RETORNO' in prompt and 'PLAN ORIGINAL' in prompt for prompt in repairs))
        self.assertEqual(state['execution_plan'], 'PLAN ORIGINAL')

    def test_autonomous_mode_implements_after_unanimous_approval_and_respects_budget(self):
        for limit, expected, writes in ((24, 'done', 3), (12, 'limit', 0)):
            config = deepcopy(self.config)
            config['automation'].update(mode='autonomous', max_calls=limit)
            written = []
            def runner(node, prompt, *args, writable=False):
                if writable:
                    written.append(node['model'])
                return self.answer(prompt)
            engine = Harness(runner)
            engine.start('OBJETIVO AUTORIZADO', config)
            state = self.wait(engine)
            self.assertEqual(state['phase'], expected)
            self.assertEqual(len(written), writes)
            self.assertLessEqual(state['usage']['calls'], limit)

    def test_re_review_stays_read_only_even_in_autonomous_mode(self):
        config = deepcopy(self.config)
        config['automation']['mode'] = 'autonomous'
        engine = Harness(lambda node, prompt, *args, **kwargs: self.answer(prompt))
        engine.start('TAREA', config)
        state = self.wait(engine)
        calls = []
        def review(node, prompt, *args, writable=False):
            calls.append(writable)
            return '{"vote":"conditional","reason":"Verificación pendiente"}'
        engine.runner = review
        engine.review_again(state['id'], config)
        state = self.wait(engine)
        self.assertEqual(calls, [False] * 3)
        self.assertEqual(state['phase'], 'changes_requested')

    def test_cancellation_stops_automatic_deliberation(self):
        entered = Event()
        def runner(node, prompt, workspace, cancel):
            if engine.snapshot()['usage']['cycle'] > 1:
                entered.set()
                cancel.wait(3)
                raise ai.Cancelled()
            return '{"vote":"conditional","reason":"Pendiente"}' if 'Devuelve solo JSON' in prompt else 'Plan'
        engine = Harness(runner)
        engine.start('TAREA', self.config)
        self.assertTrue(entered.wait(2))
        engine.cancel()
        self.assertEqual(self.wait(engine)['phase'], 'cancelled')

    def test_invalid_automation_and_readable_legacy_votes(self):
        for field, value in [('mode', 'unsafe'), ('max_cycles', 99), ('max_calls', True), ('max_calls', 0)]:
            config = deepcopy(self.config)
            config['automation'][field] = value
            with self.assertRaises(ValueError):
                validate_config(config)
        entry = readable_entry({'phase': 'Voto', 'text': '{"vote":"conditional","reason":"Comprueba el teclado"}'})
        self.assertEqual(entry['text'], 'Comprueba el teclado')
        self.assertEqual(entry['label'], 'Con condiciones')
        self.assertEqual(entry['blocks'], [{'type': 'paragraph', 'text': 'Comprueba el teclado'}])
        self.assertEqual([block['type'] for block in text_blocks('## Informe\n\n- Cambio\n\n```js\nconst x = 1;\n```')],
                         ['heading', 'list', 'code'])
        self.assertEqual(text_blocks('| Núcleo | Estado |\n|---|---|\n| Melchior | Listo |'),
                         [{'type': 'table', 'headers': ['Núcleo', 'Estado'], 'rows': [['Melchior', 'Listo']]}])

    def test_parallel_proposals_use_the_same_previous_messages_snapshot(self):
        proposals = []
        def runner(node, prompt, *args):
            if engine.snapshot()['phase'] == 'analysis' and 'PROPUESTAS INDEPENDIENTES:' not in prompt:
                proposals.append(prompt)
                return 'PROPUESTA PRIVADA ' + node['model']
            return '{"vote":"yes","reason":"OK"}'
        engine = Harness(runner)
        engine.start('TAREA', self.config)
        self.wait(engine)
        self.assertEqual(len(proposals), 3)
        self.assertTrue(all('PROPUESTA PRIVADA' not in prompt for prompt in proposals))

    def test_malformed_vote_is_retried_once_and_preserves_its_diagnostic(self):
        votes = Counter()
        def runner(node, prompt, *args):
            if 'Devuelve solo JSON' in prompt:
                votes[node['model']] += 1
                if node['model'] == 'casper' and votes['casper'] == 1:
                    return 'Respuesta sin el voto solicitado'
            return self.answer(prompt)
        engine = Harness(runner)
        engine.start('TAREA', self.config)
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'ready')
        self.assertEqual(votes, {'melchior': 1, 'balthasar': 1, 'casper': 2})
        errors = [entry for entry in state['answers']['casper']['history'] if entry['status'] == 'error']
        self.assertIn('Respuesta sin el voto solicitado', errors[0]['error_info']['detail'])

    def test_repeated_review_conditions_stop_before_all_five_cycles(self):
        config = deepcopy(self.config)
        config['automation'].update(max_cycles=5, max_calls=120)
        def runner(node, prompt, *args, **kwargs):
            if engine.snapshot()['phase'] == 'review':
                return '{"vote":"conditional","reason":"Falta acceso al navegador"}'
            return self.answer(prompt)
        engine = Harness(runner)
        engine.start('TAREA', config)
        state = self.wait(engine)
        engine.execute(state['id'], state['request'], config)
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'changes_requested')
        self.assertEqual(state['usage']['calls'], 16)
        self.assertTrue(any(entry['phase'] == 'Sin progreso' for entry in state['communications']))

    def test_failed_writer_preserves_previous_contributions_and_is_not_retried(self):
        writes = []
        def runner(node, prompt, workspace, cancel, writable=False):
            if writable:
                writes.append(node['model'])
                if node['model'] == 'balthasar':
                    raise RuntimeError('503 network failure')
                Path(workspace, 'base.txt').write_text('conservar')
                return 'BASE IMPLEMENTADA'
            return self.answer(prompt)
        engine = Harness(runner)
        engine.start('TAREA', self.config)
        state = self.wait(engine)
        engine.execute(state['id'], state['request'], self.config)
        state = self.wait(engine)
        self.assertEqual(state['phase'], 'error')
        self.assertEqual(writes, ['melchior', 'balthasar'])
        self.assertIn('BASE IMPLEMENTADA', state['execution_report'])
        self.assertEqual(Path(self.directory.name, 'base.txt').read_text(), 'conservar')
        self.assertFalse(state['answers']['balthasar']['error_info']['retryable'])

    def test_autonomous_state_does_not_resume_after_restart(self):
        config = deepcopy(self.config)
        config['automation']['mode'] = 'autonomous'
        storage = Path(self.directory.name) / 'history'
        engine = Harness(lambda node, prompt, *args, **kwargs: self.answer(prompt), storage)
        engine.start('TAREA', config)
        state = self.wait(engine)
        path = storage / f"{state['task_id']}.json"
        record = json.loads(path.read_text(encoding='utf-8'))
        record['state'].update(phase='execution', busy=True)
        path.write_text(json.dumps(record), encoding='utf-8')
        restored = Harness(lambda *args: self.fail('No debe haber inferencias al recuperar'), storage)
        self.assertEqual(restored.snapshot()['phase'], 'interrupted')
        self.assertFalse(restored.snapshot()['busy'])

    def test_failed_call_checkpoint_cancels_the_team_before_starting_the_model(self):
        calls = []
        engine = Harness(lambda *args, **kwargs: calls.append(args))
        engine.config = validate_config(self.config)
        engine.reset_usage()
        with patch.object(engine, 'persist', side_effect=RuntimeError('No se pudo guardar')):
            with self.assertRaises(RuntimeError):
                engine.call('melchior', 'Ejecución', 'PLAN', writable=True)
        self.assertFalse(calls)
        self.assertTrue(engine.cancelled.is_set())
        self.assertTrue(engine.snapshot()['busy'])


if __name__ == '__main__':
    unittest.main()
