from copy import deepcopy
import hashlib
import json
import re
from urllib.parse import urlparse

from dash import Dash, Input, Output, State, ALL, MATCH, ctx, dcc, html, no_update
from dash.exceptions import PreventUpdate
from dash_local_react_components import load_react_component
from flask import abort, request

import ai
from harness import DEFAULT_AUTOMATION, DEFAULT_CONFIG, ROOT, NAMES, load_config
from presentation import council_caption, readable_answer, readable_entry, text_blocks
from workspaces import WorkspaceStore


app = Dash(__name__, title="MAGI · Proyectos y chats", update_title=None,
           meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
try:
    settings, startup_error = load_config(), ""
except (ValueError, OSError) as error:
    settings, startup_error = deepcopy(DEFAULT_CONFIG), f"No se pudo cargar la configuración: {error}"
controller = WorkspaceStore(ROOT / ".magi", settings)
initial_chat = controller.data["selected"]
settings = controller.chat(initial_chat)["config"]
initial_project = controller.data['projects'][controller.chat(initial_chat)['project_id']]

Magi = load_react_component(app, "components", "magi.js")
WiseMan = load_react_component(app, "components", "wise_man.js")
Response = load_react_component(app, "components", "response.js")
Modal = load_react_component(app, "components", "modal.js")
Header = load_react_component(app, "components", "header.js")
Status = load_react_component(app, "components", "status.js")


@app.server.before_request
def local_requests_only():
    if request.host.split(":")[0] not in ("127.0.0.1", "localhost"):
        abort(403)
    origin = request.headers.get("Origin")
    if origin and (urlparse(origin).scheme != "http" or urlparse(origin).netloc != request.host):
        abort(403)
    if request.method == "POST" and not request.is_json:
        abort(415)


def choices(identifier, options, value):
    return html.Div(dcc.RadioItems(id=identifier, options=options, value=value, className="magi-choices"),
                    role="radiogroup", **{"aria-labelledby": f"label-{identifier}"})


def node_settings(name, index):
    node = settings["nodes"][name]
    return html.Fieldset([
        html.Legend(f"{name.upper()} · {index}"),
        html.Label("Motor", id=f"label-provider-{name}"),
        choices(f"provider-{name}", [
            {"label": "Codex", "value": "codex"}, {"label": "OpenCode", "value": "opencode"},
            {"label": "Claude Code", "value": "claude"},
        ], node["provider"]),
        html.Label(["Modelo", dcc.Dropdown(id=f"model-{name}", value=node["model"],
                     options=model_options(node["provider"], {}, "", node["model"])[0],
                     searchable=True, clearable=False, optionHeight=50, maxHeight=250,
                     placeholder="Buscar o elegir modelo", className="model-picker")], className="model-label"),
        html.Small(id=f"model-notice-{name}", className="model-notice", role="status"),
        html.Details([
            html.Summary('Perspectiva e instrucciones'),
            html.Label('Instrucciones del núcleo', htmlFor=f'instructions-{name}', className='sr-only'),
            dcc.Textarea(id=f"instructions-{name}", value=node["instructions"], maxLength=8000),
        ], className='node-instructions'),
    ], className="node-settings")


def model_options(provider, catalog, search, current):
    entry = (catalog or {}).get(provider, {})
    models = entry.get("models", [])
    options = [{"value": "", "label": "Predeterminado de la CLI"}] + models
    detected = {option["value"] for option in options}
    if current and current not in detected:
        options.append({"value": current, "label": f"{current} · guardado / no detectado"})
    candidate = (search or "").strip()
    if (candidate and candidate != current and candidate not in detected
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}", candidate)
            and (provider != "opencode" or ("/" in candidate and all(candidate.partition("/")[::2])))):
        options.append({"value": candidate, "label": f"Usar ID manual: {candidate}", "search": candidate})
    notice = entry.get("notice", "Abre la configuración para detectar los modelos.")
    if current and current not in detected:
        notice += " Se conserva tu selección; no está en esta lista."
    return options, notice


app.layout = html.Div(id="desktop-shell", className="desktop-shell", children=[
    html.Aside([
        html.Div([
            html.Div([html.H1("MAGI"), html.Button("‹", id="toggle-sidebar", n_clicks=0, className="sidebar-toggle",
                      **{"aria-label": "Plegar barra de proyectos", "aria-expanded": "true", "aria-controls": "project-list"})],
                     className="brand-heading"),
            html.Span("Multi Agent Group Intelligence"),
        ], className="brand"),
        html.Button("＋ Nuevo chat", id="new-task", n_clicks=0, className="new-chat",
                    title="Crear un chat con su propia carpeta dentro de MAGI"),
        html.Div([
            html.Label('Buscar proyectos o chats', htmlFor='nav-search', className='sr-only'),
            dcc.Input(id='nav-search', type='search', value='', placeholder='Buscar chats…', debounce=False),
            html.P(id='nav-search-status', role='status', className='nav-search-status'),
        ], className='nav-search'),
        html.Div("PROYECTOS", className="section-label"),
        html.Nav(id="project-list", **{"aria-label": "Proyectos y chats"}),
        html.Button("Diseño: Clásico ⇄", id="switch-design", n_clicks=0, className="design-switch",
                    title="Cambiar entre el diseño clásico y el triangular", **{"aria-pressed": "false"}),
        html.Details([
            html.Summary("＋ Añadir proyecto"),
            html.Label("Nombre del proyecto", htmlFor="project-name"),
            dcc.Input(id="project-name", value="", maxLength=80, placeholder="Nombre opcional"),
            html.Label("Carpeta existente", htmlFor="project-path"),
            dcc.Input(id="project-path", value="", placeholder="C:\\ruta\\al\\proyecto"),
            html.Button("Abrir proyecto", id="add-project", n_clicks=0),
        ], className="add-project"),
        html.P("● SESIONES LOCALES", className="local-indicator"),
    ], className="sidebar"),
    html.Main([
      html.Section([
        html.Div(Magi(id="magi", children=[
            Header(id="header-left", side="left", title="指示"),
            Header(id="header-right", side="right", title="待機中"), Status(id="status"),
            *[WiseMan(id={"type": "wise-man", "name": name}, name=name, order_number=index)
              for index, name in enumerate(NAMES, 1)], Response(id="response", status="info"),
        ]), className='magi-stage'),
        html.Div([
            html.Div(id="progress", role="status", **{"aria-live": "polite"}),
            html.Span(id='run-metrics', className='run-metrics'),
        ], className='run-strip'),
      ], className="council-pane", **{"aria-label": "Panel MAGI"}),
      html.Section([
        html.Header([
            html.Div([html.H2([html.Span('通信', className='nerv-japanese', **{'aria-hidden': 'true'}), "Conversación"]), html.Span(id='execution-policy', className='execution-policy',
                         **{'data-policy': settings['automation']['mode']})], className='chat-heading-copy'),
            html.Div([
                html.Button("Ejecutar plan", id="execute", n_clicks=0, disabled=True),
                html.Button("Revisar", id="review", n_clicks=0, disabled=True),
                html.Button("Detener", id="cancel", n_clicks=0, disabled=True,
                            title='Detiene los modelos. Los cambios ya guardados permanecen en disco.'),
                html.Button('Ampliar chat', id='expand-chat', type='button',
                            **{'aria-pressed': 'false', 'aria-controls': 'conversation'}),
                html.Button('↓ Últimos', id='jump-latest', type='button', hidden=True, className='jump-latest',
                            title='Ir a los mensajes más recientes'),
                html.Button("Configuración", id="open-configuration", n_clicks=0,
                            **{'aria-haspopup': 'dialog', 'aria-controls': 'workspace-tools'}),
            ], className='task-actions', role='group', **{'aria-label': 'Acciones del chat'}),
        ], className='conversation-heading'),
        html.Div(id="notice", children=startup_error, role="alert"),
        html.Div(id="storage-notice", role="alert"),
        html.Div(id="conversation", className="conversation", role="region", tabIndex=0,
                 **{"aria-label": "Conversación del chat", "data-chat": initial_chat}),
        html.Section([
            html.Div([
                html.Div([
                    html.Label('Modo', htmlFor='request-mode', className='sr-only'),
                    dcc.Dropdown(id='request-mode', value='auto', clearable=False, searchable=False,
                                 options=[{'label': label, 'value': value} for value, label in
                                          [('auto', 'Automático'), ('ask', 'Preguntar'), ('work', 'Trabajar'), ('council', 'Consejo')]],
                                 className='model-picker'),
                ], className='request-mode'),
                html.Label('Mensaje para MAGI', htmlFor='query', className='sr-only'),
                dcc.Textarea(id="query", value=controller.chat(initial_chat)["draft"], maxLength=16000,
                             placeholder="Haz una pregunta o pide un cambio…"),
                html.Button("Enviar", id="start", n_clicks=0, className="primary", disabled=True,
                            **{'data-busy': True, 'aria-keyshortcuts': 'Control+Enter Meta+Enter'}),
            ], className='composer-inputs'),
            html.Div([
                html.P(id="task-context", className="help composer-help"),
                html.Span(id="draft-status", className="draft-status", role="status"),
                html.Span('Ctrl + Enter para enviar', className='send-shortcut'),
            ], className='composer-meta'),
        ], className="composer", **{'aria-label': 'Escribir un mensaje'}),
      ], className="chat-pane", **{'aria-label': 'Chat de MAGI'}),
    ], className='workspace-pane'),
    html.Dialog([
      html.Header([
        html.H2([html.Span('設定', className='nerv-japanese', **{'aria-hidden': 'true'}), 'Configurar este chat'], id='tools-title'),
        html.Button('Cerrar', id='close-configuration', type='button'),
      ], className='tools-heading'),
      html.Div([
          html.Button(label, type='button', id=f'tab-{key}', role='tab', className='settings-tab',
                      **{'data-settings-tab': key, 'aria-selected': 'true' if key == 'chat' else 'false',
                         'aria-controls': f'panel-{key}'}, tabIndex=0 if key == 'chat' else -1)
          for key, label in [('chat', 'Chat y trabajo'), ('models', 'Núcleos'), ('activity', 'Actividad')]
      ], className='settings-tabs', role='tablist', **{'aria-label': 'Secciones de configuración'}),
      html.Div([
        html.Section([
            html.H3('Este chat'),
            html.Label('Nombre del chat', htmlFor='chat-title'),
            dcc.Input(id='chat-title', value=controller.chat(initial_chat)['title'], type='text', maxLength=80),
            html.Label('Nombre del proyecto', htmlFor='workspace-name'),
            dcc.Input(id='workspace-name', value=initial_project['name'], type='text', maxLength=80),
            html.Label("Carpeta del proyecto", htmlFor="workspace"),
            dcc.Input(id="workspace", value=settings["workspace"], type="text", readOnly=True),
            html.P('Para usar otra carpeta, añade un proyecto desde la barra lateral.', className='help'),
            html.Label("Automatización", id="label-automation-mode"),
            choices("automation-mode", [
                {"label": "Manual · tú inicias la edición", "value": "manual"},
                {"label": "Consejo automático · debate y revisión", "value": "council"},
                {"label": "Autónomo · permite editar al enviar", "value": "autonomous"},
            ], settings["automation"]["mode"]),
            html.P('Manual y Consejo automático esperan a que pulses Ejecutar plan. Autónomo puede implementar y corregir dentro de tu solicitud.', className='help'),
            html.Details([
                html.Summary('Límites y consenso'),
                html.Label("Acuerdo entre los núcleos", id="label-consensus"),
                choices("consensus", [{"label": "Unanimidad · 3 de 3", "value": "unanimous"},
                                       {"label": "Mayoría · 2 de 3", "value": "majority"}], settings["consensus"]),
                html.Div([
                    html.Div([html.Label("Máximo de ciclos", htmlFor="max-cycles"),
                              dcc.Input(id="max-cycles", type="number", min=1, max=5, step=1, value=settings["automation"]["max_cycles"])]),
                    html.Div([html.Label("Consultas por operación", htmlFor="max-calls"),
                              dcc.Input(id="max-calls", type="number", min=6, max=120, step=1, value=settings["automation"]["max_calls"])]),
                ], className="automation-limits"),
                html.P('Cada reintento cuenta. Detener cancela las llamadas; los cambios escritos permanecen. Reiniciar nunca reanuda una ejecución.', className='help'),
            ], className='advanced-settings'),
        ], id='panel-chat', className='configuration settings-panel', role='tabpanel',
           **{'data-settings-panel': 'chat', 'aria-labelledby': 'tab-chat'}),
        html.Section([
            html.H3('Los tres núcleos'),
            html.Label("Núcleo coordinador", id="label-executor"),
            choices("executor", [{"label": name.upper(), "value": name} for name in NAMES], settings["executor"]),
            html.Div([
                html.Button("Actualizar modelos", id="refresh-models", n_clicks=0),
                dcc.Loading(html.Div(id="model-catalog-status", role="status"), type="dot", color="#ff8d00"),
            ], className="model-toolbar"),
            html.Div([node_settings(name, index) for index, name in enumerate(NAMES, 1)], className="chat-node-settings"),
            html.P("Busca un modelo o escribe su ID y elige «Usar ID manual». El catálogo no garantiza acceso ni cuota. Las sesiones permanecen en cada herramienta.", className="help"),
        ], id='panel-models', className='configuration settings-panel', role='tabpanel', hidden=True,
           **{'data-settings-panel': 'models', 'aria-labelledby': 'tab-models'}),
        html.Section([
            html.H3('Seguimiento del trabajo'),
            html.Div(id="automation-status", className="automation-status", role="status"),
            html.Div(id="agent-summary", className="agent-summary"),
            html.Details([html.Summary("Comunicación entre núcleos"), html.Div(id="communications")], className="communication-panel"),
            html.Details([
                html.Summary("Contexto y consumo"),
                html.Pre(id="task-goal"),
                html.P("Cada chat conserva su objetivo y memoria. Los chats de un mismo proyecto comparten archivos. Solo una operación puede ejecutarse a la vez.", className="help"),
                html.P("Consultas base: pregunta directa, 1; deliberación, 6; ejecución cooperativa y revisión, 8; revisar, 3. Enrutamiento, ciclos y reintentos pueden añadir consultas. Navegar y guardar no consultan modelos.", className="help"),
            ], className="context-panel"),
            html.Details([html.Summary('Atajos de teclado'), html.Ul([
                html.Li('Ctrl / ⌘ + Enter: enviar el mensaje'), html.Li('Ctrl / ⌘ + K: buscar chats'),
                html.Li('Ctrl / ⌘ + coma: configuración'), html.Li('Escape: cerrar la ventana'),
            ])], className='keyboard-help'),
        ], id='panel-activity', className='settings-panel', role='tabpanel', hidden=True,
           **{'data-settings-panel': 'activity', 'aria-labelledby': 'tab-activity'}),
      ], className='tools-body'),
      html.Footer([
          html.Div([html.P('Los cambios se aplican al guardar.', className='help'),
                    html.Span(id='settings-dirty', role='status'), html.Div(id='configuration-notice', role='status')]),
          html.Button('Guardar cambios', id='save', n_clicks=0, className='primary'),
      ], className='tools-footer'),
    ], id='workspace-tools', className='workspace-tools', **{'aria-labelledby': 'tools-title'}),
    *[Modal(id={"type": "modal", "name": name}, name=name) for name in NAMES],
    dcc.Store(id="view", data={"chat_id": initial_chat}, storage_type="session"),
    dcc.Store(id="session", data={"chat_id": initial_chat, "id": ""}),
    dcc.Store(id="composer-chat", data=initial_chat),
    dcc.Store(id='saved-form', data={'title': controller.chat(initial_chat)['title'], 'project_name': initial_project['name'], 'config': settings}),
    dcc.Store(id="nav-signature"), dcc.Store(id="conversation-signature"),
    dcc.Store(id="ui-design", data="classic", storage_type="local"),
    dcc.Store(id="model-catalog", data={}),
    dcc.Store(id="sidebar-collapsed", data=False, storage_type="local"),
    dcc.Interval(id="poll", interval=750),
])


app.clientside_callback(
    "function(busy, text) { return busy === true || busy === 'true' || !(text || '').trim(); }",
    Output('start', 'disabled'), Input('start', 'data-busy'), Input('query', 'value'))

app.clientside_callback(
    """function(mode, policy) {
        if (mode === 'ask') return ['Solo lectura', 'Responde preguntas sin crear ni editar archivos.'];
        if (policy === 'autonomous') return ['Edición al enviar',
            'Las solicitudes de trabajo permiten implementar y corregir dentro del alcance aprobado. Las preguntas siguen en lectura.'];
        return ['Edición con confirmación', 'MAGI preparará el trabajo. Pulsa Ejecutar plan cuando esté aprobado para empezar a editar.'];
    }""", Output('execution-policy', 'children'), Output('execution-policy', 'title'),
    Input('request-mode', 'value'), Input('execution-policy', 'data-policy'))

app.clientside_callback("function(path) { return !(path || '').trim(); }",
                        Output('add-project', 'disabled'), Input('project-path', 'value'))

app.clientside_callback(
    """function(saved, title, project, rule, executor, mode, cycles, calls, ...nodes) {
        if (!saved) return '';
        const config = saved.config;
        const values = [title, project, rule, executor, mode, cycles, calls, ...nodes];
        const expected = [saved.title, saved.project_name, config.consensus, config.executor, config.automation.mode,
            config.automation.max_cycles, config.automation.max_calls,
            ...['melchior', 'balthasar', 'casper'].flatMap(n =>
                ['provider', 'model', 'instructions'].map(k => config.nodes[n][k]))];
        const clean = value => typeof value === 'string' ? value.trim() : value;
        return values.some((value, index) => clean(value) !== clean(expected[index])) ? 'Cambios sin guardar' : '';
    }""", Output('settings-dirty', 'children'), Input('saved-form', 'data'), Input('chat-title', 'value'),
    Input('workspace-name', 'value'),
    Input('consensus', 'value'), Input('executor', 'value'), Input('automation-mode', 'value'),
    Input('max-cycles', 'value'), Input('max-calls', 'value'),
    *[Input(f'{field}-{name}', 'value') for name in NAMES for field in ('provider', 'model', 'instructions')])


@app.callback(Output("sidebar-collapsed", "data"), Input("toggle-sidebar", "n_clicks"),
              State("sidebar-collapsed", "data"), prevent_initial_call=True)
def toggle_sidebar(_, collapsed):
    return collapsed is not True


@app.callback(Output("desktop-shell", "className"), Output("toggle-sidebar", "children"),
              Output("toggle-sidebar", "aria-expanded"), Output("toggle-sidebar", "aria-label"),
              Input("sidebar-collapsed", "data"))
def apply_sidebar(collapsed):
    if collapsed is True:
        return "desktop-shell desktop-shell--compact", "›", "false", "Mostrar barra de proyectos"
    return "desktop-shell", "‹", "true", "Plegar barra de proyectos"


@app.callback(Output("model-catalog", "data"), Output("model-catalog-status", "children"),
              Input("open-configuration", "n_clicks"), Input("refresh-models", "n_clicks"), Input("workspace", "value"),
              prevent_initial_call=True)
def discover_models(opened, _, workspace):
    if not opened:
        raise PreventUpdate
    catalog = {provider: ai.model_catalog(provider, workspace, refresh=ctx.triggered_id == "refresh-models")
               for provider in ai.PROVIDERS}
    installed = [ai.PROVIDERS[provider] for provider, entry in catalog.items() if entry["installed"]]
    return catalog, ("Detectado: " + " · ".join(installed) if installed else "No se detectaron CLI compatibles.")


for node_name in NAMES:
    app.callback(Output(f"model-{node_name}", "options", allow_duplicate=True), Output(f"model-notice-{node_name}", "children"),
                 Input(f"provider-{node_name}", "value"), Input("model-catalog", "data"),
                 Input(f"model-{node_name}", "search_value"), Input(f"model-{node_name}", "value"),
                 prevent_initial_call=True)(model_options)


@app.callback(Output("ui-design", "data"), Input("switch-design", "n_clicks"),
              State("ui-design", "data"), prevent_initial_call=True)
def switch_design(_, current):
    return "classic" if current == "triangular" else "triangular"


@app.callback(Output("magi", "variant"), Output("switch-design", "children"), Output("switch-design", "aria-pressed"),
              Input("ui-design", "data"))
def apply_design(design):
    triangular = design == "triangular"
    return ("triangular" if triangular else "classic", f"Diseño: {'Triangular' if triangular else 'Clásico'} ⇄",
            "true" if triangular else "false")


def read_settings(workspace, rule, executor, values):
    return {"workspace": workspace, "consensus": rule, "executor": executor,
            "automation": dict(zip(DEFAULT_AUTOMATION, values[9:12])) if len(values) >= 12 and values[9] is not None else deepcopy(DEFAULT_AUTOMATION),
            "nodes": {name: dict(zip(("provider", "model", "instructions"), values[index * 3:index * 3 + 3]))
                      for index, name in enumerate(NAMES)}}


@app.callback(
    Output("notice", "children"), Output("query", "value", allow_duplicate=True),
    Output("configuration-notice", "children"),
    Output('saved-form', 'data', allow_duplicate=True),
    Input("start", "n_clicks"), Input("save", "n_clicks"), Input("cancel", "n_clicks"),
    Input("execute", "n_clicks"), Input("review", "n_clicks"),
    State("query", "value"), State("workspace", "value"), State("consensus", "value"), State("executor", "value"),
    State("view", "data"), State("session", "data"), State("composer-chat", "data"),
    State('request-mode', 'value'),
    State('chat-title', 'value'),
    State('workspace-name', 'value'),
    *[State(f"{field}-{name}", "value") for name in NAMES for field in ("provider", "model", "instructions")],
    State("automation-mode", "value"), State("max-cycles", "value"), State("max-calls", "value"),
    prevent_initial_call=True,
)
def handle_action(start, save, cancel, execute, review, task, workspace, rule, executor, view, session, composer, request_mode, chat_title, project_name, *values):
    action = ctx.triggered_id
    try:
        if not session or session.get("chat_id") != view.get("chat_id") or composer != view.get("chat_id"):
            raise ValueError("El chat está cambiando. Espera a que cargue antes de enviar.")
        config = (read_settings(workspace, rule, executor, values) if action == 'save'
                  else controller.chat(view['chat_id'])['config'])
        controller.perform(view["chat_id"], session["id"], action, task or "", config,
                           request_mode=request_mode or 'auto', title=chat_title if action == 'save' else None,
                           project_name=project_name if action == 'save' else None)
        message = {"start": "Solicitud enviada con el contexto de este chat.", "save": "Configuración guardada para este chat.",
                 "execute": "Ejecución iniciada.", "review": "Revisión iniciada sin repetir la implementación.",
                 "cancel": "Cancelación solicitada."}[action]
        saved = controller.chat(view['chat_id'])
        return (message, "" if action == "start" else no_update, message if action == "save" else no_update,
                {'title': saved['title'], 'project_name': controller.data['projects'][saved['project_id']]['name'],
                 'config': saved['config']} if action == 'save' else no_update)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        return str(error), no_update, str(error) if action == "save" else no_update, no_update


@app.callback(
    Output("view", "data"), Output("notice", "children", allow_duplicate=True),
    Input("new-task", "n_clicks"), Input("add-project", "n_clicks"),
    Input({"type": "chat", "id": ALL}, "n_clicks"), Input({"type": "project", "id": ALL}, "n_clicks"),
    Input({"type": "new-chat", "id": ALL}, "n_clicks"),
    Input({"type": "delete-chat", "id": ALL}, "n_clicks"),
    Input({"type": "restore-chat", "id": ALL}, "n_clicks"), Input("poll", "n_intervals"),
    State("composer-chat", "data"), State("query", "value"), State("project-path", "value"), State("project-name", "value"),
    State("view", "data"),
    prevent_initial_call=True,
)
def navigate(new, add, chats, projects, new_chats, deletes, restores, poll, previous, draft, folder, name, view):
    trigger = ctx.triggered_id
    if trigger == "poll":
        target = current_chat_id(view)
        if isinstance(view, dict) and view.get("chat_id") == target:
            raise PreventUpdate
        return {"chat_id": target}, "El chat se envió a la papelera desde otra vista."
    clicks = {"chat": chats, "project": projects, "new-chat": new_chats,
              "delete-chat": deletes, "restore-chat": restores}.get(trigger.get("type"), []) if isinstance(trigger, dict) else []
    if not ctx.triggered or (not any(clicks) if isinstance(trigger, dict) else not ctx.triggered[0].get("value")):
        raise PreventUpdate
    try:
        if previous in controller.data["chats"]:
            controller.save_draft(previous, draft or "")
        notice = ""
        if trigger == "add-project":
            project = controller.add_project(folder, name or "")
            candidates = [(key, item) for key, item in controller.data["chats"].items() if item["project_id"] == project]
            target = max(candidates, key=lambda item: item[1]["updated"])[0] if candidates else controller.new_chat(project)
        elif trigger == "new-task":
            target = controller.new_chat(source=current_chat_id({"chat_id": previous}))
        elif trigger["type"] == "delete-chat":
            controller.delete_chat(trigger["id"])
            target = previous if previous in controller.data["chats"] else controller.data["selected"]
            notice = "Chat enviado a la papelera. Puedes restaurarlo desde la barra lateral. Los archivos del proyecto se conservaron."
        elif trigger["type"] == "restore-chat":
            controller.restore_chat(trigger["id"])
            target = trigger["id"]
            notice = "Chat restaurado."
        elif trigger["type"] == "new-chat":
            target = controller.new_chat(trigger["id"])
        elif trigger["type"] == "project":
            candidates = [(key, item) for key, item in controller.data["chats"].items() if item["project_id"] == trigger["id"]]
            target = max(candidates, key=lambda item: item[1]["updated"])[0] if candidates else controller.new_chat(trigger["id"])
        else:
            target = trigger["id"]
        controller.select(target)
        return {"chat_id": target}, notice
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        return no_update, str(error)


def current_chat_id(view):
    with controller.lock:
        chat_id = view.get("chat_id") if isinstance(view, dict) else None
        return chat_id if isinstance(chat_id, str) and chat_id in controller.data["chats"] else controller.data["selected"]


@app.callback(
    Output("query", "value"), Output("composer-chat", "data"),
    Output("workspace", "value"), Output("consensus", "value"), Output("executor", "value"),
    *[Output(f"{field}-{name}", "value") for name in NAMES for field in ("provider", "model", "instructions")],
    Output("automation-mode", "value"), Output("max-cycles", "value"), Output("max-calls", "value"),
    Output('chat-title', 'value'),
    Output('workspace-name', 'value'),
    Output('saved-form', 'data'),
    *[Output(f"model-{name}", "options") for name in NAMES],
    Input("view", "data"), State("model-catalog", "data"),
)
def load_chat(view, catalog=None):
    with controller.lock:
        chat_id = current_chat_id(view)
        chat = controller.chat(chat_id)
        project_name = controller.data['projects'][chat['project_id']]['name']
    config = chat["config"]
    return (chat["draft"], chat_id, config["workspace"], config["consensus"], config["executor"],
            *[config["nodes"][node][field] for node in NAMES for field in ("provider", "model", "instructions")],
            *[config["automation"][field] for field in DEFAULT_AUTOMATION],
            chat['title'],
            project_name,
            {'title': chat['title'], 'project_name': project_name, 'config': config},
            *[model_options(config["nodes"][name]["provider"], catalog, "", config["nodes"][name]["model"])[0]
              for name in NAMES])


@app.callback(Output("draft-status", "children"), Input("query", "n_blur"),
              State("query", "value"), State("composer-chat", "data"), prevent_initial_call=True)
def save_draft(_, draft, chat_id):
    try:
        controller.save_draft(chat_id, draft or "")
        return "Borrador guardado" if draft else ""
    except (ValueError, KeyError, OSError) as error:
        return str(error)


def sidebar(data, current):
    groups = []
    for project_id, project in data["projects"].items():
        chats = sorted(((key, chat) for key, chat in data["chats"].items() if chat["project_id"] == project_id),
                       key=lambda item: item[1]["updated"], reverse=True)
        if not chats:
            continue
        groups.append(html.Section([
            html.Div([
                html.Button([html.Span("▱", **{"aria-hidden": "true"}), project["name"]],
                            id={"type": "project", "id": project_id}, n_clicks=0, title=project["path"], className="project-button"),
                html.Button("＋", id={"type": "new-chat", "id": project_id}, n_clicks=0,
                            **{"aria-label": f"Nuevo chat en {project['name']}"}, className="project-add-chat"),
            ], className="project-row"),
            html.Ul([html.Li([html.Button([
                html.Span("◌" if chat["busy"] else "·", className="chat-marker", **{"aria-hidden": "true"}),
                html.Span(chat["title"], className="chat-name"),
                *([html.Span("Trabajando", className="busy-label")] if chat["busy"] else []),
            ], id={"type": "chat", "id": key}, n_clicks=0, title=chat["title"],
                className="chat-link selected" if key == current else "chat-link",
                **{"aria-current": "page" if key == current else "false"}),
                html.Button("×", id={"type": "delete-chat", "id": key}, n_clicks=0, disabled=chat["busy"],
                            className="chat-delete", title="Espera a que termine el chat" if chat["busy"] else "Enviar chat a la papelera",
                            **{"aria-label": f"Eliminar chat: {chat['title']}"}),
            ], className="chat-row", **{'data-chat-title': chat['title']}) for key, chat in chats]),
        ], className="project-group", **{'data-project-name': project['name']}))
    trash = data.get("trash", {})
    if trash:
        groups.append(html.Details([
            html.Summary(f"Papelera ({len(trash)})"),
            html.P("Los archivos de los proyectos se conservan."),
            html.Ul([html.Li([
                html.Span(chat["title"], className="chat-name", title=chat["title"]),
                html.Button("Restaurar", id={"type": "restore-chat", "id": key}, n_clicks=0,
                            **{"aria-label": f"Restaurar chat: {chat['title']}"}),
            ], className="chat-row") for key, chat in sorted(trash.items(), key=lambda item: item[1]["updated"], reverse=True)]),
        ], className="chat-trash"))
    return groups


def inline_text(text):
    return [html.Strong(part[2:-2]) if part.startswith("**") else html.Code(part[1:-1]) if part.startswith("`") else part
            for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text)]


def message_body(blocks):
    return [html.Pre(block["text"], className="message-code") if block["type"] == "code"
            else html.Hr() if block["type"] == "divider"
            else html.Div(html.Table([html.Thead(html.Tr([html.Th(inline_text(cell)) for cell in block["headers"]])),
                                      html.Tbody([html.Tr([html.Td(inline_text(cell)) for cell in row]) for row in block["rows"]])]),
                          className="message-table") if block["type"] == "table"
            else html.H4(inline_text(block["text"])) if block["type"] == "heading"
            else html.Ul([html.Li(inline_text(item)) for item in block["items"]]) if block["type"] == "list"
            else html.P(inline_text(block["text"]), className="message-paragraph") for block in blocks]


def message_entry(entry):
    item = readable_entry(entry)
    info = item.get("error_info")
    return html.Article([
        html.Div([html.Strong("MAGI · COORDINACIÓN" if item.get("sender") == "system" else item.get("sender", "MAGI").upper() + " → CONSEJO"),
                  html.Span(item["label"], className=f"vote-badge vote-{item.get('status', 'info')}")], className="message-meta"),
        html.Small(f"{item.get('phase', '')} · ciclo {item.get('cycle', 1)} · {item.get('at', '')[11:19]} UTC"),
        *message_body(item["blocks"]),
        *([html.P(info["action"], className="error-action"),
           html.Details([html.Summary("Detalle técnico"), html.Pre(info["detail"])])] if info else []),
    ], className=f"kernel-message kernel-{item.get('status', 'info')}")


def conversation(state):
    dialogue = [entry for entry in state.get('dialogue', []) if entry['status'] != 'routed']
    if not state["task_id"] and not dialogue:
        return html.Div([html.Span("01 / NUEVO CONTEXTO", className="section-label"), html.H2("¿Qué construimos?"),
                         html.P("Haz una pregunta o describe lo que quieres construir. MAGI elegirá cómo ayudarte."),
                         html.P("Este chat conserva su propia memoria.")], className="empty-chat")
    items = state["checkpoints"] + [state] if state['task_id'] else []
    messages = []
    def questions(iteration):
        for entry in dialogue:
            if entry['after_iteration'] != iteration:
                continue
            messages.append(html.Article([html.Span('TÚ · CONSULTA', className='message-label'),
                                          html.Pre(entry['question'])], className='message user-message'))
            info = entry.get('error_info') if entry['status'] == 'error' else None
            messages.append(html.Article([
                html.Span(entry['node'].upper() + ' · RESPUESTA', className='message-label'),
                *message_body(text_blocks(entry['reply'])),
                html.Small(f"{entry.get('calls', 0)} {'consulta' if entry.get('calls') == 1 else 'consultas'} · Solo lectura", className='help'),
                *([html.P(entry['activity'], className='help', role='status')] if entry['status'] != 'answer' else []),
                *([html.P(info['action'], className='error-action'), html.Details([html.Summary('Detalle técnico'), html.Pre(info['detail'])])] if info else []),
                *([html.Details([html.Summary('Perspectivas del consejo'),
                                *[html.Section([html.Strong(name.upper()), *message_body(text_blocks(reply))])
                                  for name, reply in entry['opinions'].items()]])] if entry.get('opinions') else []),
            ], className='message council-message', **{'aria-live': 'polite'}))
    questions(0)
    for item in items:
        iteration = item["iteration"]
        messages.append(html.Article([html.Span(f"TÚ · PASO {iteration}", className="message-label"),
                                     html.Pre(item["request"])], className="message user-message"))
        entries = []
        for name in NAMES:
            for entry in state["answers"][name]["history"]:
                if entry.get("iteration", 1) == iteration:
                    entries.append(html.Details([html.Summary(f"{name.upper()} · {entry['phase']} · ciclo {entry.get('cycle', 1)}"),
                                                 message_entry({**entry, "sender": name})]))
        messages.append(html.Article([
            html.Span(f"MAGI · PASO {iteration}", className="message-label"),
            *message_body(text_blocks(item.get("plan", ""))),
            *([html.P("Los núcleos están trabajando…" if state["busy"] else state["message"], className="help")]
              if item is state else []),
            *([html.Details([html.Summary("Informe de ejecución"), html.Pre(item["execution_report"])])]
              if item.get("execution_report") and item.get("execution_request") == item["request"] else []),
            *entries,
        ], className="message council-message"))
        questions(iteration)
    if state['busy'] and not state.get('query_busy'):
        for name, answer in state['answers'].items():
            if not answer['id'] and answer.get('response'):
                messages.append(html.Article([html.Span(name.upper() + ' · EN VIVO', className='message-label'),
                                              html.P(answer.get('activity', 'Procesando'), className='help'),
                                              *message_body(text_blocks(answer['response']))], className='message council-message'))
    return messages


@app.callback(
    Output("session", "data"), Output("progress", "children"),
    Output("start", "data-busy"), Output("save", "disabled"), Output("cancel", "disabled"), Output("execute", "disabled"),
    Output("review", "disabled"), Output("status", "extention"), Output("response", "status"),
    Output("response", "question_id"), Output("response", "answer_id"),
    Output({"type": "wise-man", "name": ALL}, "answer"), Output({"type": "wise-man", "name": ALL}, "question_id"),
    Output({"type": "wise-man", "name": ALL}, "runtime"),
    Output({"type": "modal", "name": ALL}, "question"), Output({"type": "modal", "name": ALL}, "answer"),
    Output("start", "children"), Output("storage-notice", "children"), Output("task-context", "children"),
    Output("task-goal", "children"), Output("agent-summary", "children"),
    Output("project-list", "children"), Output("nav-signature", "data"),
    Output("conversation", "children"), Output("conversation-signature", "data"), Output("conversation", "data-chat"),
    Output("automation-status", "children"), Output("communications", "children"),
    Output("header-left", "title"), Output("header-right", "title"),
    Output("header-left", "translation"), Output("header-right", "translation"),
    Output("response", "text"), Output("response", "translation"),
    Output('execution-policy', 'data-policy'), Output('run-metrics', 'children'),
    Input("poll", "n_intervals"), Input("view", "data"),
    State("nav-signature", "data"), State("conversation-signature", "data"),
)
def refresh(_, view, previous_nav, previous_conversation):
    with controller.lock:
        chat_id = current_chat_id(view)
        chat, engine = controller.chat(chat_id), controller.engine(chat_id)
        state, data = engine.snapshot(), controller.navigation()
    config = chat["config"]
    answers = [{**state["answers"][name], "error_info": state["answers"][name].get("error_info") or
                (ai.error_info(state["answers"][name]["error"]) if state["answers"][name]["error"] else None)} for name in NAMES]
    descriptions = [f"{ai.PROVIDERS[config['nodes'][name]['provider']]} · {config['nodes'][name]['model'] or 'modelo de la CLI'}" for name in NAMES]
    nav_data = [(key, value["title"], value["updated"], value["busy"]) for key, value in data["chats"].items()]
    nav_hash = hashlib.sha256(json.dumps([chat_id, data["projects"], nav_data, data.get("trash", {})], sort_keys=True).encode()).hexdigest()
    conversation_hash = hashlib.sha256(json.dumps([chat_id, state, config], sort_keys=True).encode()).hexdigest()
    modal_answers = [readable_answer(answer, state.get("communications", [])) for answer in answers] if conversation_hash != previous_conversation else [no_update] * 3
    node_answers = [{key: value for key, value in answer.items() if key != "history"} for answer in answers]
    occupied = controller.busy()
    left, right, translation, response_text, response_translation = council_caption(state)
    last_query = state.get('dialogue', [])[-1:]
    calls = (last_query[0].get('calls', 0) if last_query and last_query[0]['status'] != 'routed'
             else state['usage']['calls'])
    metrics = f"{calls} {'consulta' if calls == 1 else 'consultas'}" if calls or state['busy'] else ''
    if metrics and state['task_id'] and not (last_query and last_query[0]['status'] != 'routed'):
        metrics += f" · Ciclo {state['usage']['cycle']}"
    budget_limit = state['usage']['limit'] if engine.config else config['automation']['max_calls']
    return (
        {"chat_id": chat_id, "id": state["id"]}, state["message"],
        occupied, state["busy"], not state["busy"], occupied or state["phase"] != "ready",
        occupied or not state["execution_report"] or state["phase"] in ("ready", "blocked", "restored"),
        state["phase"].upper(), state["status"], state["id"], "" if state["busy"] else state["id"],
        node_answers, [state["id"]] * 3, descriptions,
        [{"id": state["id"], "query": state["request"], "goal": state["task"]}] * 3, modal_answers,
        "Enviar", controller.storage_error or engine.dialogue_error or engine.storage_error,
        "Otro chat está trabajando. Puedes preparar tu siguiente mensaje." if occupied and not state["busy"]
        else "El contexto de este chat se conserva.",
        f"Objetivo original:\n{state['task']}" if state["task_id"] else "Este chat todavía no tiene un objetivo.",
        [html.Div([html.Strong(name.upper()), html.Span(description),
                   html.Small(answer["error_info"]["title"] if answer.get("error_info") else answer["conditions"] or answer.get("activity", "En espera")),
                   html.Details([html.Summary('Aportes y verificaciones'),
                       *([message_entry(entry) for entry in answer['history']
                          if entry.get('iteration') == state['iteration'] and
                          entry.get('phase') in ('Síntesis del plan', 'Preparación del aporte', 'Ejecución', 'Revisión del resultado')]
                         or [html.P('Este núcleo todavía no ha entregado aportes en esta iteración.', className='help')])]),
                   *([html.P(answer["error_info"]["action"], className="error-action"),
                      html.Details([html.Summary("Detalle técnico"), html.Pre(answer["error_info"]["detail"])])] if answer.get("error_info") else [])],
                  className="agent-card agent-error" if answer["error"] else "agent-card", role="alert" if answer["error"] else "group")
         for name, description, answer in zip(NAMES, descriptions, answers)],
        sidebar(data, chat_id) if nav_hash != previous_nav else no_update, nav_hash,
        conversation(state) if conversation_hash != previous_conversation else no_update, conversation_hash, chat_id,
        [html.Span(f"{ {'manual': 'MANUAL', 'council': 'CONSEJO AUTOMÁTICO', 'autonomous': 'AUTÓNOMO'}[config['automation']['mode']] } · "
            f"Consultas: {state['usage']['calls']}/{budget_limit} · Ciclo: {state['usage']['cycle']} · Correcciones: {state['usage']['repairs']}"),
         html.Progress(value=state['usage']['calls'], max=budget_limit, className='call-budget',
             title=f"{state['usage']['calls']} de {budget_limit} consultas utilizadas",
             **{'aria-label': 'Consultas consumidas del presupuesto de esta operación'})],
        ([message_entry(entry) for entry in state.get("communications", [])[-30:]] or
         html.P("Los mensajes del consejo aparecerán al enviar una nueva solicitud. El historial anterior sigue disponible en cada núcleo.", className="help")) if conversation_hash != previous_conversation else no_update,
        left, right, translation, translation, response_text, response_translation,
        config['automation']['mode'], metrics,
    )


@app.callback(Output({"type": "modal", "name": MATCH}, "is_open"),
              Input({"type": "wise-man", "name": MATCH}, "n_clicks"), prevent_initial_call=True)
def open_node(_):
    return True


if __name__ == "__main__":
    try:
        app.run(host="127.0.0.1", port=8050, debug=False)
    finally:
        controller.cancel()
        controller.persist()
