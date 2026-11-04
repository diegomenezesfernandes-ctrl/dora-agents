# ============================================================
# scripts/listar_tickets.py  (DORA-3)
# Objetivo: usar o JiraClient para listar os tickets REAIS
#           do projeto, e VER a paginacao acontecendo.
# Como rodar:  uv run scripts\listar_tickets.py
# ============================================================

import os
from dotenv import load_dotenv
from dora_agents.clients.jira import JiraClient

load_dotenv()                                    # carrega o .env

jira = JiraClient.do_ambiente()                  # cria o cliente com as chaves do .env
projeto = os.environ["JIRA_PROJECT_KEY"]         # ex.: DORA

# JQL = "Jira Query Language", a linguagem de busca do Jira.
# Aqui: todos os tickets do projeto, do mais antigo para o mais novo.
jql = f"project = {projeto} ORDER BY created ASC"

# tamanho_pagina=5 de proposito: com poucos tickets, assim
# conseguimos ver varias paginas. Em producao usariamos 50 ou 100.
print("Buscando tickets...")
tickets = jira.buscar(
    jql,
    campos=["summary", "status", "issuetype", "created"],
    tamanho_pagina=5,
    mostrar_progresso=True,
)

print(f"\nTotal: {len(tickets)} tickets\n")
for t in tickets:
    f = t["fields"]                              # os campos ficam dentro de "fields"
    chave = t["key"]
    tipo = f["issuetype"]["name"]
    status = f["status"]["name"]
    criado = f["created"][:10]                   # so a data (AAAA-MM-DD)
    titulo = f["summary"]
    print(f"{chave:<9} {tipo:<10} {status:<13} {criado}  {titulo}")