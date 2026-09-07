"""Camada de acesso ao Supabase. Todas as funções de leitura/escrita do app passam por aqui."""
import streamlit as st
from supabase import create_client

DEFAULT_EMO_LABELS = [
    "Muito insatisfeito", "Insatisfeito", "Levemente insatisfeito", "Neutro",
    "Levemente satisfeito", "Satisfeito", "Muito satisfeito", "Encantado",
]

# Catálogo de técnicas disponíveis para adicionar ao roteiro de um projeto.
# "render" define como a técnica se comporta na sessão:
#   'emocards' -> escolha de emoção por tarefa (com tarefas cadastradas em ordem)
#   '3e'       -> balão de fala + nuvem de pensamento por tarefa (tarefas em ordem)
#   'notes'    -> anotação livre por tarefa (nome da tarefa digitado na hora)
TECHNIQUE_CATALOG = [
    {"key": "emocards", "name": "Emocards", "render": "emocards",
     "desc": "Cartões de emoção (escala de 8) escolhidos pelo participante em cada tarefa."},
    {"key": "3e", "name": "3E — Fala e Pensamento", "render": "3e",
     "desc": "Abre o template da técnica 3E (balão de fala, nuvem de pensamento e boneco para desenhar) no Miro."},
    {"key": "attrakdiff", "name": "AttrakDiff", "render": "attrakdiff",
     "desc": "Questionário AttrakDiff (qualidade pragmática, hedônica e atratividade), com escala de -3 a +3 por par de palavras."},
    {"key": "think_aloud", "name": "Pensar em voz alta", "render": "notes",
     "desc": "Registro livre do que o participante fala enquanto realiza a tarefa."},
    {"key": "five_sec", "name": "Teste dos 5 segundos", "render": "notes",
     "desc": "Primeiras impressões registradas logo após a exposição à tela."},
    {"key": "card_sorting", "name": "Card sorting", "render": "notes",
     "desc": "Registro de como o participante organizou os cartões em categorias."},
    {"key": "sus", "name": "Questionário SUS", "render": "notes",
     "desc": "Anotações e pontuação do questionário padronizado de usabilidade."},
    {"key": "journey_map", "name": "Mapa de jornada", "render": "notes",
     "desc": "Registro de etapas, ações e sentimentos ao longo da jornada."},
    {"key": "interview", "name": "Entrevista contextual", "render": "notes",
     "desc": "Perguntas e respostas registradas durante ou após o uso."},
]


def catalog_by_key(key):
    return next((c for c in TECHNIQUE_CATALOG if c["key"] == key), None)


@st.cache_resource
def get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def sb():
    return get_client()


# ---------------- projects ----------------
def list_projects():
    r = sb().table("projects").select("*").order("created_at").execute()
    return r.data


def get_project(project_id):
    r = sb().table("projects").select("*").eq("id", project_id).single().execute()
    return r.data


def create_project(name, description):
    r = sb().table("projects").insert({"name": name, "description": description}).execute()
    project = r.data[0]
    add_technique_from_catalog(project["id"], "emocards")
    return project


def update_project_script(project_id, script):
    sb().table("projects").update({"script": script}).eq("id", project_id).execute()


def delete_project(project_id):
    sb().table("projects").delete().eq("id", project_id).execute()


# ---------------- members ----------------
def list_members(project_id):
    r = sb().table("members").select("*").eq("project_id", project_id).execute()
    return r.data


def add_member(project_id, name, email):
    sb().table("members").insert({"project_id": project_id, "name": name, "email": email}).execute()


def remove_member(member_id):
    sb().table("members").delete().eq("id", member_id).execute()


# ---------------- techniques ----------------
def list_techniques(project_id):
    r = sb().table("techniques").select("*").eq("project_id", project_id).order("created_at").execute()
    return r.data


def add_technique_from_catalog(project_id, template_key):
    tpl = catalog_by_key(template_key)
    if not tpl:
        return
    payload = {
        "project_id": project_id, "name": tpl["name"], "type": tpl["render"],
        "template_key": tpl["key"],
    }
    if tpl["render"] == "emocards":
        payload["labels"] = DEFAULT_EMO_LABELS
    sb().table("techniques").insert(payload).execute()


def remove_technique(technique_id):
    sb().table("techniques").delete().eq("id", technique_id).execute()


def rename_technique(technique_id, name):
    sb().table("techniques").update({"name": name}).eq("id", technique_id).execute()


def update_emo_label(technique_id, labels):
    sb().table("techniques").update({"labels": labels}).eq("id", technique_id).execute()


# ---------------- technique tasks ----------------
def list_tasks(technique_id):
    r = sb().table("technique_tasks").select("*").eq("technique_id", technique_id).order("order_index").execute()
    return r.data


def add_task(technique_id, task_name):
    existing = list_tasks(technique_id)
    next_index = (max([t["order_index"] for t in existing]) + 1) if existing else 0
    sb().table("technique_tasks").insert({
        "technique_id": technique_id, "task_name": task_name, "order_index": next_index,
    }).execute()


def remove_task(task_id):
    sb().table("technique_tasks").delete().eq("id", task_id).execute()


# ---------------- tests (sessões) ----------------
def list_tests(project_id):
    r = sb().table("tests").select("*").eq("project_id", project_id).order("created_at", desc=True).execute()
    return r.data


def get_test(test_id):
    r = sb().table("tests").select("*").eq("id", test_id).single().execute()
    return r.data


def create_test(project_id, tester, co_testers, participant, test_datetime):
    r = sb().table("tests").insert({
        "project_id": project_id, "tester": tester, "co_testers": co_testers,
        "participant": participant, "test_datetime": test_datetime, "status": "ongoing",
    }).execute()
    return r.data[0]


def finish_test(test_id):
    sb().table("tests").update({"status": "done"}).eq("id", test_id).execute()


def delete_test(test_id):
    sb().table("tests").delete().eq("id", test_id).execute()


# ---------------- entries (registros) ----------------
def list_entries(test_id):
    r = sb().table("entries").select("*").eq("test_id", test_id).order("created_at").execute()
    return r.data


def list_entries_for_project(project_id):
    test_ids = [t["id"] for t in list_tests(project_id)]
    if not test_ids:
        return []
    r = sb().table("entries").select("*").in_("test_id", test_ids).execute()
    return r.data


def add_entry(test_id, technique_id, task_name, emotion=None, note=None, drawing=None):
    sb().table("entries").insert({
        "test_id": test_id, "technique_id": technique_id, "task_name": task_name,
        "emotion": emotion, "note": note, "drawing": drawing,
    }).execute()


def delete_entry(entry_id):
    sb().table("entries").delete().eq("id", entry_id).execute()


def set_single_answer(test_id, technique_id, task_name, emotion):
    """Garante um único registro por (teste, técnica, item) — apaga a resposta anterior
    para esse item, se houver, e grava a nova. Usado no AttrakDiff, onde cada item do
    questionário só pode ter uma resposta por sessão (o participante pode mudar de ideia
    e clicar em outro valor)."""
    sb().table("entries").delete().eq("test_id", test_id).eq("technique_id", technique_id).eq("task_name", task_name).execute()
    sb().table("entries").insert({
        "test_id": test_id, "technique_id": technique_id, "task_name": task_name, "emotion": emotion,
    }).execute()
