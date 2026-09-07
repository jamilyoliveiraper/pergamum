"""Geração do relatório em PDF (agregado por tarefa) usando fpdf2."""
import io
import base64
from datetime import datetime
from fpdf import FPDF
from charts import make_bar_chart, emo_counts_by_task


def _fig_to_png_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    return buf


def build_project_pdf(project, techniques, tests, entries):
    pdf = FPDF(unit="pt", format="A4")
    pdf.set_auto_page_break(auto=True, margin=40)
    pdf.add_page()

    pdf.set_font("Times", "B", 20)
    pdf.cell(0, 26, project["name"], ln=1)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(90, 90, 90)
    pdf.cell(0, 16, f"Relatorio gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1)
    pdf.cell(0, 16, f"{len(tests)} sessao(oes) de teste registrada(s)", ln=1)
    pdf.set_text_color(20, 20, 20)
    pdf.ln(6)

    emo_techs = [t for t in techniques if t["type"] == "emocards"]
    three_e_techs = [t for t in techniques if t["type"] == "3e"]
    wrote_anything = False

    for tech in emo_techs:
        task_order = [t["task_name"] for t in tech.get("tasks", [])]
        by_task = emo_counts_by_task(entries, tech["id"], task_order)
        if not by_task:
            continue
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 20, f"{tech['name']} - agregado de todas as sessoes", ln=1)
        for task_name, counts in by_task.items():
            fig = make_bar_chart(task_name, tech["labels"], counts)
            img = _fig_to_png_bytes(fig)
            if pdf.get_y() > 620:
                pdf.add_page()
            pdf.image(img, w=440)
            pdf.ln(4)
            wrote_anything = True

    for test in tests:
        test_entries = [e for e in entries if e["test_id"] == test["id"]]
        if not test_entries:
            continue
        if pdf.get_y() > 600:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 18, f"Sessao: {test['participant']}", ln=1)
        pdf.set_font("Helvetica", "", 10.5)
        pdf.set_text_color(90, 90, 90)
        co = f" - com {test['co_testers']}" if test.get("co_testers") else ""
        pdf.cell(0, 14, f"Facilitador: {test['tester']}{co}", ln=1)
        pdf.cell(0, 14, f"Data: {test.get('test_datetime','')}", ln=1)
        pdf.set_text_color(20, 20, 20)
        wrote_anything = True

        for tech in emo_techs:
            counts = [0] * 8
            for e in test_entries:
                if e.get("technique_id") == tech["id"] and e.get("emotion"):
                    counts[e["emotion"] - 1] += 1
            if sum(counts) == 0:
                continue
            fig = make_bar_chart(f"{tech['name']} - emocoes gerais", tech["labels"], counts)
            img = _fig_to_png_bytes(fig)
            if pdf.get_y() > 560:
                pdf.add_page()
            pdf.image(img, w=380)
            pdf.ln(4)

        for tech in three_e_techs:
            e3 = next((e for e in test_entries if e.get("technique_id") == tech["id"]), None)
            if not e3:
                continue
            if pdf.get_y() > 640:
                pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 18, f"{tech['name']} (3E)", ln=1)
            pdf.set_font("Helvetica", "", 10.5)
            if e3.get("note"):
                pdf.multi_cell(0, 13, e3["note"])
            if e3.get("drawing"):
                try:
                    img_bytes = io.BytesIO(base64.b64decode(e3["drawing"]))
                    if pdf.get_y() > 560:
                        pdf.add_page()
                    pdf.image(img_bytes, w=200)
                except Exception:
                    pass
            pdf.ln(6)

        notes = [e for e in test_entries if e.get("note") and e.get("technique_id") not in {t["id"] for t in three_e_techs}]
        if notes:
            pdf.set_font("Helvetica", "I", 10)
            for e in notes:
                if pdf.get_y() > 760:
                    pdf.add_page()
                pdf.multi_cell(0, 13, f"{e['task_name']}: {e['note']}")
        pdf.ln(8)

    if not wrote_anything:
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 16, "Ainda nao ha registros suficientes para gerar um relatorio completo.")

    return bytes(pdf.output(dest="S"))
