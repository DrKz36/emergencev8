#!/usr/bin/env python3
"""
Génération du graphique de rétention mémoire
=============================================

Agrège les résultats CSV de memory_probe.py pour tous les agents
et génère un graphique comparatif de la rétention mémoire.

Usage:
    python scripts/plot_retention.py

    # Avec mode debug (ticks courts)
    DEBUG_MODE=true python scripts/plot_retention.py

Entrées:
    - memory_results_neo.csv
    - memory_results_anima.csv
    - memory_results_nexus.csv

Sortie:
    - retention_curve_all.png
"""

import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Configuration
ROOT_DIR = Path(__file__).parent.parent
OUTPUT_PNG = ROOT_DIR / "retention_curve_all.png"

# Mode debug (ticks courts)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Ordre des ticks (pour l'axe X)
if DEBUG_MODE:
    TICK_ORDER = ["T+1min", "T+2min", "T+3min"]
else:
    TICK_ORDER = ["T+1h", "T+1d", "T+1w"]


def plot_all():
    """Génère le graphique comparatif de rétention pour tous les agents."""
    print("="*80)
    print("📈 GÉNÉRATION DU GRAPHIQUE DE RÉTENTION MÉMOIRE")
    print("="*80)

    # Recherche des fichiers CSV
    csv_files = list(ROOT_DIR.glob("memory_results_*.csv"))

    if not csv_files:
        print("❌ Aucun fichier memory_results_*.csv trouvé dans", ROOT_DIR)
        print("   Exécutez d'abord memory_probe.py pour chaque agent.")
        return

    print(f"📂 {len(csv_files)} fichiers CSV trouvés:")
    for f in csv_files:
        print(f"   - {f.name}")
    print()

    # Configuration du graphique
    plt.figure(figsize=(10, 6))
    plt.style.use('seaborn-v0_8-darkgrid')

    colors = {
        'neo': '#3498db',      # Bleu
        'anima': '#e74c3c',    # Rouge
        'nexus': '#2ecc71'     # Vert
    }

    agents_plotted = []

    # Traitement de chaque fichier
    for csv_file in csv_files:
        agent_name = csv_file.stem.split("_")[-1].capitalize()

        try:
            df = pd.read_csv(csv_file)

            if df.empty:
                print(f"⚠️  {agent_name}: fichier vide, ignoré")
                continue

            # Agrégation par tick (moyenne des scores)
            pivot = df.pivot_table(
                index="tick",
                values="score",
                aggfunc="mean"
            )

            # Réindexation pour garantir l'ordre correct des ticks
            pivot = pivot.reindex(TICK_ORDER, fill_value=0)

            # Tracé de la courbe
            color = colors.get(agent_name.lower(), '#95a5a6')
            plt.plot(
                pivot.index,
                pivot["score"],
                marker="o",
                markersize=8,
                linewidth=2,
                label=agent_name,
                color=color
            )

            agents_plotted.append(agent_name)

            # Stats
            mean_score = pivot["score"].mean()
            print(f"✅ {agent_name}: score moyen = {mean_score:.2f}")

        except Exception as e:
            print(f"❌ Erreur lors du traitement de {csv_file.name}: {e}")
            continue

    # Pas d'agents à afficher
    if not agents_plotted:
        print("❌ Aucun agent n'a pu être tracé")
        return

    # Finalisation du graphique
    plt.title("Courbe de rétention mémoire – Agents ÉMERGENCE", fontsize=16, fontweight='bold')
    plt.xlabel("Échéance temporelle", fontsize=12)
    plt.ylabel("Score de rétention (0-1)", fontsize=12)
    plt.ylim(-0.05, 1.05)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', fontsize=11)

    # Annotations
    mode_text = "MODE DEBUG (délais courts)" if DEBUG_MODE else "Mode production"
    plt.text(
        0.02, 0.98,
        mode_text,
        transform=plt.gca().transAxes,
        fontsize=9,
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3)
    )

    plt.tight_layout()

    # Sauvegarde
    plt.savefig(OUTPUT_PNG, dpi=150)
    print()
    print("="*80)
    print(f"✅ Graphique généré avec succès")
    print(f"📊 Fichier : {OUTPUT_PNG}")
    print(f"👥 Agents tracés : {', '.join(agents_plotted)}")
    print("="*80)


def plot_detailed():
    """
    Génère un graphique détaillé avec un subplot par agent.
    Affiche les scores individuels par fait (F1, F2, F3).
    """
    print("\n📊 Génération du graphique détaillé par fait...")

    csv_files = list(ROOT_DIR.glob("memory_results_*.csv"))
    if not csv_files:
        print("❌ Aucun fichier CSV trouvé")
        return

    num_agents = len(csv_files)
    fig, axes = plt.subplots(1, num_agents, figsize=(6 * num_agents, 5), sharey=True)

    if num_agents == 1:
        axes = [axes]

    for idx, csv_file in enumerate(csv_files):
        agent_name = csv_file.stem.split("_")[-1].capitalize()
        ax = axes[idx]

        try:
            df = pd.read_csv(csv_file)

            # Pivot par tick et fact_id
            pivot = df.pivot_table(
                index="tick",
                columns="fact_id",
                values="score",
                aggfunc="mean"
            )

            # Réindexation
            pivot = pivot.reindex(TICK_ORDER, fill_value=0)

            # Tracé de chaque fait
            for fact_id in pivot.columns:
                ax.plot(
                    pivot.index,
                    pivot[fact_id],
                    marker="o",
                    label=fact_id,
                    linewidth=2
                )

            ax.set_title(f"Agent {agent_name}", fontsize=14, fontweight='bold')
            ax.set_xlabel("Échéance", fontsize=11)
            if idx == 0:
                ax.set_ylabel("Score", fontsize=11)
            ax.set_ylim(-0.05, 1.05)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best')

        except Exception as e:
            print(f"❌ Erreur pour {agent_name}: {e}")
            continue

    plt.tight_layout()
    detailed_png = ROOT_DIR / "retention_curve_detailed.png"
    plt.savefig(detailed_png, dpi=150)
    print(f"✅ Graphique détaillé sauvegardé : {detailed_png}")


if __name__ == "__main__":
    try:
        plot_all()

        # Graphique détaillé optionnel
        if os.getenv("DETAILED", "false").lower() == "true":
            plot_detailed()

    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
