# Campo — versão Streamlit + Supabase

App multi-usuário: todos os facilitadores acessam a **mesma URL** e leem/gravam no **mesmo banco de dados**
(Supabase/Postgres). Os dados ficam salvos no banco a cada ação — se você fechar a aba, o teste continua
exatamente de onde parou (basta reabrir o link da sessão, ou reabrir o teste "em andamento" na aba Testes).

## 1. Criar o banco no Supabase (gratuito)

1. Crie uma conta em https://supabase.com e crie um novo projeto.
2. Vá em **SQL Editor > New query**, cole o conteúdo de `schema.sql` deste pacote e rode.
3. Vá em **Settings > API** e copie:
   - **Project URL** → vai virar `SUPABASE_URL`
   - **anon public key** → vai virar `SUPABASE_KEY`
     (para um app interno de equipe, a anon key com RLS desligado — já feito no `schema.sql` — é suficiente;
     dá para reforçar depois com Supabase Auth + RLS se quiser controlar quem edita o quê).

## 2. Colocar o código num repositório GitHub

Suba esta pasta inteira (`app.py`, `db.py`, `charts.py`, `pdf_export.py`, `requirements.txt`, `schema.sql`)
para um repositório no GitHub. **Não suba** o arquivo `.streamlit/secrets.toml` (só o `.example`) — as chaves
do Supabase são configuradas direto no Streamlit Cloud, no passo 3.

## 3. Publicar no Streamlit Community Cloud (gratuito, não roda na sua máquina)

1. Acesse https://share.streamlit.io e conecte sua conta do GitHub.
2. Clique em "New app", escolha o repositório e o arquivo principal `app.py`.
3. Antes de rodar, vá em **Advanced settings > Secrets** e cole:
   ```
   SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
   SUPABASE_KEY = "sua-chave-anon"
   ```
4. Clique em Deploy. Você recebe uma URL pública (tipo `https://campo-seuapp.streamlit.app`).
5. Envie essa URL para todos os facilitadores — todos usam o mesmo link e o mesmo projeto/banco de dados.

## Como funciona a continuidade da sessão

- A posição de qual tarefa está sendo testada fica guardada apenas na aba aberta (para evitar pular tarefa à
  toa). Se você fechar a aba no meio de uma tarefa, ao reabrir o teste ele volta para a primeira tarefa da
  lista — mas como cada tarefa já respondida aparece com o botão **Seguir**, é só clicar até chegar na próxima
  pendente. **Nenhum registro já salvo é perdido**, porque cada resposta vai direto para o Supabase assim que
  você confirma no pop-up.
- Todos os registros, tarefas, técnicas e projetos ficam no Supabase — não em `session_state` do Streamlit
  nem no navegador — por isso sobrevivem a reload, a fechar a aba, e são vistos por qualquer facilitador
  com acesso à mesma URL.

## Rodando localmente para testar antes do deploy (opcional)

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # edite com suas chaves reais
streamlit run app.py
```

Isso roda só na sua máquina, para conferência — para os outros facilitadores acessarem, use o deploy do
passo 3.
