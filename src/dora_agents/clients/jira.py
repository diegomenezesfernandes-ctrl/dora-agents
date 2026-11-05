# ============================================================
# src/dora_agents/clients/jira.py  (DORA-3)
# Objetivo: buscar TODOS os tickets de um projeto no Jira,
#           pagina por pagina, sem perder nenhum.
#
# Endpoint usado: POST /rest/api/3/search/jql
#   - E o endpoint atual de busca do Jira Cloud.
#   - Pagina com "nextPageToken" (um "marcador de pagina").
# ============================================================

import os
from datetime import datetime
import httpx

# O Jira agrupa todo status em 3 "categorias", com chaves fixas em ingles.
# Usamos a categoria, e nao o nome do status ("A fazer", "Concluído"...),
# porque o nome muda com o idioma e com a configuracao de cada time.
CATEGORIA_PARA_PADRAO = {
    "new": "To Do",
    "indeterminate": "In Progress",
    "done": "Done",
}


class JiraClient:
    """Cliente simples da API do Jira Cloud.

    'Cliente' = uma classe que esconde os detalhes da API
    (endereco, login, paginacao) e oferece metodos faceis de usar.
    """

    def __init__(self, url, email, token, http=None):
        self.url = url.rstrip("/")                 # remove "/" do final, se houver
        # 'http' pode ser passado de fora (util nos testes).
        # Se ninguem passar, criamos um cliente HTTP de verdade.
        self.http = http or httpx.Client(auth=(email, token), timeout=30)

    @classmethod
    def do_ambiente(cls):
        """Cria o cliente lendo JIRA_URL, JIRA_EMAIL e JIRA_API_TOKEN do .env."""
        return cls(
            url=os.environ["JIRA_URL"],
            email=os.environ["JIRA_EMAIL"],
            token=os.environ["JIRA_API_TOKEN"],
        )

    def buscar(self, jql, campos, tamanho_pagina=50, mostrar_progresso=False):
        """Executa uma busca JQL e devolve a lista COMPLETA de tickets.

        jql            -> a consulta, ex.: 'project = DORA ORDER BY created ASC'
        campos         -> quais campos trazer, ex.: ["summary", "status"]
        tamanho_pagina -> quantos tickets por pagina (o Jira limita o maximo)
        """
        todos = []            # aqui vamos juntando os tickets de todas as paginas
        marcador = None       # na 1a pagina ainda nao temos marcador
        pagina = 0

        while True:
            pagina += 1

            # 1) Monta o pedido da pagina atual
            corpo = {"jql": jql, "fields": campos, "maxResults": tamanho_pagina}
            if marcador:
                corpo["nextPageToken"] = marcador      # "me de a pagina seguinte a esta"

            # 2) Envia para o Jira
            resp = self.http.post(f"{self.url}/rest/api/3/search/jql", json=corpo)
            resp.raise_for_status()   # se vier erro (401, 404...), para aqui com mensagem clara
            dados = resp.json()

            # 3) Guarda os tickets desta pagina
            tickets = dados.get("issues", [])
            todos.extend(tickets)
            if mostrar_progresso:
                print(f"  pagina {pagina}: {len(tickets)} tickets (acumulado: {len(todos)})")

            # 4) Decide se ha mais paginas
            marcador = dados.get("nextPageToken")
            if dados.get("isLast", True) or not marcador:
                break                                  # acabou: nao ha proxima pagina

            # Trava de seguranca: evita loop infinito se a API se comportar mal
            if pagina >= 1000:
                raise RuntimeError("Mais de 1000 paginas: algo esta errado na paginacao.")

        return todos

    # ========================================================
    # DIA 4: changelog e normalizacao
    # ========================================================

    def mapa_categorias(self):
        """Devolve {id_do_status: "To Do" | "In Progress" | "Done"}.

        Ex.: o status "Em andamento" (id 3) vira "In Progress"."""
        resp = self.http.get(f"{self.url}/rest/api/3/status")
        resp.raise_for_status()
        mapa = {}
        for status in resp.json():
            categoria = status["statusCategory"]["key"]          # "new", "indeterminate" ou "done"
            mapa[status["id"]] = CATEGORIA_PARA_PADRAO.get(categoria, "To Do")
        return mapa

    def changelog(self, chave):
        """Devolve TODAS as mudancas de um ticket (status, titulo, responsavel...).

        Este endpoint pagina do jeito "antigo": por posicao (startAt),
        e nao por marcador. Mesma ideia, outra forma: pedir de novo
        a partir de onde parou, ate a API dizer isLast = true."""
        todas = []
        inicio = 0
        while True:
            resp = self.http.get(
                f"{self.url}/rest/api/3/issue/{chave}/changelog",
                params={"startAt": inicio, "maxResults": 100},
            )
            resp.raise_for_status()
            dados = resp.json()
            valores = dados.get("values", [])
            todas.extend(valores)
            if dados.get("isLast", True) or not valores:
                break
            inicio += len(valores)                               # proxima "pagina"
        return todas

    def tickets_normalizados(self, projeto):
        """Busca os tickets do projeto e devolve no MESMO formato do
        JSON sintetico (fixtures/dados_sinteticos.json).

        Esse e o coracao do dia: quem calcula as metricas nao precisa
        saber se os dados vieram do Jira ou do gerador sintetico."""
        categorias = self.mapa_categorias()
        brutos = self.buscar(
            f"project = {projeto} ORDER BY created ASC",
            campos=["issuetype", "created"],
        )

        resultado = []
        for t in brutos:
            tipo = t["fields"]["issuetype"]

            # Subtarefas ficam de fora: contariam o mesmo trabalho duas vezes
            if tipo.get("subtask"):
                continue

            # Cada "entrada" do changelog tem uma data e uma lista de itens.
            # So nos interessam os itens em que o campo alterado e o status.
            historico = []
            for entrada in self.changelog(t["key"]):
                quando = _data_iso(entrada["created"])
                for item in entrada["items"]:
                    if item.get("field") != "status":
                        continue
                    de = categorias.get(item.get("from"), "To Do")
                    para = categorias.get(item.get("to"), "To Do")
                    if de == para:
                        continue          # ex.: "Em andamento" -> "Em revisao": mesma categoria
                    historico.append({"de": de, "para": para, "em": quando})

            historico.sort(key=lambda h: h["em"])     # garante ordem cronologica
            resultado.append({
                "chave": t["key"],
                "tipo": tipo["name"],
                "criado_em": _data_iso(t["fields"]["created"]),
                "historico_status": historico,
            })
        return resultado


def _data_iso(texto_jira):
    """Converte '2026-10-22T10:05:12.345-0300' em '2026-10-22T10:05-03:00'."""
    return datetime.fromisoformat(texto_jira).isoformat(timespec="minutes")