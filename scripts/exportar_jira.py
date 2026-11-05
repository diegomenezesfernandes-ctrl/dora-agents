# ============================================================
# scripts/exportar_jira.py  (KAN-5, Dia 4)
# Objetivo: buscar os tickets REAIS com o historico de status,
#           salvar no formato padrao e mostrar o lead time de cada um.
# Como rodar:  uv run scripts\exportar_jira.py
# Saida:       data\jira_tickets.json  (fica fora do Git, ver .gitignore)
# ============================================================

import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from dora_agents.clients.jira import JiraClient

load_dotenv()
jira = JiraClient.do_ambiente()
projeto = os.environ["JIRA_PROJECT_KEY"]

print("Buscando tickets e changelog (um pedido por ticket, pode levar alguns segundos)...")
tickets = jira.tickets_normalizados(projeto)

# 1) Salva no formato padrao
pasta = Path("data")
pasta.mkdir(exist_ok=True)
arquivo = pasta / "jira_tickets.json"
arquivo.write_text(json.dumps({"tickets": tickets}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Arquivo gerado: {arquivo} ({len(tickets)} tickets, subtarefas excluidas)\n")


# 2) Mostra o historico e o lead time dos tickets concluidos
def horas_entre(inicio, fim):
    return (datetime.fromisoformat(fim) - datetime.fromisoformat(inicio)).total_seconds() / 3600


for t in tickets:
    print(f"{t['chave']}  ({t['tipo']})  criado em {t['criado_em']}")
    for h in t["historico_status"]:
        print(f"    {h['em']}   {h['de']:<11} -> {h['para']}")

    # Lead time = criado -> ULTIMA vez que entrou em Done
    # (se o ticket foi reaberto e concluido de novo, vale a conclusao final)
    entradas_done = [h["em"] for h in t["historico_status"] if h["para"] == "Done"]
    if entradas_done:
        horas = horas_entre(t["criado_em"], entradas_done[-1])
        print(f"    >>> LEAD TIME: {horas:.1f} horas ({horas / 24:.1f} dias)")
    else:
        print("    (ainda nao concluido)")
    print()