#!/usr/bin/env python3
"""
Merge Reports - Fusion des rapports des agents ÉMERGENCE
Fusionne les rapports d'Anima, Neo et ProdGuardian en un rapport global
"""

import json
import glob
import datetime
import os
import sys
from pathlib import Path
from collections import defaultdict

# Répertoire des rapports
REPORTS_DIR = Path(__file__).parent.parent / "reports"


def charger_rapports():
    """
    Charge tous les rapports JSON disponibles
    Returns: dict {nom_agent: données_rapport}
    """
    rapports = {}

    # Parcourir tous les fichiers *_report.json
    for fichier in REPORTS_DIR.glob("*_report.json"):
        nom_agent = fichier.stem.replace("_report", "")

        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                rapports[nom_agent] = json.load(f)
            print(f"✅ Chargé: {fichier.name}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Erreur lors du chargement de {fichier.name}: {e}", file=sys.stderr)
            rapports[nom_agent] = {"status": "error", "error": str(e)}

    return rapports


def determiner_statut_global(rapports):
    """
    Détermine le statut global basé sur tous les rapports
    Priority: CRITICAL > DEGRADED > WARNING > OK
    """
    statuts = []

    for agent, rapport in rapports.items():
        statut = rapport.get("status", "unknown").upper()
        statuts.append(statut)

    # Priorité
    if "CRITICAL" in statuts:
        return "CRITICAL"
    elif "DEGRADED" in statuts:
        return "DEGRADED"
    elif "WARNING" in statuts:
        return "WARNING"
    elif "ERROR" in statuts:
        return "ERROR"
    elif all(s in ["OK", "UNKNOWN"] for s in statuts):
        return "OK"
    else:
        return "UNKNOWN"


def extraire_actions_prioritaires(rapports):
    """
    Extrait et priorise toutes les actions recommandées
    Returns: list of actions sorted by priority
    """
    actions = []

    for agent, rapport in rapports.items():
        # Différents formats possibles
        recommandations = rapport.get("recommendations", [])
        if not isinstance(recommandations, list):
            recommandations = []

        for rec in recommandations:
            if isinstance(rec, dict):
                actions.append({
                    "agent": agent,
                    "priority": rec.get("priority", "MEDIUM"),
                    "action": rec.get("action", rec.get("description", "No description")),
                    "details": rec.get("details", rec.get("msg", ""))
                })

    # Trier par priorité
    priority_order = {"HIGH": 0, "CRITICAL": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
    actions.sort(key=lambda x: priority_order.get(x["priority"], 99))

    return actions


def generer_resume_par_agent(rapports):
    """
    Génère un résumé du statut de chaque agent
    """
    resume = {}

    for agent, rapport in rapports.items():
        statut = rapport.get("status", "unknown")

        # Informations spécifiques selon l'agent
        if agent == "docs":
            resume[agent] = {
                "statut": statut,
                "fichiers_modifies": len(rapport.get("changes_detected", [])),
                "docs_a_mettre_a_jour": len(rapport.get("docs_to_update", []))
            }
        elif agent == "integrity":
            resume[agent] = {
                "statut": statut,
                "problemes": len(rapport.get("issues", [])),
                "critical": len([i for i in rapport.get("issues", []) if i.get("severity") == "critical"])
            }
        elif agent == "prod":
            resume[agent] = {
                "statut": statut,
                "erreurs": rapport.get("summary", {}).get("errors", 0),
                "signaux_critiques": rapport.get("summary", {}).get("critical_signals", 0),
                "logs_analyses": rapport.get("logs_analyzed", 0)
            }
        else:
            resume[agent] = {
                "statut": statut,
                "details": "Rapport générique"
            }

    return resume


def fusionner_rapports(rapports):
    """
    Fusionne tous les rapports en un rapport global structuré
    """
    statut_global = determiner_statut_global(rapports)
    actions_prioritaires = extraire_actions_prioritaires(rapports)
    resume_agents = generer_resume_par_agent(rapports)

    # Compter les problèmes par type
    total_errors = 0
    total_warnings = 0
    total_critical = 0

    for agent, rapport in rapports.items():
        if agent == "prod":
            summary = rapport.get("summary", {})
            total_errors += summary.get("errors", 0)
            total_warnings += summary.get("warnings", 0)
            total_critical += summary.get("critical_signals", 0)
        elif agent == "integrity":
            issues = rapport.get("issues", [])
            for issue in issues:
                if issue.get("severity") == "critical":
                    total_critical += 1
                elif issue.get("severity") == "warning":
                    total_warnings += 1

    rapport_global = {
        "timestamp": datetime.datetime.now().isoformat(),
        "statut_global": statut_global,
        "resume": {
            "agents_executes": len(rapports),
            "total_erreurs": total_errors,
            "total_warnings": total_warnings,
            "total_critical": total_critical,
            "actions_prioritaires": len(actions_prioritaires)
        },
        "agents": resume_agents,
        "actions_prioritaires": actions_prioritaires[:10],  # Top 10
        "rapports_complets": rapports
    }

    return rapport_global


def afficher_resume(rapport_global):
    """
    Affiche un résumé lisible du rapport global
    """
    # Force UTF-8 encoding for emoji support on Windows
    import platform
    if platform.system() == "Windows":
        import sys
        sys.stdout.reconfigure(encoding='utf-8')

    print("\n" + "="*70)
    print("📊 RAPPORT DE SYNCHRONISATION GLOBALE")
    print("="*70)

    statut = rapport_global["statut_global"]
    emoji = {
        "OK": "🟢",
        "WARNING": "🟡",
        "DEGRADED": "🟡",
        "CRITICAL": "🔴",
        "ERROR": "🔴"
    }.get(statut, "⚪")

    print(f"\n{emoji} Statut Global: {statut}")
    print(f"🕒 Timestamp: {rapport_global['timestamp']}")

    print(f"\n📋 RÉSUMÉ:")
    resume = rapport_global["resume"]
    print(f"   - Agents exécutés: {resume['agents_executes']}")
    print(f"   - Erreurs totales: {resume['total_erreurs']}")
    print(f"   - Warnings: {resume['total_warnings']}")
    print(f"   - Signaux critiques: {resume['total_critical']}")
    print(f"   - Actions prioritaires: {resume['actions_prioritaires']}")

    print(f"\n✅ AGENTS:")
    for agent, details in rapport_global["agents"].items():
        agent_emoji = {"OK": "✅", "DEGRADED": "⚠️", "CRITICAL": "🔴"}.get(
            details["statut"].upper(), "❓"
        )
        print(f"   {agent_emoji} {agent.capitalize()}: {details['statut']}")
        if agent == "docs":
            if details.get("docs_a_mettre_a_jour", 0) > 0:
                print(f"      → {details['docs_a_mettre_a_jour']} docs à mettre à jour")
        elif agent == "integrity":
            if details.get("critical", 0) > 0:
                print(f"      → {details['critical']} problèmes critiques")
        elif agent == "prod":
            if details.get("erreurs", 0) > 0:
                print(f"      → {details['erreurs']} erreurs détectées")

    if rapport_global["actions_prioritaires"]:
        print(f"\n💡 ACTIONS PRIORITAIRES:")
        for i, action in enumerate(rapport_global["actions_prioritaires"][:5], 1):
            priority_emoji = {"HIGH": "🔴", "CRITICAL": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(
                action["priority"], "⚪"
            )
            print(f"   {i}. {priority_emoji} [{action['agent'].upper()}] {action['action']}")
            if action.get("details"):
                print(f"      → {action['details'][:100]}")

    print("\n" + "="*70 + "\n")


def main():
    """Fonction principale"""
    print("🔄 Fusion des rapports des agents ÉMERGENCE...\n", file=sys.stderr)

    # Créer le répertoire reports s'il n'existe pas
    REPORTS_DIR.mkdir(exist_ok=True)

    # Charger les rapports
    rapports = charger_rapports()

    if not rapports:
        print("⚠️  Aucun rapport trouvé dans reports/", file=sys.stderr)
        sys.exit(1)

    # Fusionner
    rapport_global = fusionner_rapports(rapports)

    # Sauvegarder
    output_path = REPORTS_DIR / "global_report.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(rapport_global, f, indent=2, ensure_ascii=False)

    print(f"✅ Rapport global sauvegardé: {output_path}\n", file=sys.stderr)

    # Afficher le résumé
    afficher_resume(rapport_global)

    # Code de sortie basé sur le statut global
    exit_code = 0
    if rapport_global["statut_global"] == "CRITICAL":
        exit_code = 2
    elif rapport_global["statut_global"] in ["DEGRADED", "ERROR"]:
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
