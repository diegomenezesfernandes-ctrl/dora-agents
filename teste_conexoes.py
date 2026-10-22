# ============================================================
# teste_conexoes.py
# Objetivo: verificar se as chaves do .env funcionam
#           no Jira e no GitHub.
# ============================================================

import os                       # permite ler variáveis do sistema
import httpx                    # permite acessar endereços da internet (APIs)
from dotenv import load_dotenv  # lê o arquivo .env

# Carrega o .env para a memória do programa
load_dotenv()

# ------------------------------------------------------------
# PASSO 1: conferir se todas as variáveis foram preenchidas
# ------------------------------------------------------------
necessarias = [
    "JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY",
    "GITHUB_TOKEN", "GITHUB_REPO",
]
faltando = [nome for nome in necessarias if not os.getenv(nome)]

if faltando:
    print("[ERRO] Faltam estas variaveis no .env:", faltando)
    raise SystemExit  # encerra o programa aqui

# Guarda os valores em variáveis com nomes curtos
jira_url   = os.getenv("JIRA_URL").rstrip("/")   # remove "/" do final, se houver
jira_email = os.getenv("JIRA_EMAIL")
jira_token = os.getenv("JIRA_API_TOKEN")
jira_key   = os.getenv("JIRA_PROJECT_KEY")
gh_token   = os.getenv("GITHUB_TOKEN")
gh_repo    = os.getenv("GITHUB_REPO")

# ------------------------------------------------------------
# PASSO 2: testar o Jira
# O Jira usa "e-mail + token" como se fosse "usuário + senha".
# ------------------------------------------------------------
print("\n--- Testando o Jira ---")

# 2a) Quem sou eu? (confirma que o login funciona)
resp = httpx.get(
    f"{jira_url}/rest/api/3/myself",
    auth=(jira_email, jira_token),
    timeout=30,  # espera no máximo 30 segundos
)
if resp.status_code == 200:          # 200 = "deu certo" na linguagem da web
    print("[OK] Login no Jira como:", resp.json()["displayName"])
else:
    print("[ERRO] Login no Jira falhou. Codigo:", resp.status_code)

# 2b) O projeto existe? (confirma a chave do projeto)
resp = httpx.get(
    f"{jira_url}/rest/api/3/project/{jira_key}",
    auth=(jira_email, jira_token),
    timeout=30,
)
if resp.status_code == 200:
    print("[OK] Projeto encontrado:", resp.json()["name"])
else:
    print("[ERRO] Projeto", jira_key, "nao encontrado. Codigo:", resp.status_code)

# ------------------------------------------------------------
# PASSO 3: testar o GitHub
# O GitHub usa o token num "cabeçalho" chamado Authorization.
# ------------------------------------------------------------
print("\n--- Testando o GitHub ---")

resp = httpx.get(
    f"https://api.github.com/repos/{gh_repo}",
    headers={
        "Authorization": f"Bearer {gh_token}",
        "Accept": "application/vnd.github+json",
    },
    timeout=30,
)
if resp.status_code == 200:
    print("[OK] Repositorio encontrado:", resp.json()["full_name"])
else:
    print("[ERRO] GitHub falhou. Codigo:", resp.status_code)

print("\nFim do teste.")