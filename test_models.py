import json
import subprocess
import unittest
from unittest.mock import patch

import ai


class ModelCatalogTests(unittest.TestCase):
    def setUp(self):
        ai._model_cache.clear()

    def test_claude_aliases_do_not_infer_or_claim_account_access(self):
        with patch('ai.find_cli', return_value=['claude.exe']), patch('ai.query_models') as query:
            result = ai.model_catalog('claude', 'workspace')
        self.assertTrue(result['installed'])
        self.assertEqual([item['value'] for item in result['models']], ['sonnet', 'haiku', 'opus'])
        self.assertIn('no catálogo de acceso', result['notice'])
        query.assert_not_called()

    def test_claude_permissions_are_per_call_and_cannot_spawn_agents_or_shells(self):
        with patch('ai.find_cli', side_effect=lambda provider: ['claude.exe']):
            for writable in (False, True):
                command, env = ai.command_for({'provider': 'claude', 'model': 'haiku'}, writable)
                self.assertIn('--restricted', command)
                self.assertIn('--safe-mode', command)
                self.assertIn('--strict-mcp-config', command)
                self.assertIn('--no-session-persistence', command)
                self.assertEqual(command[command.index('--permission-mode') + 1], 'dontAsk')
                self.assertEqual(command[command.index('--permission-prompts') + 1], 'none')
                tools = command[command.index('--tools') + 1].split(',')
                self.assertEqual(tools, ['Read', 'Glob', 'Grep'] + (['Edit', 'Write'] if writable else []))
                settings = json.loads(command[command.index('--settings') + 1])
                self.assertTrue(settings['disableAllHooks'])
                self.assertIn('Read(**/.env)', settings['permissions']['deny'])
                self.assertIn('Edit(**/.magi/**)', settings['permissions']['deny'])
                self.assertEqual(command[-2:], ['--model', 'haiku'])

    def test_claude_result_and_progress_never_expose_thinking_or_accept_errors(self):
        thinking = {'type': 'assistant', 'message': {'content': [{'type': 'thinking', 'thinking': 'PRIVATE'}]}}
        self.assertIsNone(ai.live_event('claude', thinking))
        result = {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'Respuesta', 'permission_denials': []}
        self.assertEqual(ai.parse_output('claude', json.dumps(thinking)+'\n'+json.dumps(result)), 'Respuesta')
        self.assertEqual(ai.live_event('claude', result)['text'], 'Respuesta')
        for change in ({'is_error': True}, {'subtype': 'error_max_turns'}, {'permission_denials': [{'tool_name': 'Write'}]}):
            with self.assertRaises(RuntimeError):
                ai.parse_output('claude', json.dumps({**result, **change}))
        with self.assertRaises(RuntimeError):
            ai.parse_output('claude', json.dumps(thinking))

    def test_claude_permission_failure_preserves_tool_names_and_final_report(self):
        result = {'type': 'result', 'subtype': 'success', 'result': 'No pude clonar; pude crear el informe.',
                  'permission_denials': [{'tool_name': 'Bash', 'tool_input': {'command': 'DO_NOT_LOG_RAW_INPUT'}},
                                        {'tool_name': 'WebFetch'}, {'tool_name': 'Bash'}]}
        with self.assertRaises(RuntimeError) as failure:
            ai.parse_output('claude', json.dumps(result))
        detail = str(failure.exception)
        self.assertIn('Bash, WebFetch', detail)
        self.assertIn(result['result'], detail)
        self.assertNotIn('DO_NOT_LOG_RAW_INPUT', detail)
        self.assertEqual(ai.error_info(failure.exception)['kind'], 'permissions')

    def test_codex_catalog_excludes_hidden_invalid_and_duplicate_entries(self):
        payload = {'models': [
            {'slug': 'model-a', 'display_name': 'Modelo A', 'visibility': 'list'},
            {'slug': 'hidden', 'visibility': 'hide'},
            {'slug': '--flag', 'visibility': 'list'},
            {'slug': 'model-a', 'display_name': 'Modelo A', 'visibility': 'list'},
            None,
        ]}
        self.assertEqual(ai.parse_models('codex', json.dumps(payload)), [{'value': 'model-a', 'label': 'Modelo A'}])

    def test_opencode_models_keep_full_provider_ids_and_ignore_logs(self):
        output = 'Starting server…\nprovider/model\nprovider/nested/model:free\nprovider/model\nmodel-without-provider\n/invalid\nprovider/\n'
        self.assertEqual([model['value'] for model in ai.parse_models('opencode', output)],
                         ['provider/model', 'provider/nested/model:free'])
        with self.assertRaises(ValueError):
            ai.parse_models('opencode', 'No models available')

    def test_metadata_is_cached_by_cli_and_workspace_and_refresh_preserves_last_list(self):
        with patch('ai.find_cli', return_value=['codex.exe']), patch('ai.query_models') as query:
            query.return_value = json.dumps({'models': [{'slug': 'model-a', 'visibility': 'list'}]})
            first = ai.model_catalog('codex', 'workspace-a')
            self.assertEqual(ai.model_catalog('codex', 'workspace-a'), first)
            query.assert_called_once_with(['codex.exe', 'debug', 'models'], 'workspace-a')
            ai.model_catalog('codex', 'workspace-b')
            self.assertEqual(query.call_count, 2)
            query.side_effect = subprocess.TimeoutExpired('catalog', 20)
            stale = ai.model_catalog('codex', 'workspace-a', refresh=True)
            self.assertEqual(stale['models'], first['models'])
            self.assertIn('Lista anterior conservada', stale['notice'])
            self.assertIn('tardó demasiado', stale['notice'])

    def test_missing_cli_and_invalid_catalog_are_readable_without_fallback_models(self):
        with patch('ai.find_cli', side_effect=ValueError('No se encontró Codex.')), patch('ai.query_models') as query:
            result = ai.model_catalog('codex', 'workspace')
        query.assert_not_called()
        self.assertFalse(result['installed'])
        self.assertEqual(result['models'], [])
        with patch('ai.find_cli', return_value=['opencode.exe']), patch('ai.query_models', return_value='unexpected output'):
            result = ai.model_catalog('opencode', 'workspace')
        self.assertTrue(result['installed'])
        self.assertEqual(result['models'], [])
        self.assertIn('sesión y versión', result['notice'])

    def test_query_uses_no_shell_no_prompt_and_cleans_up_after_timeout(self):
        with patch('ai.subprocess.Popen') as popen, patch('ai.stop_process') as stop:
            process = popen.return_value
            process.wait.side_effect = subprocess.TimeoutExpired('models', 20)
            with self.assertRaises(subprocess.TimeoutExpired):
                ai.query_models(['opencode.exe', 'models', '--standalone'], 'workspace')
            self.assertEqual(popen.call_args.args[0], ['opencode.exe', 'models', '--standalone'])
            self.assertNotIn('shell', popen.call_args.kwargs)
            self.assertEqual(popen.call_args.kwargs['stdin'], subprocess.DEVNULL)
            stop.assert_called_once_with(process)


if __name__ == '__main__':
    unittest.main()
