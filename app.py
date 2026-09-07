"""Campo — testes de usabilidade (versão Streamlit + Supabase, multi-usuário).

Rode com: streamlit run app.py
Precisa de SUPABASE_URL e SUPABASE_KEY em st.secrets (veja README.md).
"""
import base64
from datetime import datetime

import pandas as pd
import streamlit as st

import db
from charts import (
    make_bar_chart, emo_counts_from_entries, emo_counts_by_task, legend_caption,
    FACE_EMOJI, ATTRAKDIFF_ITEMS, ATTRAK_COLOR, ATTRAK_COLOR_DARK,
    attrakdiff_item_key, attrakdiff_scores_from_entries, make_attrakdiff_chart,
)
from pdf_export import build_project_pdf

st.set_page_config(page_title="Campo — testes de usabilidade", layout="wide")

# Template da técnica 3E no Miro (balão de fala, nuvem de pensamento e boneco para desenhar).
THREE_E_MIRO_LINK = (
    "https://miro.com/welcomeonboard/"
    "RXhNMkp1ZWh5aVpaK0VNSDhRM1NEbDFlaDhYenBKWFVacG9wZFdpTHhZdjR2dGIxTTBPLzJBcjJHZXhjS3JXWm9O"
    "VGV3N1JGd0Y5S2ZsUTlrM2RSUXZpTTZHU1pLdkd5dSthd2NMQjRFZmpJeGZ0ay9kWlZIc1ZzcG16NXlpTEZnbHpz"
    "a3F6REdEcmNpNEFOMmJXWXBBPT0hdjE=?share_link_id=769349062550"
)


# ============================= navegação (sobrevive a reload / novo facilitador) =============================
def _qp_get(key, default=""):
    return st.query_params.get(key, default)


def goto(view=None, pid=None, tid=None, tab=None):
    if view is not None:
        st.query_params["view"] = view
    if pid is not None:
        st.query_params["pid"] = pid
    if tid is not None:
        st.query_params["tid"] = tid
    if tab is not None:
        st.query_params["tab"] = tab
    st.rerun()


view = _qp_get("view", "home")
current_pid = _qp_get("pid", "")
current_tid = _qp_get("tid", "")
current_tab = _qp_get("tab", "overview")


# ============================= diálogo de confirmação de emoção =============================
@st.dialog("Confirmar emoção")
def confirm_emotion_dialog(emotion, label, task_name, technique_id, test_id, pointer_key):
    st.write(f"Tarefa: **{task_name}**")
    st.markdown(f"Registrar a emoção **{emotion} — {label}** para esta tarefa?")
    c1, c2 = st.columns(2)
    if c1.button("Cancelar", use_container_width=True):
        st.rerun()
    if c2.button("Confirmar", type="primary", use_container_width=True):
        db.add_entry(test_id, technique_id, task_name, emotion=emotion)
        # Avança direto para a próxima tarefa — não é mais necessário clicar em "Seguir".
        st.session_state[pointer_key] = st.session_state.get(pointer_key, 0) + 1
        st.rerun()


# ============================= sidebar =============================
with st.sidebar:
    st.markdown("## Campo")
    st.caption("Sessões de teste de usabilidade")

    with st.expander("+ Novo projeto"):
        new_name = st.text_input("Nome do projeto", key="new_proj_name")
        new_desc = st.text_area("Descrição", key="new_proj_desc")
        if st.button("Criar projeto"):
            if new_name.strip():
                project = db.create_project(new_name.strip(), new_desc.strip())
                goto(view="project", pid=project["id"], tab="overview")
            else:
                st.warning("Dê um nome ao projeto.")

    st.divider()
    projects = db.list_projects()
    if not projects:
        st.caption("Nenhum projeto ainda.")
    for p in projects:
        active = p["id"] == current_pid
        c1, c2 = st.columns([5, 1])
        if c1.button(("• " if active else "") + p["name"], key=f"proj_{p['id']}", use_container_width=True):
            goto(view="project", pid=p["id"], tab="overview")
        with c2.popover("🗑️"):
            st.write(f"Excluir **{p['name']}**? Essa ação não pode ser desfeita.")
            if st.button("Confirmar exclusão", key=f"del_proj_side_{p['id']}", type="primary"):
                db.delete_project(p["id"])
                if active:
                    st.query_params.clear()
                st.rerun()


# ============================= tela inicial =============================
if not current_pid or view == "home":
    st.title("Bem-vindo(a) ao Campo")
    st.write("Crie um projeto na barra lateral para começar a registrar sessões de teste de usabilidade.")
    st.info("Este app é compartilhado: qualquer facilitador com o link acessa o mesmo projeto e os mesmos dados, mesmo depois de fechar a aba.")
    st.stop()

project = db.get_project(current_pid)
if not project:
    st.error("Projeto não encontrado.")
    st.stop()

techniques = db.list_techniques(current_pid)
for t in techniques:
    t["tasks"] = db.list_tasks(t["id"])


# ============================= tela: runner (rodando uma sessão) =============================
def render_runner():
    test = db.get_test(current_tid)
    if not test:
        goto(view="project", tab="tests")
        return

    st.title(f"Sessão com {test['participant']}")
    co = f" · com {test['co_testers']}" if test.get("co_testers") else ""
    st.caption(f"Facilitador: {test['tester']}{co} · {test.get('test_datetime','')}")

    if st.button("Finalizar teste", type="primary"):
        db.finish_test(test["id"])
        goto(view="result", tid=test["id"])
        return

    tech_names = {t["id"]: t["name"] for t in techniques}
    tech_id = st.selectbox(
        "Técnica", options=list(tech_names.keys()),
        format_func=lambda tid: tech_names[tid],
        key=f"runner_tech_{test['id']}",
    )
    active_tech = next(t for t in techniques if t["id"] == tech_id)
    entries = db.list_entries(test["id"])

    st.divider()

    if active_tech["type"] == "emocards":
        tasks = [t["task_name"] for t in active_tech["tasks"]]
        if not tasks:
            st.warning("Essa técnica ainda não tem tarefas cadastradas. Adicione as tarefas, na ordem em que serão testadas, na aba **Roteiro & técnicas**.")
        else:
            pointer_key = f"pointer_{test['id']}_{tech_id}"
            if pointer_key not in st.session_state:
                # Ao (re)abrir a sessão, pula direto para a primeira tarefa ainda sem
                # resposta — não é mais necessário clicar em "Seguir" para chegar lá.
                answered_tasks = {
                    e["task_name"] for e in entries if e["technique_id"] == tech_id
                }
                idx0 = 0
                while idx0 < len(tasks) and tasks[idx0] in answered_tasks:
                    idx0 += 1
                st.session_state[pointer_key] = idx0
            idx = st.session_state[pointer_key]

            if idx >= len(tasks):
                st.success("Todas as tarefas desta técnica já foram testadas nesta sessão.")
            else:
                current_task = tasks[idx]
                st.caption(f"Tarefa {idx + 1} de {len(tasks)}")
                st.markdown(
                    f"<div style='display:inline-block;background:#fff;border:1px solid #DCE3E7;"
                    f"border-radius:14px;padding:12px 18px;font-size:18px;font-weight:600;'>{current_task}</div>",
                    unsafe_allow_html=True,
                )
                st.write("")
                labels = active_tech["labels"]
                cols = st.columns(4)
                for i, lbl in enumerate(labels):
                    with cols[i % 4]:
                        if st.button(f"{FACE_EMOJI[i]}\n\n{i+1}. {lbl}", key=f"emo_{i}_{current_task}", use_container_width=True):
                            confirm_emotion_dialog(i + 1, lbl, current_task, tech_id, test["id"], pointer_key)
    elif active_tech["type"] == "3e":
        st.caption("Técnica 3E")
        st.write(
            "Peça ao participante para escrever seus comentários no balão de fala, seus "
            "pensamentos na nuvem de pensamento, e para desenhar na cabeça do boneco um rosto "
            "ou objetos que representem sua emoção ou experiência — tudo direto no template do Miro."
        )
        st.link_button("🔗 Abrir template 3E no Miro", THREE_E_MIRO_LINK, use_container_width=True)
    elif active_tech["type"] == "attrakdiff":
        answers_map = {
            e["task_name"]: e["emotion"]
            for e in entries
            if e["technique_id"] == tech_id and e.get("emotion") is not None
        }
        st.caption(f"AttrakDiff — {len(answers_map)} de {len(ATTRAKDIFF_ITEMS)} respondidas")

        box_key = f"attrakdiff_box_{tech_id}"
        st.markdown(
            f"""
            <style>
            .st-key-{box_key} div[data-testid="stHorizontalBlock"]:first-of-type {{
                position: sticky;
                top: 0;
                z-index: 999;
                background: #FFFFFF;
                padding-top: 6px;
                padding-bottom: 6px;
                border-bottom: 1px solid #E4E4E4;
            }}
            .st-key-{box_key} button[kind="primary"] {{
                background-color: {ATTRAK_COLOR} !important;
                border-color: {ATTRAK_COLOR} !important;
                color: #FFFFFF !important;
            }}
            .st-key-{box_key} button[kind="primary"]:hover {{
                background-color: {ATTRAK_COLOR_DARK} !important;
                border-color: {ATTRAK_COLOR_DARK} !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

        col_ratio = [3.4] + [1] * 7
        with st.container(height=560, border=True, key=box_key):
            header_cols = st.columns(col_ratio)
            header_cols[0].write("")
            for i, n in enumerate(range(-3, 4)):
                header_cols[i + 1].markdown(
                    f"<div style='text-align:center;font-weight:700;color:{ATTRAK_COLOR};'>{n}</div>",
                    unsafe_allow_html=True,
                )

            for group, left, right in ATTRAKDIFF_ITEMS:
                item_key = attrakdiff_item_key(left, right)
                current_val = answers_map.get(item_key)
                row_cols = st.columns(col_ratio)
                row_cols[0].markdown(
                    f"<div style='font-size:13px;line-height:1.3;padding-top:6px;'>"
                    f"<b>{left}</b><br><span style='color:#888;'>{right}</span></div>",
                    unsafe_allow_html=True,
                )
                for i, n in enumerate(range(-3, 4)):
                    selected = current_val == n
                    if row_cols[i + 1].button(
                        str(n), key=f"ad_{tech_id}_{item_key}_{n}",
                        type="primary" if selected else "secondary",
                        use_container_width=True,
                    ):
                        db.set_single_answer(test["id"], tech_id, item_key, n)
                        st.rerun()
    else:
        task_name = st.text_input("Nome da tarefa", key=f"notes_task_{test['id']}")
        note = st.text_area("Anotação — o que o participante disse ou fez?", key=f"notes_note_{test['id']}")
        if st.button("Salvar registro"):
            if not task_name.strip():
                st.warning("Digite o nome da tarefa.")
            elif not note.strip():
                st.warning("Escreva uma anotação.")
            else:
                db.add_entry(test["id"], tech_id, task_name.strip(), note=note.strip())
                st.rerun()

    st.divider()
    st.subheader(f"Registros desta sessão ({len(entries)})")
    if not entries:
        st.caption("Nenhum registro ainda.")
    else:
        for e in entries:
            tech = next((t for t in techniques if t["id"] == e["technique_id"]), None)
            detail = tech["labels"][e["emotion"] - 1] if (tech and tech["type"] == "emocards" and e.get("emotion")) else (e.get("note") or "")
            c1, c2 = st.columns([5, 1])
            c1.write(f"**{e['task_name']}** — {detail}")
            if e.get("drawing"):
                c1.image(base64.b64decode(e["drawing"]), width=140)
            if c2.button("remover", key=f"del_{e['id']}"):
                db.delete_entry(e["id"])
                st.rerun()

        df = pd.DataFrame(entries)[["task_name", "technique_id", "emotion", "note", "created_at"]]
        st.download_button(
            "Baixar .csv desta sessão", df.to_csv(index=False).encode("utf-8"),
            file_name=f"sessao_{test['participant']}.csv", mime="text/csv",
        )

    if st.button("← Voltar aos testes"):
        goto(view="project", tab="tests")


# ============================= tela: resultado individual (agregado, sem dividir por tarefa) =============================
def render_result():
    test = db.get_test(current_tid)
    if not test:
        goto(view="project", tab="tests")
        return

    c1, c2 = st.columns([4, 1])
    with c1:
        st.title(f"Resultado — {test['participant']}")
        st.caption(f"Facilitador: {test['tester']} · {test.get('test_datetime','')}")
    with c2:
        if st.button("← Voltar aos testes"):
            goto(view="project", tab="tests")
        if st.button("Excluir sessão"):
            db.delete_test(test["id"])
            goto(view="project", tab="tests")

    entries = db.list_entries(test["id"])
    emo_techs = [t for t in techniques if t["type"] == "emocards"]
    attrak_techs = [t for t in techniques if t["type"] == "attrakdiff"]
    any_chart = False
    for tech in emo_techs:
        counts = emo_counts_from_entries(entries, tech["id"])
        if sum(counts) > 0:
            any_chart = True
            st.subheader(tech["name"])
            fig = make_bar_chart(f"Emoções gerais — {test['participant']}", tech["labels"], counts)
            st.pyplot(fig, use_container_width=False)
            st.caption(legend_caption(tech["labels"]))
    for tech in attrak_techs:
        scores = attrakdiff_scores_from_entries(entries, tech["id"])
        if scores:
            any_chart = True
            st.subheader(tech["name"])
            fig = make_attrakdiff_chart(scores, title=f"AttrakDiff — {test['participant']}", color=ATTRAK_COLOR)
            st.pyplot(fig, use_container_width=False)
    if not any_chart:
        st.caption("Sem dados de emocards ou AttrakDiff para gerar gráfico nesta sessão.")

    # O relatório da sessão mostra apenas os resultados de Emocards e AttrakDiff.
    report_tech_ids = {t["id"] for t in emo_techs + attrak_techs}
    report_entries = [e for e in entries if e["technique_id"] in report_tech_ids]

    st.subheader("Todos os registros")
    if not report_entries:
        st.caption("Nenhum registro de Emocards ou AttrakDiff nessa sessão.")
    else:
        for e in report_entries:
            tech = next((t for t in techniques if t["id"] == e["technique_id"]), None)
            if tech and tech["type"] == "emocards" and e.get("emotion"):
                detail = tech["labels"][e["emotion"] - 1]
            elif tech and tech["type"] == "attrakdiff" and e.get("emotion") is not None:
                detail = f"{e['emotion']:+d}"
            else:
                detail = e.get("note") or ""
            st.write(f"**{e['task_name']}** — {tech['name'] if tech else ''}: {detail}")

        df = pd.DataFrame(report_entries)[["task_name", "technique_id", "emotion", "note", "created_at"]]
        st.download_button(
            "Baixar .csv desta sessão", df.to_csv(index=False).encode("utf-8"),
            file_name=f"resultado_{test['participant']}.csv", mime="text/csv",
        )


# ============================= tela: projeto (abas) =============================
def render_project():
    st.title(project["name"])
    if project.get("description"):
        st.caption(project["description"])

    tab_labels = ["Visão geral", "Membros", "Roteiro & técnicas", "Testes", "Relatório"]
    tab_keys = ["overview", "members", "script", "tests", "report"]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        st.write(project.get("description") or "_Sem descrição._")
        if st.button("Excluir projeto", type="secondary"):
            db.delete_project(project["id"])
            st.query_params.clear()
            st.rerun()

    with tabs[1]:
        members = db.list_members(project["id"])
        for m in members:
            c1, c2 = st.columns([5, 1])
            c1.write(f"**{m['name']}** — {m.get('email','')}")
            if c2.button("remover", key=f"rm_member_{m['id']}"):
                db.remove_member(m["id"])
                st.rerun()
        st.divider()
        with st.form(key="add_member_form", clear_on_submit=True):
            mn = st.text_input("Nome", key="member_name")
            me = st.text_input("E-mail", key="member_email")
            submitted_member = st.form_submit_button("Adicionar membro")
            if submitted_member:
                if mn.strip():
                    db.add_member(project["id"], mn.strip(), me.strip())
                    st.rerun()
                else:
                    st.warning("Dê um nome ao membro.")

    with tabs[2]:
        st.text_area(
            "Roteiro do teste", value=project.get("script", ""), key="script_text", height=160,
        )
        if st.button("Salvar roteiro"):
            db.update_project_script(project["id"], st.session_state["script_text"])
            st.success("Roteiro salvo")

        st.divider()
        st.markdown("### Técnicas")
        for tech in techniques:
            with st.expander(f"{tech['name']} ({tech['type']})", expanded=False):
                new_name = st.text_input("Nome desta técnica no projeto", value=tech["name"], key=f"name_{tech['id']}")
                if new_name != tech["name"] and st.button("Salvar nome", key=f"save_name_{tech['id']}"):
                    db.rename_technique(tech["id"], new_name)
                    st.rerun()

                if tech["type"] == "emocards":
                    labels = list(tech["labels"])
                    changed = False
                    for i in range(8):
                        new_lbl = st.text_input(f"Rótulo {i+1}", value=labels[i], key=f"lbl_{tech['id']}_{i}")
                        if new_lbl != labels[i]:
                            labels[i] = new_lbl
                            changed = True
                    if changed and st.button("Salvar rótulos", key=f"save_lbl_{tech['id']}"):
                        db.update_emo_label(tech["id"], labels)
                        st.rerun()

                if tech["type"] == "emocards":
                    st.markdown("**Tarefas (na ordem em que serão testadas)**")
                    for i, task in enumerate(tech["tasks"]):
                        c1, c2 = st.columns([5, 1])
                        c1.write(f"{i+1}. {task['task_name']}")
                        if c2.button("remover", key=f"rm_task_{task['id']}"):
                            db.remove_task(task["id"])
                            st.rerun()
                    with st.form(key=f"add_task_form_{tech['id']}", clear_on_submit=True):
                        new_task = st.text_input("Nova tarefa", key=f"new_task_{tech['id']}")
                        submitted_task = st.form_submit_button("Adicionar tarefa")
                        if submitted_task and new_task.strip():
                            db.add_task(tech["id"], new_task.strip())
                            st.rerun()
                elif tech["type"] == "3e":
                    st.caption(
                        "Técnica 3E: não é necessário cadastrar tarefas nem registrar nada aqui. "
                        "Durante a sessão, o app mostra um link que abre o template pronto no Miro."
                    )
                elif tech["type"] == "attrakdiff":
                    st.caption(
                        "AttrakDiff: os 18 pares de palavras do questionário são fixos e não podem ser "
                        "editados aqui. Durante a sessão, o app mostra o questionário completo, com "
                        "escala de -3 a +3 por item."
                    )

                if st.button("Excluir técnica", key=f"rm_tech_{tech['id']}"):
                    db.remove_technique(tech["id"])
                    st.rerun()

        st.divider()
        st.markdown("### Adicionar técnica ao roteiro")
        added_keys = {t.get("template_key") for t in techniques}
        available = [c for c in db.TECHNIQUE_CATALOG if c["key"] not in added_keys]
        if not available:
            st.caption("Todas as técnicas do catálogo já foram adicionadas.")
        for c in available:
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{c['name']}**  \n{c['desc']}")
            if c2.button("+ Adicionar", key=f"add_cat_{c['key']}"):
                db.add_technique_from_catalog(project["id"], c["key"])
                st.rerun()

    with tabs[3]:
        if st.button("+ Nova sessão de teste"):
            st.session_state["show_new_test"] = True
        if st.session_state.get("show_new_test"):
            with st.form("new_test_form"):
                tester = st.text_input("Seu nome (quem conduz o teste)")
                co_testers = st.text_input("Outros testadores (opcional, separados por vírgula)")
                participant = st.text_input("Nome de quem está sendo testado")
                dt = st.text_input("Data e hora", value=datetime.now().strftime("%Y-%m-%d %H:%M"))
                submitted = st.form_submit_button("Iniciar teste")
                if submitted:
                    if tester.strip() and participant.strip():
                        test = db.create_test(project["id"], tester.strip(), co_testers.strip(), participant.strip(), dt)
                        st.session_state["show_new_test"] = False
                        goto(view="runner", tid=test["id"])
                    else:
                        st.warning("Preencha seu nome e o do participante.")

        st.divider()
        tests = db.list_tests(project["id"])
        if not tests:
            st.caption("Nenhuma sessão registrada ainda.")
        for t in tests:
            n_entries = len(db.list_entries(t["id"]))
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.write(f"**{t['participant']}** testado por {t['tester']} · {t.get('test_datetime','')} · {n_entries} registro(s)")
            c2.write("🟡 em andamento" if t["status"] == "ongoing" else "🟢 concluído")
            if c3.button("Abrir", key=f"open_test_{t['id']}"):
                goto(view="runner" if t["status"] == "ongoing" else "result", tid=t["id"])

    with tabs[4]:
        tests = db.list_tests(project["id"])
        all_entries = db.list_entries_for_project(project["id"])
        total_entries = len(all_entries)
        st.caption(f"{len(tests)} sessão(ões) · {total_entries} registro(s) no total")

        # O relatório do projeto também mostra apenas Emocards e AttrakDiff.
        emo_techs = [t for t in techniques if t["type"] == "emocards"]
        attrak_techs = [t for t in techniques if t["type"] == "attrakdiff"]
        any_chart = False
        for tech in emo_techs:
            task_order = [t["task_name"] for t in tech["tasks"]]
            by_task = emo_counts_by_task(all_entries, tech["id"], task_order)
            if by_task:
                any_chart = True
                st.subheader(tech["name"])
                for task_name, counts in by_task.items():
                    fig = make_bar_chart(task_name, tech["labels"], counts)
                    st.pyplot(fig, use_container_width=False)
                st.caption(legend_caption(tech["labels"]))
        for tech in attrak_techs:
            scores = attrakdiff_scores_from_entries(all_entries, tech["id"])
            if scores:
                any_chart = True
                st.subheader(tech["name"])
                fig = make_attrakdiff_chart(
                    scores, title=f"{tech['name']} — média de todas as sessões", color=ATTRAK_COLOR,
                )
                st.pyplot(fig, use_container_width=False)
        if not any_chart:
            st.caption("Ainda não há dados suficientes para o relatório agregado.")

        if all_entries:
            df = pd.DataFrame(all_entries)
            st.download_button(
                "Baixar .csv de todos os registros", df.to_csv(index=False).encode("utf-8"),
                file_name=f"{project['name']}_registros.csv", mime="text/csv",
            )
            pdf_bytes = build_project_pdf(project, techniques, tests, all_entries)
            st.download_button(
                "Gerar e baixar PDF do projeto", pdf_bytes,
                file_name=f"{project['name']}_relatorio.pdf", mime="application/pdf",
            )


# ============================= roteamento =============================
if view == "runner" and current_tid:
    render_runner()
elif view == "result" and current_tid:
    render_result()
else:
    render_project()
