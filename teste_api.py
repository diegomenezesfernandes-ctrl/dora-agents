# 1) Importa a ferramenta que lê o arquivo .env
from dotenv import load_dotenv

# 2) Importa a biblioteca oficial da Anthropic
import anthropic

# 3) Lê o .env e coloca a sua chave na memória do programa
load_dotenv()

# 4) Cria a "conexão" com a Anthropic (ela pega a chave automaticamente)
client = anthropic.Anthropic()

# 5) Envia uma mensagem para o Claude
resposta = client.messages.create(
    model="claude-haiku-5-5",   # modelo mais barato, ideal para testes
    max_tokens=50,               # limite de tamanho da resposta (controla custo)
    messages=[
        {"role": "user", "content": "Diga apenas: setup OK"}
    ],
)

# 6) Mostra a resposta na tela
print(resposta.content[0].text)