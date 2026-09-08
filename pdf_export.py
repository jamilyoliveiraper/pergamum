"""Geração do relatório em PDF (agregado por tarefa) usando fpdf2.

O relatório mostra apenas os resultados de Emocards e AttrakDiff — as demais
técnicas (3E, anotações livres etc.) não entram neste PDF.
"""
import io
from datetime import datetime
from fpdf import FPDF
from charts import make_bar_chart, emo_counts_by_task, attrakdiff_scores_from_entries, make_attrakdiff_chart, ATTRAK_COLOR


def _fig_to_png_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    return buf


# Largura de página útil em pt (A4, margens de 40pt) e layout de duas colunas
# usado para os gráficos de Emocards, deixando espaço para caber dois lado a lado.
_PAGE_MARGIN = 40
_COL_GAP = 16
_COL_W = 245  # 2 * 245 + 16 = 506pt, dentro dos ~515pt úteis de uma A4
_COL_ASPECT = 3.9 / 5.4  # mesma proporção do figsize usado em make_bar_chart


def _place_chart_row(pdf, figs, break_y=560):
    """Desenha até dois gráficos lado a lado na mesma linha, avançando o cursor do PDF
    em seguida. `figs` deve ter 1 ou 2 figuras do matplotlib."""
    if pdf.get_y() > break_y:
        pdf.add_page()
    y = pdf.get_y()
    row_h = _COL_W * _COL_ASPECT
    for i, fig in enumerate(figs[:2]):
        img = _fig_to_png_bytes(fig)
        x = _PAGE_MARGIN + i * (_COL_W + _COL_GAP)
        pdf.image(img, x=x, y=y, w=_COL_W)
    pdf.set_y(y + row_h + 12)


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
    attrak_techs = [t for t in techniques if t["type"] == "attrakdiff"]
    report_tech_ids = {t["id"] for t in emo_techs + attrak_techs}
    wrote_anything = False

    # ---- agregado de todas as sessoes: Emocards ----
    for tech in emo_techs:
        task_order = [t["task_name"] for t in tech.get("tasks", [])]
        by_task = emo_counts_by_task(entries, tech["id"], task_order)
        if not by_task:
            continue
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 20, f"{tech['name']} - agregado de todas as sessoes", ln=1)
        figs = [make_bar_chart(task_name, tech["labels"], counts) for task_name, counts in by_task.items()]
        for i in range(0, len(figs), 2):
            _place_chart_row(pdf, figs[i:i + 2])
            wrote_anything = True

    # ---- agregado de todas as sessoes: AttrakDiff ----
    for tech in attrak_techs:
        scores = attrakdiff_scores_from_entries(entries, tech["id"])
        if not scores:
            continue
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 20, f"{tech['name']} - media de todas as sessoes", ln=1)
        fig = make_attrakdiff_chart(scores, color=ATTRAK_COLOR)
        img = _fig_to_png_bytes(fig)
        if pdf.get_y() > 500:
            pdf.add_page()
        pdf.image(img, w=440)
        pdf.ln(4)
        wrote_anything = True

    # ---- uma secao por sessao, so com Emocards e AttrakDiff ----
    for test in tests:
        test_entries = [e for e in entries if e["test_id"] == test["id"] and e["technique_id"] in report_tech_ids]
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

        session_emo_figs = []
        for tech in emo_techs:
            counts = [0] * 8
            for e in test_entries:
                if e.get("technique_id") == tech["id"] and e.get("emotion"):
                    counts[e["emotion"] - 1] += 1
            if sum(counts) == 0:
                continue
            session_emo_figs.append(make_bar_chart(f"{tech['name']} - emocoes gerais", tech["labels"], counts))
        for i in range(0, len(session_emo_figs), 2):
            _place_chart_row(pdf, session_emo_figs[i:i + 2], break_y=500)

        for tech in attrak_techs:
            scores = attrakdiff_scores_from_entries(test_entries, tech["id"])
            if not scores:
                continue
            fig = make_attrakdiff_chart(scores, color=ATTRAK_COLOR)
            img = _fig_to_png_bytes(fig)
            if pdf.get_y() > 460:
                pdf.add_page()
            pdf.image(img, w=380)
            pdf.ln(4)

        pdf.ln(8)

    if not wrote_anything:
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 16, "Ainda nao ha registros suficientes para gerar um relatorio completo.")

    return bytes(pdf.output(dest="S"))
