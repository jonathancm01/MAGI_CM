from copy import deepcopy
import json
from pathlib import Path
import tempfile
from threading import Event
import time
import unittest
from unittest.mock import patch

from harness import DEFAULT_CONFIG, NAMES
from workspaces import WorkspaceStore

_app_directory = tempfile.TemporaryDirectory()
with patch('workspaces.WorkspaceStore', return_value=WorkspaceStore(Path(_app_directory.name) / '.magi', DEFAULT_CONFIG)):
    import main


class WebTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.config = deepcopy(DEFAULT_CONFIG)
        self.config['workspace'] = directory.name
        self.store = WorkspaceStore(Path(directory.name) / '.magi', self.config)
        self.chat_id = self.store.data['selected']
        self.config = self.store.chat(self.chat_id)['config']
        self.engine = self.store.engine(self.chat_id)
        self.client = main.app.server.test_client()
        replacement = patch('main.controller', self.store)
        replacement.start()
        self.addCleanup(replacement.stop)

    def post(self, key, values, changed):
        callback = main.app.callback_map[key]
        outputs = callback['output']
        outputs = [dict(id=item.component_id, property=item.component_property) for item in outputs]
        inputs = [{**item, 'value': values.get(item['id'], [])} for item in callback['inputs']]
        states = [{**item, 'value': values.get(item['id'])} for item in callback['state']]
        return self.client.post('/_dash-update-component', json={
            'output': key, 'outputs': outputs, 'inputs': inputs, 'state': states, 'changedPropIds': [changed],
        })

    def action_values(self):
        values = {'query': '', 'workspace': self.config['workspace'], 'consensus': 'majority',
                  'executor': 'casper', 'view': {'chat_id': self.chat_id}, 'composer-chat': self.chat_id,
                  'session': {'chat_id': self.chat_id, 'id': self.engine.snapshot()['id']}}
        values.update({key: 0 for key in ('start', 'save', 'execute', 'review', 'cancel')})
        for index, name in enumerate(NAMES):
            values.update({f'provider-{name}': 'codex' if index < 2 else 'opencode',
                           f'model-{name}': f'model-{index}' if index < 2 else 'opencode/model-2',
                           f'instructions-{name}': f'perspective-{index}'})
        return values

    def action_key(self):
        return next(key for key, callback in main.app.callback_map.items()
                    if any(item['id'] == 'start' and item['property'] == 'n_clicks' for item in callback['inputs']))

    def test_activity_shows_current_contributions_without_mixing_previous_iterations(self):
        self.engine.state['iteration'] = 2
        self.engine.state['answers']['melchior']['history'] = [
            {'sender': 'melchior', 'phase': 'Ejecución', 'iteration': 1, 'text': 'APORTE ANTERIOR'},
            {'sender': 'melchior', 'phase': 'Ejecución', 'iteration': 2, 'text': 'ARCHIVO ACTUAL COMPROBADO'},
            {'sender': 'melchior', 'phase': 'Revisión del resultado', 'iteration': 2, 'text': 'REVISIÓN CRUZADA ACTUAL'},
        ]
        cards = main.refresh(0, {'chat_id': self.chat_id}, None, None)[20]
        rendered = json.dumps(cards, default=lambda component: component.to_plotly_json(), ensure_ascii=False)
        self.assertIn('Aportes y verificaciones', rendered)
        self.assertIn('ARCHIVO ACTUAL COMPROBADO', rendered)
        self.assertIn('REVISIÓN CRUZADA ACTUAL', rendered)
        self.assertNotIn('APORTE ANTERIOR', rendered)

    def test_budget_indicator_uses_real_call_count_and_saved_limit(self):
        self.engine.state['usage']['calls'] = 5
        self.store.data['chats'][self.chat_id]['config']['automation']['max_calls'] = 30
        activity = main.refresh(0, {'chat_id': self.chat_id}, None, None)[26]
        meter = activity[1].to_plotly_json()['props']
        self.assertEqual(meter['value'], 5)
        self.assertEqual(meter['max'], 30)
        self.assertIn('presupuesto', meter['aria-label'])
        self.engine.config = deepcopy(self.config)
        self.engine.state['usage']['limit'] = 18
        activity = main.refresh(0, {'chat_id': self.chat_id}, None, None)[26]
        self.assertEqual(activity[1].to_plotly_json()['props']['max'], 18)

    def test_loopback_origin_and_content_type_boundaries(self):
        self.assertEqual(self.client.get('/_dash-layout').status_code, 200)
        self.assertEqual(self.client.get('/', base_url='http://evil.example').status_code, 403)
        self.assertEqual(self.client.post('/_dash-update-component', json={},
                                         headers={'Origin': 'https://evil.example'}).status_code, 403)
        self.assertEqual(self.client.post('/_dash-update-component', data='not json').status_code, 415)

    def test_form_saves_all_three_nodes_only_in_current_chat(self):
        values = self.action_values()
        values['save'] = 1
        second = self.store.new_chat(self.store.chat(self.chat_id)['project_id'])
        response = self.post(self.action_key(), values, 'save.n_clicks')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertIn('Configuración guardada', response.json['response']['configuration-notice']['children'])
        stored = self.store.chat(self.chat_id)['config']
        self.assertEqual(stored['executor'], 'casper')
        for index, name in enumerate(NAMES):
            self.assertEqual(stored['nodes'][name]['model'], values[f'model-{name}'])
        self.assertEqual(self.store.chat(second)['config'], self.config)

    def test_configuration_dialog_shows_save_errors_without_losing_draft(self):
        values = self.action_values()
        values.update(save=1, query='Borrador que debo conservar')
        values['consensus'] = 'invalid'
        response = self.post(self.action_key(), values, 'save.n_clicks')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['response']['configuration-notice']['children'],
                         response.json['response']['notice']['children'])
        self.assertNotIn('query', response.json['response'])
        self.assertEqual(self.store.chat(self.chat_id)['config'], self.config)

    def test_new_chat_saves_previous_draft_and_loads_independent_form(self):
        values = {'new-task': 1, 'add-project': 0, 'composer-chat': self.chat_id, 'query': 'Borrador anterior',
                  'project-path': '', 'project-name': ''}
        key = next(key for key, callback in main.app.callback_map.items()
                   if any(item['id'] == 'new-task' for item in callback['inputs']))
        response = self.post(key, values, 'new-task.n_clicks')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        new_view = response.json['response']['view']['data']
        self.assertNotEqual(new_view['chat_id'], self.chat_id)
        new_folder = Path(self.store.chat(new_view['chat_id'])['config']['workspace'])
        self.assertNotEqual(str(new_folder), self.config['workspace'])
        self.assertTrue(new_folder.is_dir())
        self.assertEqual(new_folder.parent, self.store.storage.parent / 'projects')
        self.assertEqual(self.store.chat(self.chat_id)['draft'], 'Borrador anterior')
        self.assertEqual(main.load_chat(new_view)[0], '')
        self.assertEqual(main.load_chat({'chat_id': self.chat_id})[0], 'Borrador anterior')

    def test_switching_chat_reloads_its_own_models_and_stale_form_cannot_send(self):
        other = self.store.new_chat(self.store.chat(self.chat_id)['project_id'])
        config = deepcopy(self.config)
        config['nodes']['casper']['model'] = 'specific-model'
        self.store.perform(other, self.store.engine(other).snapshot()['id'], 'save', '', config)
        form = main.load_chat({'chat_id': other})
        self.assertIn('specific-model', form)
        self.assertIn('specific-model', [option['value'] for option in form[-1]])
        values = self.action_values()
        values.update(view={'chat_id': other}, start=1, query='No debe enviarse al chat equivocado')
        with patch.object(self.store, 'perform') as perform:
            response = self.post(self.action_key(), values, 'start.n_clicks')
        perform.assert_not_called()
        self.assertIn('cambiando', response.json['response']['notice']['children'])

    def test_sidebar_pattern_click_opens_the_selected_chat(self):
        other = self.store.new_chat(self.store.chat(self.chat_id)['project_id'])
        self.store.save_draft(other, 'Borrador de otro chat')
        key = next(key for key, callback in main.app.callback_map.items()
                   if any(item['id'] == 'new-task' for item in callback['inputs']))
        pattern = next(item['id'] for item in main.app.callback_map[key]['inputs'] if '"type":"chat"' in item['id'])
        values = {'new-task': 0, 'add-project': 0, pattern: [0, 1],
                  'composer-chat': self.chat_id, 'query': '', 'project-name': '', 'project-path': ''}
        changed = json.dumps({'type': 'chat', 'id': other}, sort_keys=True, separators=(',', ':')) + '.n_clicks'
        response = self.post(key, values, changed)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.json['response']['view']['data']['chat_id'], other)

    def test_refresh_keeps_drafts_and_does_not_replace_unchanged_conversation(self):
        view = {'chat_id': self.chat_id}
        first = main.refresh(0, view, None, None)
        second = main.refresh(1, view, first[22], first[24])
        self.assertEqual(first[0]['chat_id'], self.chat_id)
        self.assertIs(second[21], main.no_update)
        self.assertIs(second[23], main.no_update)
        refresh_key = next(key for key, callback in main.app.callback_map.items()
                           if any(item['id'] == 'poll' for item in callback['inputs']))
        outputs = main.app.callback_map[refresh_key]['output']
        self.assertFalse(any(item.component_id == 'query' for item in outputs))

    def test_sidebar_delete_and_restore_callbacks_preserve_the_draft(self):
        other = self.store.new_chat(self.store.chat(self.chat_id)['project_id'])
        key = next(key for key, callback in main.app.callback_map.items()
                   if any(item['id'] == 'new-task' for item in callback['inputs']))
        values = {'new-task': 0, 'add-project': 0, 'composer-chat': self.chat_id,
                  'query': 'Borrador para recuperar', 'view': {'chat_id': self.chat_id}}
        for kind, expected in (('delete-chat', other), ('restore-chat', self.chat_id)):
            pattern = next(item['id'] for item in main.app.callback_map[key]['inputs'] if f'"type":"{kind}"' in item['id'])
            values[pattern] = [1]
            changed = json.dumps({'type': kind, 'id': self.chat_id}, sort_keys=True, separators=(',', ':')) + '.n_clicks'
            response = self.post(key, values, changed)
            self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
            self.assertEqual(response.json['response']['view']['data']['chat_id'], expected)
            values.update({'composer-chat': expected, 'query': '', 'view': {'chat_id': expected}})
        self.assertEqual(self.store.chat(self.chat_id)['draft'], 'Borrador para recuperar')

    def test_deleted_chat_in_another_tab_recovers_without_overwriting_a_draft(self):
        self.store.delete_chat(self.chat_id)
        replacement = self.store.data['selected']
        self.store.save_draft(replacement, 'BORRADOR DEL OTRO CHAT')
        stale = {'chat_id': self.chat_id}
        form = main.load_chat(stale)
        self.assertEqual(form[:2], ('BORRADOR DEL OTRO CHAT', replacement))
        self.assertEqual(main.refresh(0, stale, None, None)[0]['chat_id'], replacement)
        key = next(key for key, callback in main.app.callback_map.items()
                   if any(item['id'] == 'new-task' for item in callback['inputs']))
        response = self.post(key, {'poll': 1, 'view': stale, 'composer-chat': replacement,
                                   'query': 'NO GUARDAR EN EL OTRO CHAT'}, 'poll.n_intervals')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.json['response']['view']['data']['chat_id'], replacement)
        self.assertEqual(self.store.chat(replacement)['draft'], 'BORRADOR DEL OTRO CHAT')

    def test_sidebar_exposes_labeled_delete_and_restore_buttons_and_protects_busy_chat(self):
        self.engine.state['busy'] = True
        tree = json.loads(json.dumps(main.sidebar(self.store.navigation(), self.chat_id), default=lambda component: component.to_plotly_json()))
        def props(value):
            if isinstance(value, dict):
                yield value.get('props', {})
                for child in value.values():
                    yield from props(child)
            elif isinstance(value, list):
                for child in value:
                    yield from props(child)
        delete = next(item for item in props(tree) if item.get('id') == {'type': 'delete-chat', 'id': self.chat_id})
        self.assertTrue(delete['disabled'])
        self.assertIn('Eliminar chat', delete['aria-label'])
        self.engine.state['busy'] = False
        self.store.delete_chat(self.chat_id)
        tree = json.loads(json.dumps(main.sidebar(self.store.navigation(), self.store.data['selected']), default=lambda component: component.to_plotly_json()))
        self.assertFalse(any(item.get('id') == {'type': 'chat', 'id': self.chat_id} for item in props(tree)))
        self.assertTrue(any(item.get('id') == {'type': 'restore-chat', 'id': self.chat_id} for item in props(tree)))

    def test_design_switch_changes_only_presentation(self):
        before = self.store.engine(self.chat_id).snapshot()
        self.assertEqual(main.switch_design(1, 'classic'), 'triangular')
        self.assertEqual(main.switch_design(2, 'triangular'), 'classic')
        self.assertEqual(main.apply_design('triangular'), ('triangular', 'Diseño: Triangular ⇄', 'true'))
        self.assertEqual(main.apply_design({'invalid': 'local preference'}), ('classic', 'Diseño: Clásico ⇄', 'false'))
        key = next(key for key, callback in main.app.callback_map.items()
                   if any(item['id'] == 'ui-design' for item in callback['inputs']))
        with patch.object(self.store, 'perform') as perform:
            response = self.post(key, {'ui-design': 'triangular'}, 'ui-design.data')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.json['response']['magi']['variant'], 'triangular')
        perform.assert_not_called()
        self.assertEqual(self.store.engine(self.chat_id).snapshot(), before)

    def test_refresh_updates_japanese_headers_and_translated_status(self):
        values = main.refresh(0, {'chat_id': self.chat_id}, None, None)
        self.assertEqual(values[28:34], ('指示', '待機中', 'En espera de instrucciones', 'En espera de instrucciones', '待機', 'En espera'))

    def test_sending_ignores_unsaved_settings_and_preserves_a_custom_name(self):
        self.store.perform(self.chat_id, self.engine.snapshot()['id'], 'save', '', self.config,
                           title='Mi portafolio', project_name='Sitios personales')
        calls = []
        def runner(node, *args, **kwargs):
            calls.append(node)
            return 'Respuesta breve'
        self.engine.runner = runner
        values = self.action_values()
        values.update(start=1, query='¿Qué hace este proyecto?', **{'request-mode': 'ask',
                      'consensus': 'invalid', 'provider-melchior': 'invalid',
                      'automation-mode': 'autonomous', 'chat-title': 'Nombre sin guardar'})
        with patch('ai.command_for', return_value=(['unused'], {})):
            response = self.post(self.action_key(), values, 'start.n_clicks')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertIn('query', response.json['response'])
        deadline = time.monotonic() + 3
        while self.engine.snapshot()['busy'] and time.monotonic() < deadline:
            Event().wait(.01)
        self.assertFalse(self.engine.snapshot()['busy'])
        self.assertEqual(calls, [self.config['nodes'][self.config['executor']]])
        self.assertEqual(self.store.chat(self.chat_id)['config'], self.config)
        self.assertEqual(self.store.chat(self.chat_id)['title'], 'Mi portafolio')
        refreshed = main.refresh(0, {'chat_id': self.chat_id}, None, None)
        self.assertEqual(refreshed[-2:], ('council', '1 consulta'))

    def test_save_renames_chat_and_shared_project_without_changing_context(self):
        other = self.store.new_chat(self.store.chat(self.chat_id)['project_id'])
        self.store.save_draft(self.chat_id, 'Borrador conservado')
        before = self.engine.snapshot()
        values = self.action_values()
        values.update(save=1, **{'chat-title': 'Portafolio', 'workspace-name': 'Mis páginas'})
        response = self.post(self.action_key(), values, 'save.n_clicks')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(self.store.chat(self.chat_id)['title'], 'Portafolio')
        project = self.store.data['projects'][self.store.chat(other)['project_id']]
        self.assertEqual(project['name'], 'Mis páginas')
        self.assertEqual(project['path'], self.config['workspace'])
        self.assertEqual(self.store.chat(self.chat_id)['draft'], 'Borrador conservado')
        self.assertEqual(self.engine.snapshot(), before)
        self.assertEqual(response.json['response']['saved-form']['data']['title'], 'Portafolio')
        self.assertIn('Portafolio', main.load_chat({'chat_id': self.chat_id}))

    def test_invalid_names_do_not_partially_save_settings_or_project_names(self):
        for title in ('', 'x' * 81, ['bad'], 'Primera\nSegunda'):
            with self.subTest(title=title):
                before = deepcopy(self.store.data)
                values = self.action_values()
                values.update(save=1, **{'chat-title': title, 'workspace-name': 'No aplicar'})
                response = self.post(self.action_key(), values, 'save.n_clicks')
                self.assertIn('nombre', response.json['response']['configuration-notice']['children'])
                self.assertEqual(self.store.data, before)
                self.assertNotIn('saved-form', response.json['response'])

    def test_sidebar_can_fold_and_restore_without_touching_chats(self):
        before = self.engine.snapshot()
        self.assertTrue(main.toggle_sidebar(1, False))
        self.assertFalse(main.toggle_sidebar(2, True))
        self.assertEqual(main.apply_sidebar(True), ('desktop-shell desktop-shell--compact', '›', 'false', 'Mostrar barra de proyectos'))
        self.assertEqual(main.apply_sidebar(False), ('desktop-shell', '‹', 'true', 'Plegar barra de proyectos'))
        self.assertEqual(main.apply_sidebar('invalid'), main.apply_sidebar(False))
        key = next(key for key, callback in main.app.callback_map.items()
                   if any(item['id'] == 'sidebar-collapsed' for item in callback['inputs']))
        response = self.post(key, {'sidebar-collapsed': True}, 'sidebar-collapsed.data')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.json['response']['toggle-sidebar']['aria-expanded'], 'false')
        self.assertEqual(self.engine.snapshot(), before)

    def test_model_picker_preserves_saved_selection_and_supports_manual_ids(self):
        catalog = {'opencode': {'models': [{'value': 'provider/model-a', 'label': 'provider/model-a'}], 'notice': '1 modelo'}}
        options, notice = main.model_options('opencode', catalog, 'provider/custom', 'provider/saved')
        self.assertEqual([option['value'] for option in options], ['', 'provider/model-a', 'provider/saved', 'provider/custom'])
        self.assertIn('Se conserva tu selección', notice)
        for candidate in ('--flag', 'invalid model', 'missing-provider', 'provider/'):
            options, _ = main.model_options('opencode', catalog, candidate, 'provider/model-a')
            self.assertEqual(len(options), 2)
        options, _ = main.model_options('codex', catalog, '', 'model-b')
        self.assertEqual(options[-1]['value'], 'model-b')

    def test_catalog_callback_only_lists_metadata_and_never_performs_a_task(self):
        key = next(key for key, callback in main.app.callback_map.items()
                   if any(item['id'] == 'refresh-models' for item in callback['inputs']))
        catalog = {'installed': True, 'models': [{'value': 'model-a', 'label': 'Modelo A'}], 'notice': '1 modelo'}
        before = self.engine.snapshot()
        with patch('ai.model_catalog', return_value=catalog) as query, patch.object(self.store, 'perform') as perform:
            response = self.post(key, {'open-configuration': 1, 'refresh-models': 1, 'workspace': self.config['workspace']},
                                 'refresh-models.n_clicks')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(query.call_count, 3)
        self.assertTrue(all(call.kwargs['refresh'] for call in query.call_args_list))
        self.assertEqual(response.json['response']['model-catalog']['data']['codex'], catalog)
        self.assertEqual(response.json['response']['model-catalog']['data']['claude'], catalog)
        perform.assert_not_called()
        self.assertEqual(self.engine.snapshot(), before)
        with patch('ai.model_catalog') as query:
            response = self.post(key, {'open-configuration': 0, 'refresh-models': 0, 'workspace': self.config['workspace']},
                                 'workspace.value')
        self.assertEqual(response.status_code, 204)
        query.assert_not_called()

    def test_send_starts_current_chat_and_clears_composer_without_losing_history(self):
        calls = []
        def runner(node, prompt, workspace, cancel, writable=False):
            calls.append(prompt)
            if 'DECISION DE RUTA' in prompt:
                return '{"route":"council","reply":"Trabajo complejo","edit_requested":true,"plan":"PLAN DEL CHAT"}'
            return '{"vote":"yes","reason":"OK"}' if 'Devuelve solo JSON' in prompt else 'PLAN DEL CHAT'
        self.engine.runner = runner
        values = self.action_values()
        values.update(start=1, query='Mi objetivo independiente')
        with patch('ai.command_for', return_value=(['unused'], {})):
            response = self.post(self.action_key(), values, 'start.n_clicks')
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        self.assertEqual(response.json['response']['query']['value'], '')
        deadline = time.monotonic() + 4
        while self.engine.snapshot()['busy'] and time.monotonic() < deadline:
            Event().wait(.01)
        self.assertFalse(self.engine.snapshot()['busy'])
        self.assertEqual(self.engine.snapshot()['task'], values['query'])
        self.assertEqual(self.store.chat(self.chat_id)['draft'], '')
        self.assertEqual(self.store.chat(self.chat_id)['title'], values['query'])
        self.assertEqual(len(calls), 8)

    def test_ask_selector_answers_without_starting_work_and_renders_the_reply(self):
        calls = []
        def runner(node, prompt, *args, **kwargs):
            calls.append(prompt)
            return 'Un harness coordina modelos y herramientas.'
        self.engine.runner = runner
        values = self.action_values()
        values.update(start=1, query='¿Qué es un harness?', **{'request-mode': 'ask'})
        with patch('ai.command_for', return_value=(['unused'], {})):
            response = self.post(self.action_key(), values, 'start.n_clicks')
        self.assertEqual(response.status_code, 200)
        deadline = time.monotonic() + 4
        while self.engine.snapshot()['busy'] and time.monotonic() < deadline:
            Event().wait(.01)
        state = self.engine.snapshot()
        self.assertEqual(len(calls), 1)
        self.assertEqual(state['plan'], '')
        self.assertEqual(state['task_id'], '')
        rendered = json.dumps(main.conversation(state), default=lambda component: component.to_plotly_json(), ensure_ascii=False)
        self.assertIn('Un harness coordina modelos', rendered)
        self.assertNotIn('PASO 1', rendered)


if __name__ == '__main__':
    unittest.main()
