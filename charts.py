"""Gráficos formais em barras 2D (sem efeito 3D), usados na tela e no PDF."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BAR_COLOR = "#1F7A6C"


def emo_counts_from_entries(entries, technique_id):
    """Conta emoções (1..8) de uma lista de entries, ignorando a tarefa."""
    counts = [0] * 8
    for e in entries:
        if e.get("technique_id") == technique_id and e.get("emotion"):
            counts[e["emotion"] - 1] += 1
    return counts


def emo_counts_by_task(entries, technique_id, task_order):
    """Retorna {tarefa: [counts x8]} respeitando a ordem cadastrada das tarefas."""
    result = {}
    for e in entries:
        if e.get("technique_id") != technique_id or not e.get("emotion"):
            continue
        task = e["task_name"]
        if task not in result:
            result[task] = [0] * 8
        result[task][e["emotion"] - 1] += 1
    ordered = {t: result[t] for t in task_order if t in result}
    for t in result:
        if t not in ordered:
            ordered[t] = result[t]
    return ordered


def make_bar_chart(title, labels, counts):
    """Gráfico de barras simples e formal, com legenda numerada abaixo."""
    fig, ax = plt.subplots(figsize=(7, 4))
    x = list(range(1, len(labels) + 1))
    ax.bar(x, counts, color=BAR_COLOR, width=0.6)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_ylabel("Respostas")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    max_count = max(counts) if counts else 0
    ax.set_ylim(0, max_count + 1 if max_count else 1)
    for i, v in enumerate(counts):
        if v > 0:
            ax.text(i + 1, v + 0.05, str(v), ha="center", fontsize=9, fontweight="bold")
    fig.tight_layout()
    return fig


def legend_caption(labels):
    return "  •  ".join(f"**{i+1}** {lbl}" for i, lbl in enumerate(labels))
