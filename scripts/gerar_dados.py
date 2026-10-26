# ============================================================
# gerar_dados.py  (DORA-2)
# Objetivo: criar meses de historico FICTICIO, mas realista,
#           de um time de software: tickets, deploys e incidentes.
# Saida:    fixtures/dados_sinteticos.json
#
# Usa apenas bibliotecas que ja vem com o Python (nada a instalar).
# ============================================================

import json                                   # salvar os dados em arquivo .json
import math                                   # funcoes matematicas (log)
import random                                 # sorteios aleatorios
import statistics                             # media e mediana prontas
from datetime import datetime, timedelta      # trabalhar com datas e horas
from pathlib import Path                      # trabalhar com pastas e arquivos

# ------------------------------------------------------------
# 1) PARAMETROS DO "TIME FICTICIO"
#    Mude estes numeros para simular times melhores ou piores.
# ------------------------------------------------------------
SEMENTE = 42               # mesma semente = mesmos dados sempre (reprodutivel)
SEMANAS = 16               # ~4 meses de historico
TICKETS_POR_SEMANA = 6     # quantos tickets o time conclui por semana, em media

# Lead time (ticket criado -> Done), em DIAS, segue uma LOGNORMAL.
# A lognormal e definida por dois numeros:
#   - mediana: o valor "do meio" (metade das tarefas termina antes disso)
#   - sigma:   o tamanho da "cauda" (quanto maior, mais tarefas muito demoradas)
LEAD_TIME_MEDIANA_DIAS = 4.0
LEAD_TIME_SIGMA = 0.9

# Parte do lead time que o ticket passa PARADO em "To Do" antes de alguem pegar.
# Ex.: 0.4 = em media 40% do tempo e espera, 60% e trabalho.
FRACAO_ESPERA = 0.4

PROB_DEPLOY_FALHAR = 0.15           # 15% dos deploys geram incidente (Change Failure Rate)
RECUPERACAO_MEDIANA_HORAS = 5.0     # tempo tipico para corrigir um incidente
RECUPERACAO_SIGMA = 1.0

TIPOS = ["Tarefa", "Historia"]      # tipos de ticket "normais"
PESOS_TIPOS = [0.6, 0.4]            # 60% Tarefa, 40% Historia

INICIO = datetime(2026, 6, 1, 9, 0)  # data do primeiro ticket ficticio


# ------------------------------------------------------------
# 2) FUNCOES AUXILIARES
# ------------------------------------------------------------
def sortear_lognormal(mediana, sigma):
    """Sorteia um numero de uma lognormal a partir da MEDIANA desejada.
    Na lognormal, mediana = e^mu  ->  mu = ln(mediana)."""
    mu = math.log(mediana)
    return random.lognormvariate(mu, sigma)


def horario_comercial(momento):
    """Empurra um horario para dentro do expediente (seg-sex, 9h-18h).
    Gente de verdade nao faz deploy domingo as 3h da manha (geralmente)."""
    while momento.weekday() >= 5:                     # 5 = sabado, 6 = domingo
        momento = (momento + timedelta(days=1)).replace(hour=9, minute=0)
    if momento.hour < 9:
        momento = momento.replace(hour=9, minute=0)
    elif momento.hour >= 18:
        momento = (momento + timedelta(days=1)).replace(hour=9, minute=0)
        return horario_comercial(momento)              # pode ter caido no sabado
    return momento


def iso(momento):
    """Converte data/hora para texto no formato padrao (ISO 8601)."""
    return momento.isoformat(timespec="minutes")


def percentil(valores, p):
    """Valor abaixo do qual estao p% dos dados (ex.: p=85)."""
    ordenados = sorted(valores)
    posicao = (len(ordenados) - 1) * p / 100
    baixo = math.floor(posicao)
    alto = math.ceil(posicao)
    return ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (posicao - baixo)


# ------------------------------------------------------------
# 3) GERACAO DOS DADOS
# ------------------------------------------------------------
def gerar():
    random.seed(SEMENTE)

    tickets, deploys, incidentes = [], [], []
    numero_ticket = 100        # comeca em DORA-100 para nao confundir com os reais
    numero_deploy = 1

    total_tickets = SEMANAS * TICKETS_POR_SEMANA
    for _ in range(total_tickets):
        # --- 3a) Ticket criado em algum momento das 16 semanas ---
        criado = INICIO + timedelta(hours=random.uniform(0, SEMANAS * 7 * 24))
        criado = horario_comercial(criado)

        # --- 3b) Lead time sorteado da lognormal, dividido em espera + trabalho ---
        lead_time_dias = sortear_lognormal(LEAD_TIME_MEDIANA_DIAS, LEAD_TIME_SIGMA)
        espera = lead_time_dias * random.uniform(FRACAO_ESPERA * 0.5, FRACAO_ESPERA * 1.5)
        em_andamento = horario_comercial(criado + timedelta(days=espera))
        concluido = horario_comercial(criado + timedelta(days=lead_time_dias))

        # --- 3c) Codigo: primeiro commit logo depois de comecar o trabalho ---
        primeiro_commit = em_andamento + timedelta(hours=random.uniform(0.5, 4))
        merge_pr = concluido - timedelta(hours=random.uniform(1, 6))
        if merge_pr <= primeiro_commit:                     # tarefas muito rapidas
            merge_pr = primeiro_commit + timedelta(hours=1)

        # --- 3d) Deploy: acontece pouco depois do merge ---
        momento_deploy = horario_comercial(merge_pr + timedelta(hours=random.uniform(0.2, 3)))
        id_deploy = f"deploy-{numero_deploy:04d}"
        falhou = random.random() < PROB_DEPLOY_FALHAR       # moeda viciada de 15%

        chave = f"DORA-{numero_ticket}"
        tickets.append({
            "chave": chave,
            "tipo": random.choices(TIPOS, PESOS_TIPOS)[0],
            "criado_em": iso(criado),
            # O "changelog": cada mudanca de status com data/hora
            "historico_status": [
                {"de": "To Do", "para": "In Progress", "em": iso(em_andamento)},
                {"de": "In Progress", "para": "Done", "em": iso(concluido)},
            ],
            "primeiro_commit_em": iso(primeiro_commit),
            "deploy_id": id_deploy,
        })
        deploys.append({
            "id": id_deploy,
            "em": iso(momento_deploy),
            "tickets": [chave],
            "falhou": falhou,
        })
        numero_ticket += 1
        numero_deploy += 1

        # --- 3e) Se o deploy falhou, nasce um Bug (incidente) ---
        if falhou:
            aberto = momento_deploy + timedelta(minutes=random.uniform(10, 120))
            horas = sortear_lognormal(RECUPERACAO_MEDIANA_HORAS, RECUPERACAO_SIGMA)
            resolvido = aberto + timedelta(hours=horas)     # incidente nao espera horario comercial!
            chave_bug = f"DORA-{numero_ticket}"
            incidentes.append({
                "chave": chave_bug,
                "tipo": "Bug",
                "deploy_causador": id_deploy,
                "aberto_em": iso(aberto),
                "resolvido_em": iso(resolvido),
            })
            # A correcao tambem e um deploy
            deploys.append({
                "id": f"deploy-{numero_deploy:04d}",
                "em": iso(resolvido),
                "tickets": [chave_bug],
                "falhou": False,
            })
            numero_ticket += 1
            numero_deploy += 1

    # Ordena tudo por data, como num sistema real
    tickets.sort(key=lambda t: t["criado_em"])
    deploys.sort(key=lambda d: d["em"])
    incidentes.sort(key=lambda i: i["aberto_em"])
    return {"tickets": tickets, "deploys": deploys, "incidentes": incidentes}


# ------------------------------------------------------------
# 4) RESUMO NA TELA (para voce "enxergar" a lognormal)
# ------------------------------------------------------------
def resumo(dados):
    lead_times = []
    for t in dados["tickets"]:
        criado = datetime.fromisoformat(t["criado_em"])
        done = datetime.fromisoformat(t["historico_status"][-1]["em"])
        lead_times.append((done - criado).total_seconds() / 86400)   # segundos -> dias

    print(f"Tickets:     {len(dados['tickets'])}")
    print(f"Deploys:     {len(dados['deploys'])}")
    print(f"Incidentes:  {len(dados['incidentes'])}")
    print("\nLead time (dias):")
    print(f"  media    = {statistics.mean(lead_times):5.1f}")
    print(f"  mediana  = {statistics.median(lead_times):5.1f}")
    print(f"  p85      = {percentil(lead_times, 85):5.1f}")
    print(f"  maximo   = {max(lead_times):5.1f}")

    # Histograma de texto: cada # = 1 ticket
    print("\nDistribuicao (cada # = 1 ticket):")
    faixas = [(a, a + 2) for a in range(0, 16, 2)] + [(16, 999)]  # faixas de 2 em 2 dias
    for a, b in faixas:
        qtd = sum(1 for v in lead_times if a <= v < b)
        rotulo = f"{a:>2}-{b:<3}" if b != 999 else f"{a:>2}+   "
        print(f"  {rotulo} dias | {'#' * qtd} {qtd}")


# ------------------------------------------------------------
# 5) PROGRAMA PRINCIPAL
# ------------------------------------------------------------
if __name__ == "__main__":
    dados = gerar()

    pasta = Path("fixtures")
    pasta.mkdir(exist_ok=True)                               # cria a pasta se nao existir
    arquivo = pasta / "dados_sinteticos.json"
    arquivo.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Arquivo gerado: {arquivo}\n")
    resumo(dados)