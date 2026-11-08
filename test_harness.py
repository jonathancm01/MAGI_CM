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
from harness import DEFAULT_CONFIG, Harness, NAMES, consensus, load_config, parse_vote, save_config, validate_config


class HarnessTests(unittest.TestCase):
    def test_claude_planning_knows_writing_does_not_enable_git_or_network(self):
        engine = Harness()
        engine.config = deepcopy(DEFAULT_CONFIG)
        engine.config['nodes']['melchior']['provider'] = 'claude'
        for writable in (False, True):
            prompt = engine.prompt('melchior', 'Analiza el repositorio', writable=writable)
            self.assertIn('No dispone de terminal, git clone', prompt)
            self.assertIn('antes de aprobar el plan', prompt)
            self.assertIn('TURNO DE ESCRITURA' if writable else 'CONSULTA DE SOLO LECTURA', prompt)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = deepcopy(DEFAULT_CONFIG)
        self.config["workspace"] = self.directory.name
        self.commands = patch("ai.command_for", return_value=(["unused"], {}))
        self.commands.start()
        self.addCleanup(self.commands.stop)

    def wait(self, harness):
        deadline = time.monotonic() + 3
        while harness.snapshot()["busy"] and time.monotonic() < deadline:
            Event().wait(0.01)
        self.assertFalse(harness.snapshot()["busy"], "Worker did not finish")
        return harness.snapshot()

    def test_deliberation_then_explicit_execution_and_review(self):
        calls = []

        def runner(node, prompt, workspace, cancel, writable=False):
            calls.append((prompt, writable))
            if "Devuelve solo JSON" in prompt:
                return '{"vote":"yes","reason":"Verificado con evidencia."}'
            return "PLAN INMUTABLE" if not writable else "Implementación y pruebas realizadas."

        harness = Harness(runner)
        harness.start("Implementar una función.", self.config)
        state = self.wait(harness)
        self.assertEqual(state["phase"], "ready")
        self.assertEqual(len(calls), 7)
        self.assertFalse(any(writable for _, writable in calls))
        self.assertTrue(all('CONSULTA DE SOLO LECTURA' in prompt for prompt, _ in calls))
        for prompt, _ in calls[4:]:
            self.assertIn("PLAN EXACTO A VOTAR:\nPLAN INMUTABLE", prompt)
            self.assertIn(self.directory.name, prompt)
        harness.execute(state["id"], state["task"], self.config)
        state = self.wait(harness)
        self.assertEqual(state["phase"], "done")
        self.assertEqual(sum(writable for _, writable in calls), 3)
        self.assertEqual(len(calls), 15)
        for prompt, writable in calls:
            self.assertIn('TURNO DE ESCRITURA' if writable else 'CONSULTA DE SOLO LECTURA', prompt)
        with self.assertRaises(ValueError):
            harness.execute(state["id"], state["task"], self.config)

    def test_unwritable_folder_blocks_execution_before_starting_models(self):
        harness = Harness(lambda node, prompt, *args: '{"vote":"yes","reason":"ok"}' if 'Devuelve solo JSON' in prompt else 'Plan')
        harness.start('Crear archivos', self.config)
        state = self.wait(harness)
        with patch('harness.ensure_writable', side_effect=ValueError('No se puede escribir')) as check:
            with self.assertRaisesRegex(ValueError, 'No se puede escribir'):
                harness.execute(state['id'], state['task'], self.config)
        check.assert_called_once_with(self.config['workspace'])
        self.assertFalse(harness.snapshot()['busy'])
        self.assertEqual(harness.snapshot()['phase'], 'ready')
        self.assertEqual(harness.snapshot()['execution_report'], '')

    def test_failure_blocks_majority_and_skips_vote_round(self):
        self.config["consensus"] = "majority"
        self.config["nodes"]["casper"]["model"] = "unavailable"
        calls = []

        def runner(node, *args):
            calls.append(node)
            if node["model"] == "unavailable":
                raise RuntimeError("Sesión no disponible")
            return "Plan"

        harness = Harness(runner)
        harness.start("Tarea", self.config)
        state = self.wait(harness)
        self.assertEqual(state["phase"], "error")
        self.assertEqual(state["answers"]["casper"]["status"], "error")
        self.assertEqual(len(calls), 3)

    def test_malformed_vote_never_approves(self):
        harness = Harness(lambda node, prompt, *args: "yes" if "Devuelve solo JSON" in prompt else "Plan")
        harness.start("Tarea", self.config)
        self.assertEqual(self.wait(harness)["phase"], "error")

    def test_stale_task_config_and_id_cannot_execute(self):
        harness = Harness(lambda node, prompt, *args: '{"vote":"yes","reason":"ok"}' if "Devuelve solo JSON" in prompt else "Plan")
        harness.start("Tarea", self.config)
        state = self.wait(harness)
        changed = deepcopy(self.config)
        changed["executor"] = "casper"
        for run_id, task, config in (("stale", "Tarea", self.config), (state["id"], "Otra tarea", self.config),
                                     (state["id"], "Tarea", changed)):
            with self.assertRaises(ValueError):
                harness.execute(run_id, task, config)

    def test_cancel_and_single_active_operation(self):
        started = Event()

        def runner(node, prompt, workspace, cancel):
            started.set()
            cancel.wait(2)
            raise ai.Cancelled()

        harness = Harness(runner)
        harness.start("Tarea", self.config)
        self.assertTrue(started.wait(1))
        with self.assertRaises(ValueError):
            harness.start("Segunda tarea", self.config)
        with self.assertRaises(ValueError):
            harness.new_task()
        harness.cancel()
        state = self.wait(harness)
        self.assertEqual(state["phase"], "cancelled")
        self.assertTrue(all(answer["id"] == state["id"] for answer in state["answers"].values()))

    def test_settings_round_trip_and_invalid_save_preserves_file(self):
        path = Path(self.directory.name) / "settings.json"
        save_config(self.config, path)
        original = path.read_bytes()
        self.assertEqual(load_config(path), validate_config(self.config))
        self.config["nodes"]["casper"]["instructions"] = ""
        with self.assertRaises(ValueError):
            save_config(self.config, path)
        self.assertEqual(path.read_bytes(), original)

    def test_invalid_opencode_reference_cannot_replace_saved_settings(self):
        path = Path(self.directory.name) / 'settings.json'
        save_config(self.config, path)
        previous = path.read_bytes()
        self.config['nodes']['casper'].update(provider='opencode', model='gpt-6.1-sol')
        with self.assertRaisesRegex(ValueError, 'CASPER: OpenCode requiere proveedor/modelo'):
            save_config(self.config, path)
        self.assertEqual(path.read_bytes(), previous)

    def test_consensus_and_strict_votes(self):
        self.assertEqual(consensus(["yes", "yes", "yes"], "unanimous"), "yes")
        self.assertEqual(consensus(["yes", "yes", "no"], "unanimous"), "no")
        self.assertEqual(consensus(["yes", "yes", "conditional"], "unanimous"), "conditional")
        self.assertEqual(consensus(["yes", "yes", "no"], "majority"), "yes")
        self.assertEqual(consensus(["yes", "yes", "error"], "majority"), "error")
        self.assertEqual(consensus(["yes", "yes"], "majority"), "error")
        self.assertEqual(parse_vote('```json\n{"vote":"no","reason":"Falta una prueba"}\n```')["status"], "no")
        for text in ('yes', '{"vote":"yes","reason":""}', '{"vote":"YES","reason":"ok"}', '[]'):
            with self.assertRaises(ValueError):
                parse_vote(text)

    def test_model_cannot_be_a_flag_after_trimming(self):
        self.config["nodes"]["melchior"]["model"] = "   --unsafe-option"
        with self.assertRaises(ValueError):
            validate_config(self.config)

    @staticmethod
    def successful_runner(node, prompt, workspace, cancel, writable=False):
        if "Devuelve solo JSON" in prompt:
            return '{"vote":"yes","reason":"Evidencia comprobada."}'
        return "INFORME DE EJECUCIÓN" if writable else "PLAN APROBADO"

    def completed(self, harness):
        harness.start("Objetivo original: crear la página.", self.config)
        state = self.wait(harness)
        harness.execute(state["id"], state["request"], self.config)
        return self.wait(harness)

    def test_continuation_keeps_goal_report_objections_and_requires_new_execution(self):
        calls = []

        def runner(*args, **kwargs):
            calls.append((args[1], kwargs.get("writable", False)))
            return self.successful_runner(*args, **kwargs)

        harness = Harness(runner)
        previous = self.completed(harness)
        harness.state["answers"]["melchior"].update(status="conditional", conditions="Falta comprobar teclado.")
        harness.continue_task(previous["id"], "Corrige solamente el enlace de retorno.", self.config)
        state = self.wait(harness)
        self.assertEqual(state["task_id"], previous["task_id"])
        self.assertEqual(state["task"], previous["task"])
        self.assertNotEqual(state["id"], previous["id"])
        self.assertEqual(state["request"], "Corrige solamente el enlace de retorno.")
        self.assertEqual(state["iteration"], 2)
        self.assertEqual(state["phase"], "ready")
        self.assertEqual(len(calls), 22)
        self.assertFalse(any(writable for _, writable in calls[15:]))
        for prompt, _ in calls[15:]:
            for context in (previous["task"], "PLAN APROBADO", "INFORME DE EJECUCIÓN", "Falta comprobar teclado."):
                self.assertIn(context, prompt)
        self.assertEqual(len(state["answers"]["melchior"]["history"]), 8)
        with self.assertRaises(ValueError):
            harness.execute(previous["id"], state["request"], self.config)
        harness.execute(state["id"], state["request"], self.config)
        self.assertEqual(self.wait(harness)["phase"], "done")

    def test_re_review_makes_only_three_read_only_calls_and_keeps_executed_plan(self):
        calls = []

        def runner(*args, **kwargs):
            calls.append((args[1], kwargs.get("writable", False)))
            return self.successful_runner(*args, **kwargs)

        harness = Harness(runner)
        previous = self.completed(harness)
        calls.clear()
        harness.review_again(previous["id"], self.config)
        state = self.wait(harness)
        self.assertEqual(state["phase"], "done")
        self.assertEqual(state["iteration"], 2)
        self.assertEqual(len(calls), 3)
        self.assertFalse(any(writable for _, writable in calls))
        self.assertTrue(all("Plan ejecutado:\nPLAN APROBADO" in prompt for prompt, _ in calls))
        self.assertEqual(sum(entry["phase"] == "Ejecución" for entry in state["answers"]["melchior"]["history"]), 1)
        with self.assertRaises(ValueError):
            harness.review_again(previous["id"], self.config)

    def test_continuation_and_review_refuse_a_different_workspace(self):
        harness = Harness(self.successful_runner)
        state = self.completed(harness)
        changed = deepcopy(self.config)
        changed["workspace"] = str(Path(self.directory.name) / "other")
        Path(changed["workspace"]).mkdir()
        for action in (lambda: harness.continue_task(state["id"], "Continúa", changed),
                       lambda: harness.review_again(state["id"], changed)):
            with self.assertRaisesRegex(ValueError, "carpeta"):
                action()
        self.assertEqual(harness.snapshot()["id"], state["id"])

    def test_archive_restore_and_restart_never_reuse_execution_permission(self):
        storage = Path(self.directory.name) / "history"
        harness = Harness(self.successful_runner, storage)
        harness.start("Primera tarea", self.config)
        first = self.wait(harness)
        harness.start("Segunda tarea", self.config)
        second = self.wait(harness)
        self.assertEqual(len(harness.history()), 2)
        calls = []
        recovered = Harness(lambda *args, **kwargs: calls.append(args), storage)
        state = recovered.snapshot()
        self.assertEqual(state["task_id"], second["task_id"])
        self.assertEqual(state["phase"], "restored")
        self.assertFalse(state["busy"])
        self.assertFalse(calls)
        self.assertTrue(all(answer["id"] == state["id"] for answer in state["answers"].values()))
        for run_id in (second["id"], state["id"]):
            with self.assertRaises(ValueError):
                recovered.execute(run_id, state["request"], self.config)
        recovered.restore(first["task_id"])
        self.assertEqual(recovered.snapshot()["task"], "Primera tarea")
        self.assertEqual(len(recovered.history()), 2)
        self.assertFalse(calls)

    def test_interrupted_execution_is_restored_without_automatic_inference(self):
        storage = Path(self.directory.name) / "history"
        harness = Harness(self.successful_runner, storage)
        state = self.completed(harness)
        path = storage / f"{state['task_id']}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["state"].update(busy=True, phase="execution")
        path.write_text(json.dumps(record), encoding="utf-8")
        recovered = Harness(lambda *args: self.fail("Unexpected inference"), storage)
        self.assertEqual(recovered.snapshot()["phase"], "interrupted")
        self.assertIn("cambios parciales", recovered.snapshot()["message"])
        self.assertFalse(recovered.snapshot()["busy"])

    def test_completed_task_can_be_reviewed_after_restart(self):
        storage = Path(self.directory.name) / "history"
        previous = Harness(self.successful_runner, storage)
        original = self.completed(previous)
        calls = []

        def runner(*args, **kwargs):
            calls.append(kwargs.get("writable", False))
            return self.successful_runner(*args, **kwargs)

        recovered = Harness(runner, storage)
        recovered.review_again(recovered.snapshot()["id"], self.config)
        state = self.wait(recovered)
        self.assertEqual(calls, [False] * 3)
        self.assertEqual(state["task_id"], original["task_id"])
        self.assertEqual(state["phase"], "done")

    def test_corrupt_history_and_traversal_do_not_replace_current_task(self):
        storage = Path(self.directory.name) / "history"
        harness = Harness(self.successful_runner, storage)
        state = self.completed(harness)
        corrupt_id = "a" * 32
        corrupt = storage / f"{corrupt_id}.json"
        corrupt.write_text("[]", encoding="utf-8")
        for task_id in (corrupt_id, "../outside", None):
            with self.assertRaises(ValueError):
                harness.restore(task_id)
        self.assertEqual(harness.snapshot()["id"], state["id"])
        self.assertEqual(corrupt.read_text(encoding="utf-8"), "[]")

    def test_failed_persistence_prevents_starting_inference(self):
        calls = []
        harness = Harness(lambda *args: calls.append(args), Path(self.directory.name) / "history")
        with patch("harness.write_json", side_effect=OSError("Disk full")):
            with self.assertRaisesRegex(RuntimeError, "guardar el historial"):
                harness.start("Tarea", self.config)
        self.assertFalse(calls)
        self.assertFalse(harness.snapshot()["busy"])

    def test_re_review_partial_failure_does_not_approve_even_with_majority(self):
        harness = Harness(self.successful_runner)
        state = self.completed(harness)
        changed = deepcopy(self.config)
        changed["consensus"] = "majority"
        changed["nodes"]["casper"]["model"] = "unavailable"

        def runner(node, *args):
            if node["model"] == "unavailable":
                raise RuntimeError("Modelo no disponible")
            return '{"vote":"yes","reason":"ok"}'

        harness.runner = runner
        harness.review_again(state["id"], changed)
        self.assertEqual(self.wait(harness)["phase"], "error")

    def test_memory_distinguishes_a_new_proposal_from_the_last_executed_plan(self):
        harness = Harness(self.successful_runner)
        self.completed(harness)
        harness.state['plan'] = 'PROPUESTA SIN EJECUTAR'
        harness.checkpoint()
        memory = harness.memory()
        self.assertIn('"plan_propuesto": "PROPUESTA SIN EJECUTAR"', memory)
        self.assertIn('"plan_ejecutado": "PLAN APROBADO"', memory)
        self.assertIn('"informe_ejecución":', memory)
        self.assertIn('INFORME DE EJECUCIÓN', memory)
        self.assertIn('BALTHASAR', memory)

    def test_prepare_new_task_archives_without_inference_and_remains_blank_after_restart(self):
        storage = Path(self.directory.name) / 'history'
        harness = Harness(self.successful_runner, storage)
        previous = self.completed(harness)
        harness.runner = lambda *args, **kwargs: self.fail('Preparing a draft must not infer')
        harness.new_task()
        state = harness.snapshot()
        self.assertEqual(state['phase'], 'idle')
        self.assertEqual(state['task'], '')
        self.assertEqual(state['request'], '')
        self.assertTrue(all(not answer['history'] and answer['id'] == state['id'] for answer in state['answers'].values()))
        recovered = Harness(harness.runner, storage)
        self.assertEqual(recovered.snapshot()['phase'], 'idle')
        self.assertEqual(recovered.storage_error, '')
        self.assertEqual(len(recovered.history()), 1)
        recovered.restore(previous['task_id'])
        self.assertEqual(recovered.snapshot()['task'], previous['task'])
        self.assertEqual(recovered.snapshot()['execution_report'], previous['execution_report'])

    def test_preparing_draft_with_storage_failure_preserves_previous_task(self):
        storage = Path(self.directory.name) / 'history'
        harness = Harness(self.successful_runner, storage)
        previous = self.completed(harness)
        pointer = (storage / 'current.json').read_bytes()
        with patch('harness.write_json', side_effect=OSError('Disk full')):
            with self.assertRaises(RuntimeError):
                harness.new_task()
        self.assertEqual(harness.snapshot()['task_id'], previous['task_id'])
        self.assertEqual(harness.snapshot()['task'], previous['task'])
        self.assertEqual((storage / 'current.json').read_bytes(), pointer)


class AdapterTests(unittest.TestCase):
    def test_structured_error_survives_nonzero_exit_with_empty_stderr(self):
        output = json.dumps({"type": "error", "error": {
            "type": "unknown", "message": "Invalid model reference: deepseek-v4.1-flash-free"}})
        with self.assertRaisesRegex(RuntimeError, "OpenCode: Invalid model reference"):
            ai.parse_output("opencode", output, returncode=1)

    def test_model_failure_takes_priority_over_mcp_diagnostics(self):
        output = json.dumps({"type": "turn.failed", "error": {
            "message": "The 'gpt-6.1-sol' model is not supported when using Codex with a ChatGPT account."}})
        with self.assertRaisesRegex(RuntimeError, "gpt-6.1-sol.*not supported") as failure:
            ai.parse_output("codex", output, returncode=1, diagnostics="MCP AuthRequired: tldraw")
        self.assertNotIn("tldraw", str(failure.exception))

    def test_codex_unwraps_api_error_encoded_in_event_message(self):
        message = "The 'gpt-6.1-sol' model is not supported when using Codex with a ChatGPT account."
        output = json.dumps({"type": "error", "message": json.dumps({
            "type": "error", "status": 400, "error": {"type": "invalid_request_error", "message": message}})})
        with self.assertRaises(RuntimeError) as failure:
            ai.parse_output("codex", output, returncode=1, diagnostics="MCP AuthRequired")
        self.assertEqual(str(failure.exception), "Codex: " + message)

    def test_non_json_failure_uses_stdout_and_never_has_empty_details(self):
        with self.assertRaisesRegex(RuntimeError, "Unknown argument"):
            ai.parse_output("opencode", "Unknown argument", returncode=1)
        with self.assertRaisesRegex(RuntimeError, "no devolvió detalles"):
            ai.parse_output("opencode", "", returncode=1)
        with self.assertRaisesRegex(RuntimeError, "not authenticated"):
            ai.parse_output("opencode", "", returncode=1, diagnostics="not authenticated")

    def test_opencode_requires_a_qualified_model_without_substitution(self):
        with patch("ai.find_cli", side_effect=lambda provider: ["native-cli"]):
            for model in ("deepseek-v4.1-flash-free", "/model", "provider/"):
                with self.assertRaisesRegex(ValueError, "proveedor/modelo"):
                    ai.command_for({"provider": "opencode", "model": model})
            model = "opencode/deepseek-v4.1-flash-free"
            command, _ = ai.command_for({"provider": "opencode", "model": model})
            self.assertEqual(command[command.index("--model") + 1], model)

    def test_final_message_and_completion_are_required(self):
        events = [
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Revisando…"}},
            {"type": "item.completed", "item": {"type": "agent_message", "text": "Respuesta final"}},
            {"type": "turn.completed"},
        ]
        output = "\n".join(map(json.dumps, events))
        self.assertEqual(ai.parse_output("codex", output), "Respuesta final")
        with self.assertRaises(RuntimeError):
            ai.parse_output("codex", json.dumps(events[1]))
        with self.assertRaises(RuntimeError):
            ai.parse_output("codex", output + '\n{"type":"turn.failed","error":{"message":"No autorizado"}}')
        self.assertEqual(ai.parse_output("opencode", '{"type":"text","part":{"text":"ok"}}\n{"type":"step_finish"}'), "ok")
        self.assertEqual(ai.parse_output("opencode", '{"type":"text","part":{"text":"v2","time":{"end":123}}}'), "v2")

    def test_commands_keep_permissions_and_model(self):
        with patch("ai.find_cli", side_effect=lambda provider: ["native-cli"]):
            command, _ = ai.command_for({"provider": "codex", "model": "chosen-model"})
            self.assertIn("read-only", command)
            self.assertEqual(command[command.index("--model") + 1], "chosen-model")
            command, _ = ai.command_for({"provider": "codex", "model": "chosen-model"}, writable=True)
            self.assertIn('workspace-write', command)
            for writable in (False, True):
                command, environment = ai.command_for({"provider": "opencode", "model": ""}, writable=writable)
                self.assertIn("--standalone", command)
                self.assertEqual(command[command.index('--agent') + 1], 'build' if writable else 'plan')
                config = json.loads(environment['OPENCODE_CONFIG_CONTENT'])
                permissions = {rule['action']: rule['effect'] for rule in config['permissions']}
                self.assertEqual(permissions.get('edit', permissions['*']), 'allow' if writable else 'deny')
                self.assertEqual(permissions['execute'], 'allow')
                self.assertEqual(permissions['*'], 'deny')
                self.assertNotIn('shell', permissions)
                self.assertNotIn('external_directory', permissions)
                self.assertEqual(config['agents']['build']['permissions'], config['permissions'])
                for resource in ('edit:../*', 'read:*.env', 'edit:*.key', 'edit:*/.git/*'):
                    self.assertIn({'action': 'tool.use', 'resource': resource, 'effect': 'deny'}, config['policies'])
                self.assertNotIn('OPENCODE_PERMISSION', environment)
            with self.assertRaises(ValueError):
                ai.command_for({"provider": "unsupported", "model": ""})

    def test_real_subprocess_transports_prompt_without_shell(self):
        program = ("import sys,json; text=sys.stdin.buffer.read().decode('utf-8'); "
                   "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':text}})); "
                   "print(json.dumps({'type':'turn.completed'}))")
        prompt = 'Texto con ñ y "comillas"; $(no-ejecutar)\nsegunda línea'
        with tempfile.TemporaryDirectory() as folder, patch("ai.command_for", return_value=([sys.executable, "-c", program], os.environ.copy())):
            self.assertEqual(ai.run_agent({"provider": "codex"}, prompt, folder, Event()), prompt)

    def test_real_subprocess_failure_preserves_stdout_error(self):
        program = ("import json,sys; sys.stdin.read(); "
                   "print(json.dumps({'type':'error','error':{'message':'Invalid model reference: missing-provider'}})); "
                   "sys.exit(1)")
        with tempfile.TemporaryDirectory() as folder, patch("ai.command_for", return_value=([sys.executable, "-c", program], os.environ.copy())):
            with self.assertRaisesRegex(RuntimeError, "Invalid model reference: missing-provider"):
                ai.run_agent({"provider": "opencode"}, "test", folder, Event())

    def test_timeout_terminates_subprocess(self):
        with tempfile.TemporaryDirectory() as folder, patch("ai.TIMEOUT", 0.1), patch("ai.command_for", return_value=(
                [sys.executable, "-c", "import time; time.sleep(30)"], os.environ.copy())):
            started = time.monotonic()
            with self.assertRaisesRegex(RuntimeError, "límite"):
                ai.run_agent({"provider": "codex"}, "test", folder, Event())
            self.assertLess(time.monotonic() - started, 5)


if __name__ == "__main__":
    unittest.main()
