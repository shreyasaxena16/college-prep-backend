create table if not exists public.sat_prep_plan_templates (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  summary text,
  duration_weeks integer not null,
  target_score_range text not null check (
    target_score_range in ('1000-1200', '1200-1400', '1400+')
  ),
  created_at timestamptz not null default now(),
  unique (duration_weeks, target_score_range)
);

create table if not exists public.sat_prep_plan_template_tasks (
  id uuid primary key default gen_random_uuid(),
  plan_template_id uuid not null references public.sat_prep_plan_templates(id) on delete cascade,
  sort_order integer not null default 0,
  title text not null,
  description text,
  relative_start_date date,
  relative_due_date date,
  reminder_enabled boolean not null default true,
  subtasks jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.student_sat_prep_plans (
  id uuid primary key default gen_random_uuid(),
  student_id uuid not null,
  plan_template_id uuid not null references public.sat_prep_plan_templates(id),
  title text not null,
  sat_date date not null,
  target_score_range text not null check (
    target_score_range in ('1000-1200', '1200-1400', '1400+')
  ),
  created_at timestamptz not null default now(),
  unique (student_id, plan_template_id, sat_date)
);

alter table public.todos
add column if not exists plan_id uuid references public.student_sat_prep_plans(id) on delete set null;

create index if not exists idx_sat_plan_templates_reuse
on public.sat_prep_plan_templates(duration_weeks, target_score_range);

create index if not exists idx_sat_plan_template_tasks_template
on public.sat_prep_plan_template_tasks(plan_template_id, sort_order);

create index if not exists idx_student_sat_prep_plans_student
on public.student_sat_prep_plans(student_id);

create index if not exists idx_todos_plan_id
on public.todos(plan_id);
