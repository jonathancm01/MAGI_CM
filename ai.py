"""Installed CLI adapters. Credentials stay with each tool."""

import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
from threading import Lock
import time

PROVIDERS = {"codex": "Codex", "opencode": "OpenCode", "claude": "Claude Code"}
TIMEOUT = 600
MAX_OUTPUT = 2_000_000
_model_cache = {}
_model_lock = Lock()


class Cancelled(Exception):
    pass


def error_info(error):
    """Keep the original diagnostic and offer a concrete recovery action."""
    detail = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', str(error)).strip()
    lowered = detail.lower()
    cases = [
        (('quota', 'usage limit', 'rate limit', '429', 'límite de uso'), 'quota', 'Límite del proveedor',
         'Espera a que se restablezca el límite o elige otro modelo. No se reintenta automáticamente.', False),
        (('invalid model', 'unsupported model', 'not supported', 'model not found', 'modelo no disponible', 'model reference'),
         'model', 'Modelo no disponible', 'Comprueba el identificador y el acceso de tu sesión en Configurar este chat.', False),
        (('unauthorized', '401', '403', 'authentication', 'log in', 'login', 'sesión no disponible'),
         'auth', 'Sesión sin acceso', 'Inicia sesión en la CLI indicada y vuelve a enviar la solicitud.', False),
        (('permission', 'access denied', 'sandbox', 'read-only', 'permiso'), 'permissions', 'Permiso insuficiente',
         'Revisa la carpeta y la herramienta bloqueada. El consejo no puede concederse permisos adicionales.', False),
        (('json válido', 'voto debe contener'), 'format', 'Respuesta de voto inválida',
         'Se solicitará una respuesta estructurada una sola vez; un voto inválido nunca cuenta como aprobación.', True),
        (('timeout', 'timed out', '10 minutos', 'connection', 'network', '503', '502', 'service unavailable'),
         'transient', 'Conexión o tiempo de espera', 'En fases de solo lectura se reintenta este núcleo una vez, conservando las otras respuestas.', True),
    ]
    for patterns, kind, title, action, retryable in cases:
        if any(pattern in lowered for pattern in patterns):
            return dict(kind=kind, title=title, detail=detail, action=action, retryable=retryable)
    return dict(kind='cli', title='La herramienta no pudo terminar', detail=detail,
                action='Consulta el detalle técnico y revisa la sesión y el modelo antes de continuar.', retryable=False)


def find_cli(provider):
    if provider not in PROVIDERS:
        raise ValueError("Motor desconocido.")
    name = provider
    native = shutil.which(name + ".exe") if os.name == "nt" else shutil.which(name)
    if native:
        return [native]
    shim = shutil.which(name)
    if os.name == "nt" and shim:
        packages = {"codex": "@openai/codex/bin/codex.js", "opencode": "@opencode/cli/bin/opencode.exe",
                    "claude": "@anthropic-ai/claude-code/cli.js"}
        candidate = Path(shim).parent / "node_modules" / packages.get(provider, "missing")
        if candidate.is_file():
            if candidate.suffix == ".exe":
                return [str(candidate)]
            if candidate.suffix == ".js" and shutil.which("node"):
                return [shutil.which("node"), str(candidate)]
    raise ValueError(f"No se encontró {PROVIDERS[provider]}. Instala su CLI y reinicia MAGI.")


def validate_model(provider, model):
    if provider == "opencode" and model:
        model_provider, separator, model_name = model.partition("/")
        if not separator or not model_provider or not model_name:
            raise ValueError("OpenCode requiere proveedor/modelo, por ejemplo opencode/deepseek-v4.1-flash-free.")


def parse_models(provider, output):
    if provider == "codex":
        models = json.loads(output)["models"]
        candidates = [(model.get("slug"), model.get("display_name")) for model in models
                      if isinstance(model, dict) and model.get("visibility") == "list"]
    else:
        candidates = [(line.strip(), line.strip()) for line in output.splitlines()]
    result = {}
    for value, label in candidates:
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}", value):
            continue
        if provider == "opencode" and ("/" not in value or not all(value.partition("/")[::2])):
            continue
        result[value] = {"value": value, "label": label if isinstance(label, str) and label else value}
    if not result:
        raise ValueError("La CLI no devolvió modelos seleccionables. Revisa su sesión y versión.")
    return list(result.values())


def query_models(command, workspace):
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, cwd=workspace, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, **options)
        try:
            process.wait(timeout=20)
            if process.returncode:
                raise ValueError("La CLI no pudo listar los modelos. Comprueba su inicio de sesión y versión.")
            stdout.seek(0)
            output = stdout.read(MAX_OUTPUT + 1)
            if len(output) > MAX_OUTPUT:
                raise ValueError("El catálogo de la CLI superó el tamaño permitido.")
            return output.decode("utf-8", errors="replace")
        finally:
            stop_process(process)


def model_catalog(provider, workspace, refresh=False):
    """Metadata only: never send a prompt or replace the selected model."""
    try:
        command = find_cli(provider)
    except ValueError as error:
        return {"installed": False, "models": [], "notice": str(error)}
    if provider == 'claude':
        return {'installed': True, 'models': [{'value': name, 'label': name.capitalize()} for name in ('sonnet', 'haiku', 'opus')],
                'notice': 'Alias de Claude Code, no catálogo de acceso: Sonnet, Haiku y Opus. También puedes escribir un ID exacto. Requiere CLI con --restricted y --safe-mode.'}
    key = (provider, tuple(command), str(workspace))
    with _model_lock:
        previous = _model_cache.get(key)
        if not refresh and previous and time.monotonic() - previous[0] < 300:
            return previous[1]
        try:
            args = ["debug", "models"] if provider == "codex" else ["models", "--standalone"]
            models = parse_models(provider, query_models(command + args, workspace))
            result = {"installed": True, "models": models, "notice": f"{len(models)} modelos en el catálogo de la CLI."}
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
            notice = ("No se pudo leer el catálogo de la CLI." if isinstance(error, (json.JSONDecodeError, KeyError, TypeError))
                      else "La CLI tardó demasiado en listar los modelos." if isinstance(error, subprocess.TimeoutExpired)
                      else str(error) if isinstance(error, ValueError) else "No se pudo leer el catálogo de la CLI.")
            result = {"installed": True, "models": previous[1]["models"] if previous else [],
                      "notice": ("Lista anterior conservada. " if previous else "") + notice}
        _model_cache[key] = (time.monotonic(), result)
        return result


def command_for(node, writable=False):
    provider = node["provider"]
    validate_model(provider, node["model"])
    command, env = find_cli(provider), os.environ.copy()
    if provider == "codex":
        command += ["exec", "--json", "--color", "never", "--skip-git-repo-check",
                    "--sandbox", "workspace-write" if writable else "read-only",
                    "-c", 'approval_policy="never"']
    elif provider == "opencode":
        command += ["run", "--standalone", "--format", "json", "--agent", "build" if writable else "plan"]
        allowed = ["read", "glob", "grep", "execute"] + (["edit"] if writable else [])
        rules = [{"action": "*", "resource": "*", "effect": "deny"}] + [
            {"action": action, "resource": "*", "effect": "allow"} for action in allowed]
        policies = [{"action": "tool.use", "resource": "*", "effect": "deny"}] + [
            {"action": "tool.use", "resource": f"{action}:*", "effect": "allow"} for action in allowed]
        for action in ("read", "edit"):
            for pattern in ("../*", "*/../*", "*.env", "*.env.*", "*.pem", "*.key", ".git/*", "*/.git/*", ".magi/*", "*/.magi/*"):
                policies.append({"action": "tool.use", "resource": f"{action}:{pattern}", "effect": "deny"})
        env.pop("OPENCODE_PERMISSION", None)
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps({
            "permissions": rules, "policies": policies,
            "agents": {agent: {"permissions": rules} for agent in ("plan", "build")},
        })
    elif provider == 'claude':
        tools = ['Read', 'Glob', 'Grep'] + (['Edit', 'Write'] if writable else [])
        denied = [f'{action}({pattern})' for action in ('Read', 'Edit') for pattern in
                  ('.env', '.env.*', '*.pem', '*.key', '.git/**', '.magi/**', '.claude/**', '.mcp.json',
                   '**/.env', '**/.env.*', '**/*.pem', '**/*.key', '**/.git/**', '**/.magi/**', '**/.claude/**', '**/.mcp.json')]
        command += ['--print', '--output-format', 'stream-json', '--verbose', '--restricted', '--safe-mode',
                    '--no-session-persistence', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
                    '--permission-mode', 'dontAsk', '--permission-prompts', 'none', '--disable-slash-commands',
                    '--tools', ','.join(tools), '--allowedTools', ','.join(tools),
                    '--settings', json.dumps({'permissions': {'deny': denied}, 'disableAllHooks': True})]
    else:
        raise ValueError('Motor desconocido. Selecciona uno de los motores disponibles.')
    if node["model"]:
        command += ["--model", node["model"]]
    if provider == "codex":
        command += ["-"]
    return command, env


def parse_output(provider, output, returncode=0, diagnostics=""):
    messages, completed = [], False
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind in ("error", "turn.failed"):
            error = event.get("error") or event
            if isinstance(error, dict):
                data = error.get("data")
                message = error.get("message") or (data.get("message") if isinstance(data, dict) else None)
                message = message or json.dumps(error, ensure_ascii=False)
            else:
                message = str(error)
            try:
                details = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                details = None
            if isinstance(details, dict) and isinstance(details.get("error"), dict):
                message = details["error"].get("message") or message
            raise RuntimeError(f"{PROVIDERS[provider]}: {message}")
        if provider == "codex":
            if kind == "item.completed" and event.get("item", {}).get("type") == "agent_message":
                messages.append(event["item"].get("text", ""))
            completed = completed or kind == "turn.completed"
        elif provider == "opencode":
            if kind == "text":
                part = event.get("part", {})
                messages.append(part.get("text", ""))
                completed = bool(part.get("time", {}).get("end"))
            completed = completed or kind == "step_finish"
        elif provider == 'claude' and kind == 'result':
            if event.get('is_error') or event.get('subtype') != 'success':
                raise RuntimeError('Claude Code: ' + str(event.get('result') or event.get('errors') or event.get('subtype')))
            if event.get('permission_denials'):
                tools = sorted({item['tool_name'] for item in event['permission_denials']
                                if isinstance(item, dict) and isinstance(item.get('tool_name'), str)})
                report = event.get('result')
                detail = '\nInforme de Claude:\n' + report[-6000:] if isinstance(report, str) and report.strip() else ''
                raise RuntimeError('Claude Code: permiso denegado. Herramientas rechazadas: '
                    + (', '.join(tools) or 'no indicadas por la CLI')
                    + '. Este adaptador permite Read/Glob/Grep y, en ejecución, Edit/Write; '
                    'no permite terminal, red, MCP ni subagentes. Revisa los cambios parciales y el alcance autorizado.' + detail)
            messages.append(event.get('result', ''))
            completed = True
    if returncode:
        details = diagnostics.strip() or output.strip() or "La CLI no devolvió detalles del fallo."
        raise RuntimeError(f"{PROVIDERS[provider]} terminó con código {returncode}: {details[-2000:]}")
    text = messages[-1].strip() if messages else ""
    if not text or not completed:
        raise RuntimeError("La CLI no devolvió una respuesta completa. Revisa su sesión, modelo y versión.")
    return text


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=10, check=False)
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=10)


def live_event(provider, event):
    kind = event.get('type')
    if provider == 'claude':
        if kind == 'assistant':
            blocks = event.get('message', {}).get('content', [])
            text = '\n'.join(block.get('text', '') for block in blocks if block.get('type') == 'text')
            if text:
                return {'activity': 'Redactando respuesta…', 'text': text}
            if any(block.get('type') == 'tool_use' for block in blocks):
                return {'activity': 'Usando herramientas de archivos…'}
        if kind == 'result' and not event.get('is_error') and isinstance(event.get('result'), str):
            return {'activity': 'Respuesta recibida', 'text': event['result']}
        return None
    item = event.get('item', {}) if provider == 'codex' else event.get('part', {})
    if not isinstance(item, dict):
        return None
    if (provider == 'codex' and kind == 'item.completed' and item.get('type') == 'agent_message') or kind == 'text':
        return {'activity': 'Redactando respuesta…', 'text': item.get('text', '')}
    if provider == 'codex' and kind in ('item.started', 'item.updated', 'item.completed'):
        if item.get('type') == 'command_execution':
            return {'activity': 'Ejecutando una comprobación…'}
        if item.get('type') == 'file_change':
            paths = [change.get('path', '') for change in item.get('changes', []) if isinstance(change, dict)]
            return {'activity': ('Editando ' + ', '.join(paths))[:200]}
    tool = item.get('tool')
    if isinstance(tool, str):
        state = item.get('state', {})
        data = state.get('input', {}) if isinstance(state, dict) else {}
        path = data.get('filePath', data.get('path', '')) if isinstance(data, dict) else ''
        label = {'read': 'Leyendo', 'glob': 'Buscando archivos', 'grep': 'Buscando texto',
                 'write': 'Creando', 'edit': 'Editando', 'patch': 'Aplicando cambios', 'execute': 'Usando herramientas'}.get(tool, 'Procesando herramienta')
        return {'activity': f'{label} {path}'.strip()[:200]}
    return None


def run_agent(node, prompt, workspace, cancel, writable=False, on_event=None):
    if cancel.is_set():
        raise Cancelled()
    command, env = command_for(node, writable)
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    with tempfile.TemporaryDirectory(prefix='magi-cli-') as folder, open(Path(folder) / 'stdout', 'w+b') as stdout, tempfile.TemporaryFile() as stderr, open(Path(folder) / 'stdout', 'rb') as stream:
        process = subprocess.Popen(command, cwd=workspace, env=env, stdin=subprocess.PIPE,
                                   stdout=stdout, stderr=stderr, **options)
        started, data = time.monotonic(), prompt.encode("utf-8")
        pending = b''
        def publish():
            nonlocal pending
            if on_event is None:
                return
            pending += stream.read(MAX_OUTPUT + 1)
            lines = pending.split(b'\n')
            pending = lines.pop()
            for line in lines:
                try:
                    event = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue
                update = live_event(node['provider'], event) if isinstance(event, dict) else None
                if update:
                    on_event(update)
        try:
            while True:
                if cancel.is_set():
                    raise Cancelled()
                if time.monotonic() - started > TIMEOUT:
                    raise RuntimeError("La CLI superó el límite de 10 minutos.")
                if max(os.fstat(stdout.fileno()).st_size, os.fstat(stderr.fileno()).st_size) > MAX_OUTPUT:
                    raise RuntimeError("La salida de la CLI superó el límite de 2 MB.")
                publish()
                try:
                    process.communicate(input=data, timeout=0.25)
                    break
                except subprocess.TimeoutExpired:
                    data = None
            if cancel.is_set():
                raise Cancelled()
            publish()
            stderr.seek(0)
            diagnostics = stderr.read(MAX_OUTPUT + 1).decode("utf-8", errors="replace")
            stdout.seek(0)
            output = stdout.read(MAX_OUTPUT + 1)
            if len(output) > MAX_OUTPUT:
                raise RuntimeError("La salida de la CLI superó el límite de 2 MB.")
            return parse_output(node["provider"], output.decode("utf-8", errors="replace"), process.returncode, diagnostics)
        finally:
            stop_process(process)
