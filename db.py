"""Camada de acesso ao Supabase. Todas as funções de leitura/escrita do app passam por aqui."""
import streamlit as st
from supabase import create_client

DEFAULT_EMO_LABELS = [
    "Muito insatisfeito", "Insatisfeito", "Levemente insatisfeito", "Neutro",
    "Levemente satisfeito", "Satisfeito", "Muito satisfeito", "Encantado",
]


@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    return create_client(url, key)


def sb():
    return get_client()


# ---------------- projects ----------------
from postgrest.exceptions import APIError

def list_projects():
    try:
        r = (
            sb()
            .table("projects")
            .select("*")
            .order("created_at")
            .execute()
        )
        return r.data

    except APIError as e:
        st.write("Código:", e.code)
        st.write("Mensagem:", e.message)
        st.write("Detalhes:", e.details)
        st.write("Hint:", e.hint)
        return []


def get_project(project_id):
    r = sb().table("projects").select("*").eq("id", project_id).single().execute()
    return r.data


def create_project(name, description):
    r = sb().table("projects").insert({"name": name, "description": description}).execute()
    project = r.data[0]
    sb().table("techniques").insert({
        "project_id": project["id"], "name": "Emocards", "type": "emocards",
        "labels": DEFAULT_EMO_LABELS,
    }).execute()
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


def add_technique(project_id, name, ttype):
    payload = {"project_id": project_id, "name": name, "type": ttype}
    if ttype == "emocards":
        payload["labels"] = DEFAULT_EMO_LABELS
    sb().table("techniques").insert(payload).execute()


def remove_technique(technique_id):
    sb().table("techniques").delete().eq("id", technique_id).execute()


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


def add_entry(test_id, technique_id, task_name, emotion=None, note=None):
    sb().table("entries").insert({
        "test_id": test_id, "technique_id": technique_id, "task_name": task_name,
        "emotion": emotion, "note": note,
    }).execute()


def delete_entry(entry_id):
    sb().table("entries").delete().eq("id", entry_id).execute()
