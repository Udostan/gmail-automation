-- Create email_templates table
create table if not exists email_templates (
    id uuid default uuid_generate_v4() primary key,
    name text not null,
    subject text not null,
    content text not null,
    tags text[] default array[]::text[],
    usage_count integer default 0,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create index for searching
create index if not exists idx_email_templates_name on email_templates using gin (name gin_trgm_ops);
create index if not exists idx_email_templates_subject on email_templates using gin (subject gin_trgm_ops);
create index if not exists idx_email_templates_tags on email_templates using gin (tags);

-- Add RLS policies
alter table email_templates enable row level security;

create policy "Users can create templates"
    on email_templates for insert
    with check (true);

create policy "Users can view their templates"
    on email_templates for select
    using (true);

create policy "Users can update their templates"
    on email_templates for update
    using (true);

create policy "Users can delete their templates"
    on email_templates for delete
    using (true);
