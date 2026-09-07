"""Gráficos formais em barras 2D (sem efeito 3D), usados na tela e no PDF."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BAR_COLOR = "#1F7A6C"


def three_e_diagram_html():
    """Ilustração simples (balão de fala + boneco + nuvem de pensamento) para a técnica 3E."""
    return """
    <svg viewBox="0 0 340 175" width="300" xmlns="http://www.w3.org/2000/svg">
      <rect x="8" y="8" width="130" height="82" rx="16" fill="none" stroke="#3A4552" stroke-width="2"/>
      <polygon points="55,90 78,90 50,116" fill="none" stroke="#3A4552" stroke-width="2"/>
      <ellipse cx="168" cy="108" rx="14" ry="16" fill="none" stroke="#3A4552" stroke-width="2"/>
      <line x1="168" y1="124" x2="168" y2="150" stroke="#3A4552" stroke-width="2"/>
      <line x1="168" y1="130" x2="152" y2="145" stroke="#3A4552" stroke-width="2"/>
      <line x1="168" y1="130" x2="184" y2="145" stroke="#3A4552" stroke-width="2"/>
      <line x1="168" y1="150" x2="155" y2="170" stroke="#3A4552" stroke-width="2"/>
      <line x1="168" y1="150" x2="181" y2="170" stroke="#3A4552" stroke-width="2"/>
      <circle cx="195" cy="98" r="5" fill="none" stroke="#3A4552" stroke-width="2"/>
      <circle cx="206" cy="88" r="8" fill="none" stroke="#3A4552" stroke-width="2"/>
      <path d="M220 30
               a20 20 0 0 1 38 -8
               a18 18 0 0 1 34 4
               a16 16 0 0 1 20 22
               a16 16 0 0 1 -8 28
               a18 18 0 0 1 -30 10
               a20 20 0 0 1 -32 -4
               a18 18 0 0 1 -22 -20
               a16 16 0 0 1 0 -32 z"
            fill="none" stroke="#3A4552" stroke-width="2"/>
    </svg>
    """


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
