-- Rode este script inteiro no SQL Editor do seu projeto Supabase (Supabase > SQL Editor > New query).
-- Cria toda a estrutura usada pelo app Campo.

create extension if not exists "pgcrypto";

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text default '',
  script text default '',
  created_at timestamptz default now()
);

create table if not exists members (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade,
  name text not null,
  email text default ''
);

create table if not exists techniques (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade,
  name text not null,
  type text not null default 'emocards', -- 'emocards' ou 'notes'
  labels jsonb default '["Muito insatisfeito","Insatisfeito","Levemente insatisfeito","Neutro","Levemente satisfeito","Satisfeito","Muito satisfeito","Encantado"]',
  created_at timestamptz default now()
);

create table if not exists technique_tasks (
  id uuid primary key default gen_random_uuid(),
  technique_id uuid references techniques(id) on delete cascade,
  task_name text not null,
  order_index int not null default 0
);

create table if not exists tests (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade,
  tester text not null,
  co_testers text default '',
  participant text not null,
  test_datetime timestamptz default now(),
  status text not null default 'ongoing', -- 'ongoing' ou 'done'
  created_at timestamptz default now()
);

create table if not exists entries (
  id uuid primary key default gen_random_uuid(),
  test_id uuid references tests(id) on delete cascade,
  technique_id uuid references techniques(id) on delete cascade,
  task_name text not null,
  emotion int, -- 1 a 8, usado quando a técnica é 'emocards'
  note text,   -- usado quando a técnica é 'notes'
  created_at timestamptz default now()
);

-- Por simplicidade, o app usa a chave anônima do Supabase e o RLS fica desligado
-- (qualquer pessoa com o link do app e acesso à internet consegue ler/escrever).
-- Isso é razoável para uma ferramenta interna entre facilitadores de confiança.
-- Se quiser reforçar a segurança depois, habilite RLS + Supabase Auth nas tabelas acima.
alter table projects disable row level security;
alter table members disable row level security;
alter table techniques disable row level security;
alter table technique_tasks disable row level security;
alter table tests disable row level security;
alter table entries disable row level security;
