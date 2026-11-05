# Lista cada status do Jira com a sua categoria
from dotenv import load_dotenv
from dora_agents.clients.jira import JiraClient

load_dotenv()
jira = JiraClient.do_ambiente()

resp = jira.http.get(f"{jira.url}/rest/api/3/status")   # todos os status
for s in resp.json():
    print(f"{s['name']:<15} id={s['id']:<8} categoria={s['statusCategory']['key']}")