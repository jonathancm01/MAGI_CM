"""Local projects and independent, persistent MAGI conversations."""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
from uuid import uuid4, uuid5, NAMESPACE_URL

import ai
from harness import DEFAULT_AUTOMATION, Harness, NAMES, validate_config, write_json


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def identifier(value):
    return isinstance(value, str) and len(value) == 32 and all(c in "0123456789abcdef" for c in value)


class WorkspaceStore:
    def __init__(self, storage, defaults, runner=None):
        self.storage, self.defaults, self.runner = Path(storage), deepcopy(defaults), runner
        self.lock, self.engines, self.storage_error = RLock(), {}, ""
        self.path = self.storage / "workspaces.json"
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            self.validate_index()
        else:
            self.data = {"version": 1, "projects": {}, "chats": {}, "selected": None}
            self.import_tasks()
            self.commit(self.data)

    def validate_index(self):
        data = self.data
        if (not isinstance(data, dict) or data.get("version") != 1
                or not isinstance(data.get("projects"), dict) or not isinstance(data.get("chats"), dict)):
            raise ValueError("El índice de proyectos es inválido; se ha conservado sin sobrescribirlo.")
        for key, project in data["projects"].items():
            if (not identifier(key) or not isinstance(project, dict)
                    or not all(isinstance(project.get(field), str) for field in ("name", "path"))):
                raise ValueError("Proyecto guardado inválido.")
        trash = data.get("trash", {})
        if not isinstance(trash, dict) or data["chats"].keys() & trash.keys():
            raise ValueError("La papelera de chats es inválida.")
        for key, chat in (data["chats"] | trash).items():
            if (not identifier(key) or not isinstance(chat, dict) or chat.get("project_id") not in data["projects"]
                    or not all(isinstance(chat.get(field), str) for field in ("title", "draft", "updated"))
                    or not isinstance(chat.get("config"), dict)
                    or chat["config"].get("workspace") != data["projects"][chat["project_id"]]["path"]):
                raise ValueError("Chat guardado inválido.")
        if data.get("selected") not in data["chats"]:
            raise ValueError("La selección guardada no corresponde a un chat.")

    def commit(self, data):
        write_json(self.path, data)
        self.data = deepcopy(data)

    def import_tasks(self):
        # Keep the original task files untouched so migration is recoverable.
        for path in sorted((self.storage / "tasks").glob("*.json")):
            if not identifier(path.stem):
                continue
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                config = record["config"]
                if record["version"] != 1 or record["state"]["task_id"] != path.stem:
                    raise ValueError("Tarea antigua inválida.")
                project_id = self.add_project(config["workspace"], "", persist=False)
                self.data["chats"][path.stem] = {
                    "project_id": project_id, "title": record["state"]["task"][:80],
                    "draft": "", "config": config, "updated": record["updated"],
                }
                destination = self.storage / "chats" / path.stem
                if not (destination / f"{path.stem}.json").exists():
                    write_json(destination / f"{path.stem}.json", record)
                    write_json(destination / "current.json", {"task_id": path.stem})
            except (ValueError, KeyError, TypeError, OSError) as error:
                self.storage_error = f"No se pudo importar {path.name}: {error}. El original se ha conservado."
        pointer = self.storage / "tasks" / "current.json"
        if pointer.exists():
            try:
                previous = json.loads(pointer.read_text(encoding="utf-8")).get("task_id")
                if previous in self.data["chats"]:
                    self.data["selected"] = previous
            except (ValueError, TypeError, OSError):
                self.storage_error = "No se pudo recuperar la selección anterior; las tareas se han conservado."
        if not self.data["selected"]:
            self.new_chat(persist=False)

    def add_project(self, folder, name="", *, persist=True):
        config = deepcopy(self.defaults)
        config["workspace"] = folder
        config = validate_config(config)
        path = config["workspace"]
        project_id = uuid5(NAMESPACE_URL, str(Path(path)).casefold()).hex
        if not isinstance(name, str) or len(name.strip()) > 80:
            raise ValueError("El nombre del proyecto debe tener como máximo 80 caracteres.")
        with self.lock:
            if project_id not in self.data["projects"]:
                data = deepcopy(self.data)
                data["projects"][project_id] = {"name": name.strip() or Path(path).name or path, "path": path}
                if persist:
                    self.commit(data)
                else:
                    self.data = data
            return project_id

    def new_chat(self, project_id=None, *, source=None, persist=True):
        with self.lock:
            if project_id is not None and project_id not in self.data["projects"]:
                raise ValueError("El proyecto ya no está disponible.")
            data = deepcopy(self.data)
            config = self.chat(source)["config"] if source else deepcopy(self.defaults)
            chat_id = uuid4().hex
            created = None
            if project_id is None:
                root = self.storage.parent.resolve()
                folder = root / "projects" / f"chat-{chat_id}"
                if not folder.resolve().is_relative_to(root):
                    raise ValueError("La carpeta automática debe permanecer dentro de MAGI.")
                folder.parent.mkdir(parents=True, exist_ok=True)
                folder.mkdir()
                created = folder
                path = str(folder.resolve())
                project_id = uuid5(NAMESPACE_URL, path.casefold()).hex
                data["projects"][project_id] = {"name": f"Chat {chat_id[:8]}", "path": path}
            siblings = [chat for chat in data["chats"].values() if chat["project_id"] == project_id]
            if siblings:
                config = deepcopy(max(siblings, key=lambda chat: chat["updated"])["config"])
            config["workspace"] = data["projects"][project_id]["path"]
            data["chats"][chat_id] = {"project_id": project_id, "title": "Nuevo chat", "draft": "",
                                      "config": config, "updated": now()}
            data["selected"] = chat_id
            if persist:
                try:
                    self.commit(data)
                except OSError:
                    if created is not None:
                        try:
                            created.rmdir()
                        except OSError:
                            pass
                    raise
            else:
                self.data = data
            return chat_id

    def chat(self, chat_id):
        with self.lock:
            if not identifier(chat_id) or chat_id not in self.data["chats"]:
                raise ValueError("Este chat no existe. Selecciona uno en la barra lateral.")
            chat = deepcopy(self.data["chats"][chat_id])
            chat["config"].setdefault("automation", deepcopy(DEFAULT_AUTOMATION))
            return chat

    def delete_chat(self, chat_id):
        with self.lock:
            chat = self.chat(chat_id)
            if chat_id in self.engines and self.engines[chat_id].snapshot()["busy"]:
                raise ValueError("No puedes eliminar un chat trabajando. Espera a que termine o cancela su operación.")
            data = deepcopy(self.data)
            data.setdefault("trash", {})[chat_id] = data["chats"].pop(chat_id)
            if not data["chats"]:
                replacement = uuid4().hex
                data["chats"][replacement] = {**deepcopy(chat), "title": "Nuevo chat", "draft": "", "updated": now()}
            if data["selected"] == chat_id:
                data["selected"] = max(data["chats"], key=lambda key: data["chats"][key]["updated"])
            self.commit(data)
            self.engines.pop(chat_id, None)

    def restore_chat(self, chat_id):
        with self.lock:
            if not identifier(chat_id) or chat_id not in self.data.get("trash", {}):
                raise ValueError("Este chat ya no está en la papelera.")
            data = deepcopy(self.data)
            data["chats"][chat_id] = data["trash"].pop(chat_id)
            data["selected"] = chat_id
            self.commit(data)

    def engine(self, chat_id):
        with self.lock:
            self.chat(chat_id)
            if chat_id not in self.engines:
                options = {"runner": self.runner} if self.runner is not None else {}
                engine = Harness(storage=self.storage / "chats" / chat_id, **options)
                if not engine.state["task_id"]:
                    engine.state["id"] = uuid4().hex
                    for answer in engine.state["answers"].values():
                        answer["id"] = engine.state["id"]
                self.engines[chat_id] = engine
            return self.engines[chat_id]

    def select(self, chat_id, previous=None, draft=None):
        with self.lock:
            self.chat(chat_id)
            engine = self.engine(chat_id)
            if engine.storage_error:
                raise ValueError(engine.storage_error)
            data = deepcopy(self.data)
            if previous in data["chats"] and isinstance(draft, str):
                data["chats"][previous]["draft"] = draft[:16000]
            data["selected"] = chat_id
            self.commit(data)
            return self.chat(chat_id)

    def save_draft(self, chat_id, draft):
        if not isinstance(draft, str) or len(draft) > 16000:
            raise ValueError("El borrador supera el límite de 16000 caracteres.")
        with self.lock:
            chat = self.chat(chat_id)
            if chat["draft"] != draft:
                data = deepcopy(self.data)
                data["chats"][chat_id]["draft"] = draft
                self.commit(data)

    def busy(self):
        with self.lock:
            return any(engine.snapshot()["busy"] for engine in self.engines.values())

    def perform(self, chat_id, run_id, action, task, config, *, request_mode=None, title=None, project_name=None):
        with self.lock:
            chat, engine = self.chat(chat_id), self.engine(chat_id)
            state = engine.snapshot()
            if run_id != state["id"]:
                raise ValueError("El chat cambió en otra vista. Espera a que se actualice antes de enviar.")
            if action == "cancel":
                engine.cancel()
                return
            clean = validate_config(config)
            if clean["workspace"] != self.data["projects"][chat["project_id"]]["path"]:
                raise ValueError("La carpeta pertenece al proyecto. Añade otro proyecto para cambiarla.")
            for name in NAMES:
                node = clean["nodes"][name]
                ai.validate_model(node["provider"], node["model"])
            if state["busy"] or (action != "save" and self.busy()):
                raise ValueError("Hay un chat trabajando. Espera o cancela su operación antes de iniciar otra.")
            data = deepcopy(self.data)
            data["chats"][chat_id].update(config=clean, updated=now())
            if action == 'save':
                for label, value, target, key in (
                    ('chat', title, data['chats'][chat_id], 'title'),
                    ('proyecto', project_name, data['projects'][chat['project_id']], 'name'),
                ):
                    if value is not None:
                        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 80 or not value.strip().isprintable():
                            raise ValueError(f'El nombre del {label} debe tener entre 1 y 80 caracteres, en una sola línea.')
                        target[key] = value.strip()
            if action == "start":
                if not isinstance(task, str) or not task.strip() or len(task) > 16000:
                    raise ValueError("Escribe una solicitud de entre 1 y 16000 caracteres.")
                nodes = clean['nodes'].values() if request_mode is None else [clean['nodes'][clean['executor']]]
                for node in nodes:
                    ai.command_for(node)
                data["chats"][chat_id]["draft"] = task
                if chat['title'] == 'Nuevo chat' and not state["task_id"] and not state.get('dialogue'):
                    data["chats"][chat_id]["title"] = task.strip().splitlines()[0][:80]
            self.commit(data)
            if action == "save":
                return
            if action == "start":
                if request_mode is not None:
                    engine.submit(task, clean, run_id, request_mode)
                elif state["task_id"]:
                    engine.continue_task(run_id, task, clean)
                else:
                    engine.start(task, clean)
                self.save_draft(chat_id, "")
            elif action == "execute":
                if task and task.strip():
                    raise ValueError("Envía primero tu nueva instrucción o vacía el borrador antes de ejecutar el plan anterior.")
                engine.execute(run_id, state["request"], clean)
            elif action == "review":
                engine.review_again(run_id, clean)
            else:
                raise ValueError("Acción desconocida.")

    def navigation(self):
        with self.lock:
            data = deepcopy(self.data)
            for key, chat in data["chats"].items():
                chat["busy"] = key in self.engines and self.engines[key].snapshot()["busy"]
            return data

    def cancel(self):
        with self.lock:
            for engine in self.engines.values():
                engine.cancel()

    def persist(self):
        with self.lock:
            for engine in self.engines.values():
                engine.persist()
