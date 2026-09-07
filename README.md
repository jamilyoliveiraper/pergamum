# Campo — versão Streamlit + Supabase

## Novidades desta versão

- **Excluir projetos**: além do botão já existente na aba "Visão geral" do projeto, agora também dá
  para excluir direto pela barra lateral, clicando no ícone 🗑️ ao lado do nome do projeto (pede
  confirmação antes de apagar).
- **Adicionar tarefa apertando Enter**: o campo "Nova tarefa" (na técnica Emocards) agora é um
  formulário — basta digitar o nome e apertar **Enter**, sem precisar clicar no botão.
- **Emojis nos gráficos**: os gráficos de barra agora mostram o emoji de cada emoção (😠🙁😕😐🙂😊😄🤩)
  abaixo da barra correspondente, além de já aparecerem nas legendas de texto. Para os emojis
  aparecerem coloridos quando publicado no Streamlit Community Cloud, este pacote inclui um arquivo
  `packages.txt` que instala a fonte `fonts-noto-color-emoji` no servidor — **não precisa fazer nada
  além do deploy normal**. Rodando localmente em Windows/Mac isso já funciona nativamente; em Linux
  local, instale essa mesma fonte do seu sistema se quiser vê-los no gráfico (`sudo apt install
  fonts-noto-color-emoji`), embora ela já apareça nas legendas de texto de qualquer forma.
- **Técnica 3E sem tarefas cadastradas**: a 3E deixou de pedir uma lista de tarefas. Agora ela é
  preenchida **uma única vez, ao final da sessão**: o(a) testador(a) pede ao participante para
  escrever seus comentários no balão de fala, seus pensamentos na nuvem de pensamento, e para
  **desenhar na cabeça do boneco** (usando o mouse/touch, direto no navegador) um rosto ou objetos
  que representem sua emoção ou experiência com o produto testado. O fluxo do desenho é:
  1. desenhar no quadro que aparece na tela;
  2. clicar em **⬇ Baixar desenho (PNG)** (o navegador salva o arquivo, geralmente na pasta Downloads);
  3. enviar esse mesmo arquivo de volta logo abaixo, no campo de upload.

  Esse vai-e-volta existe por um motivo técnico importante: a primeira versão usava uma biblioteca de
  terceiros (`streamlit-drawable-canvas`) para um canvas com retorno direto ao Python, mas essa
  biblioteca está **sem manutenção há anos** e quebrou assim que o Streamlit Cloud atualizou para uma
  versão mais nova do Streamlit (foi o erro `RuntimeError` que você viu). Para não depender de um
  pacote frágil que pode quebrar de novo a qualquer atualização, o desenho agora usa só a API estável
  e nativa do Streamlit (`components.html` + `file_uploader`), que não tem esse risco — ao custo de um
  passo extra (baixar e reenviar o arquivo) em vez de ficar tudo em uma única tela.
  - Sobre o template enviado (link do Google Drive): não foi possível abrir esse link a partir daqui,
    porque este ambiente não tem acesso a `drive.google.com` (só a um conjunto restrito de domínios
    técnicos) e o link é de visualização privada. Por isso, recriei um template equivalente
    (balão de fala + nuvem de pensamento + boneco com a cabeça em branco para desenhar) diretamente
    no app. Se o template do Drive tiver um layout específico que você queira reproduzir com
    exatidão, me envie a imagem diretamente na conversa (upload de arquivo) que eu ajusto o desenho
    de fundo do canvas para bater com ele.


App multi-usuário: todos os facilitadores acessam a **mesma URL** e leem/gravam no **mesmo banco de dados**
(Supabase/Postgres). Os dados ficam salvos no banco a cada ação — se você fechar a aba, o teste continua
exatamente de onde parou (basta reabrir o link da sessão, ou reabrir o teste "em andamento" na aba Testes).

## 1. Criar o banco no Supabase (gratuito)

1. Crie uma conta em https://supabase.com e crie um novo projeto.
2. Vá em **SQL Editor > New query**, cole o conteúdo de `schema.sql` deste pacote e rode.
   - Se você já tinha rodado uma versão anterior deste projeto, o próprio `schema.sql` já inclui a linha
     `alter table techniques add column if not exists template_key text;` para atualizar a tabela existente
     sem perder os dados.
3. Vá em **Settings > API** e copie:
   - **Project URL** → vai virar `SUPABASE_URL`
   - **anon public key** → vai virar `SUPABASE_KEY`
     (para um app interno de equipe, a anon key com RLS desligado — já feito no `schema.sql` — é suficiente;
     dá para reforçar depois com Supabase Auth + RLS se quiser controlar quem edita o quê).

## 2. Colocar o código num repositório GitHub

Suba esta pasta inteira (`app.py`, `db.py`, `charts.py`, `pdf_export.py`, `requirements.txt`,
`packages.txt`, `schema.sql`) para um repositório no GitHub. **Não suba** o arquivo
`.streamlit/secrets.toml` (só o `.example`) — as chaves do Supabase são configuradas direto no
Streamlit Cloud, no passo 3. O `packages.txt` é lido automaticamente pelo Streamlit Community Cloud
para instalar pacotes do sistema (aqui, a fonte de emoji colorida usada nos gráficos). Não há mais
nenhuma dependência de componente de terceiros para o desenho da técnica 3E — só bibliotecas
mantidas ativamente (Streamlit, Pillow, matplotlib, fpdf2, supabase, pandas).

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
