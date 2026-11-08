"""Readable, escaped message blocks shared by the conversation and nucleus dialogs."""

from copy import deepcopy
import re

import ai
from harness import parse_vote

LABELS = {"yes": "Aprobado", "no": "Objeción", "conditional": "Con condiciones", "info": "Aporte", "error": "Error"}

# Left and right headers form one phrase; the status box has its own caption.
COUNCIL_CAPTIONS = {
    "idle": ("指示", "待機中", "En espera de instrucciones", "待機", "En espera"),
    "question": ("質問", "回答中", "Respondiendo una pregunta", "応答中", "Respondiendo"),
    "answered": ("質問", "回答済", "Pregunta respondida", "回答済", "Respondido"),
    "prepared": ("変更", "準備済", "Cambio preparado", "実行待機", "Esperando ejecución"),
    "receiving": ("申請", "受付中", "Recibiendo una solicitud", "受信中", "Recibiendo"),
    "analysis": ("要求", "解析中", "Analizando la solicitud", "処理中", "Procesando"),
    "planning": ("計画", "作成中", "Elaborando el plan", "計画中", "Planificando"),
    "debate": ("提案", "審議中", "Deliberando propuestas", "検討中", "Evaluando"),
    "voting": ("投票", "受付中", "Recibiendo votos", "集計中", "Contando votos"),
    "consensus": ("合意", "形成中", "Construyendo acuerdo", "協議中", "En deliberación"),
    "ready": ("計画", "承認済", "Plan aprobado", "実行待機", "Esperando ejecución"),
    "conditions": ("条件", "確認中", "Revisando condiciones", "要修正", "Requiere correcciones"),
    "teamwork": ("共同", "作業中", "Trabajando en conjunto", "連携中", "Colaborando"),
    "communication": ("情報", "共有中", "Compartiendo información", "通信中", "Comunicando"),
    "review": ("結果", "検証中", "Verificando el resultado", "確認中", "Comprobando"),
    "repair": ("不具合", "修正中", "Corrigiendo fallos", "修復中", "Reparando"),
    "retry": ("処理", "再試行中", "Reintentando el procesamiento", "復旧中", "Restableciendo el funcionamiento"),
    "error": ("異常", "検出", "Anomalía detectada", "要確認", "Requiere revisión"),
    "interrupted": ("作業", "中断", "Trabajo interrumpido", "停止中", "Detenido"),
    "limit": ("上限", "到達", "Límite alcanzado", "一時停止", "En pausa"),
    "done": ("任務", "完了", "Misión completada", "解決済", "Resuelto"),
}


def council_caption(state):
    if state.get('query_busy'):
        return COUNCIL_CAPTIONS['question']
    if state['phase'] == 'ready' and state.get('workflow') == 'direct':
        return COUNCIL_CAPTIONS['prepared']
    if not state['task_id'] and state.get('dialogue'):
        status = state['dialogue'][-1]['status']
        return COUNCIL_CAPTIONS['answered' if status == 'answer' else 'error' if status == 'error' else 'interrupted']
    phase, usage = state["phase"], state["usage"]
    answers = state["answers"].values()
    if state["busy"] and any(answer.get("activity") == "Reintentando" for answer in answers):
        key = "retry"
    elif phase == "analysis":
        finished = any(answer["id"] == state["id"] for answer in answers)
        key = ("debate" if usage["cycle"] > 1 else "receiving" if not usage["calls"]
               else "planning" if finished else "analysis")
    elif phase == "voting":
        votes = sum(answer["id"] == state["id"] and answer.get("activity") == "Voto compartido" for answer in answers)
        key = "consensus" if votes >= 2 else "voting"
    elif phase == "execution":
        key = "repair" if usage["repairs"] else "communication" if state["execution_report"] else "teamwork"
    else:
        key = {"blocked": "conditions", "changes_requested": "conditions", "cancelled": "interrupted",
               "restored": "idle"}.get(phase, phase)
    return COUNCIL_CAPTIONS.get(key, COUNCIL_CAPTIONS["idle"])


def text_blocks(text):
    blocks = []
    for index, part in enumerate(re.split(r"```[^\n]*\n([\s\S]*?)```", text)):
        if index % 2:
            blocks.append({"type": "code", "text": part.rstrip()})
            continue
        paragraph = []
        def flush():
            if paragraph:
                blocks.append({"type": "paragraph", "text": "\n".join(paragraph)})
                paragraph.clear()
        for line in part.splitlines():
            heading = re.match(r"^#{1,6}\s+(.+)$", line)
            item = re.match(r"^\s*(?:[-*]|\d+[.)])\s+(.+)$", line)
            if line.strip().startswith('|') and line.strip().endswith('|'):
                flush()
                cells = [cell.strip() for cell in line.strip()[1:-1].split('|')]
                if all(re.fullmatch(r':?-+:?', cell) for cell in cells):
                    continue
                if not blocks or blocks[-1]['type'] != 'table':
                    blocks.append({'type': 'table', 'headers': cells, 'rows': []})
                else:
                    blocks[-1]['rows'].append(cells)
            elif re.fullmatch(r'\s*([-*_])\1{2,}\s*', line):
                flush()
                blocks.append({'type': 'divider'})
            elif not line.strip() or heading or item:
                flush()
                if heading:
                    blocks.append({"type": "heading", "text": heading[1]})
                elif item:
                    if not blocks or blocks[-1]["type"] != "list":
                        blocks.append({"type": "list", "items": []})
                    blocks[-1]["items"].append(item[1])
            else:
                paragraph.append(line)
        flush()
    return blocks


def readable_entry(entry):
    result = deepcopy(entry)
    text = str(entry.get("text", ""))
    try:
        vote = parse_vote(text)
    except ValueError:
        pass
    else:
        result.update(status=vote["status"], raw=text)
        text = vote["conditions"]
    if result.get("status") == "error":
        result["error_info"] = entry.get("error_info") or ai.error_info(text)
        text = result["error_info"]["title"]
    result.update(text=text, blocks=text_blocks(text), label=LABELS.get(result.get("status"), "Mensaje"))
    return result


def readable_answer(answer, messages):
    result = deepcopy(answer)
    result["history"] = [readable_entry(entry) for entry in answer["history"]]
    result["messages"] = [readable_entry(entry) for entry in messages]
    if answer.get("error"):
        result["error_info"] = answer.get("error_info") or ai.error_info(answer["error"])
    return result
