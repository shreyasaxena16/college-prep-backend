# Live Schema Validation Report

Date: 2026-05-20

Scope: Read-only validation from `college-prep-backend` using the backend Supabase client and `.env` credentials.

## Result

The backend's current Supabase credentials can query data tables, but cannot export the full schema through the Supabase/PostgREST OpenAPI endpoint. Supabase returned:

```text
401 Unauthorized
Secret API key required
Only secret API keys can be used for this endpoint.
```

The Supabase CLI path was also unavailable in this environment because the CLI is not installed and the download/install approval was rejected.

## Validated Tables and Columns

The following live checks succeeded:

- `profiles`: `id`, `firstname`, `lastname`, `username`, `role`
- `students`: `id`, `profile_id`
- `questions`: `id`, `subject`, `topic`, `difficulty`, `sat_band`, `question`, `options`, `correct_answer`, `explanation`
- `test_sessions`: `id`, `user_id`, `total_questions`, `current_index`, `score`, `status`, `created_at`
- `test_answers`: `id`, `session_id`, `question_id`, `selected_answer`, `is_correct`
- `attempts`: `user_id`, `question_id`, `selected_answer`, `is_correct`
- `student_attempts`: `student_id`, `question_id`, `selected_answer`, `is_correct`
- `todos`: `id`, `student_id`, `title`, `description`, `start_date`, `due_date`, `reminder_enabled`, `plan_id`
- `sat_prep_plan_templates`: `id`, `title`, `summary`, `duration_weeks`, `target_score_range`
- `sat_prep_plan_template_tasks`: `id`, `plan_template_id`, `sort_order`, `title`, `description`, `relative_start_day`, `relative_due_day`, `reminder_enabled`, `subtasks`
- `student_sat_prep_plans`: `id`, `student_id`, `plan_template_id`, `title`, `sat_date`, `target_score_range`

## Migration Compatibility Notes

- The proposed AI/RAG migration correctly reuses `profiles`, `students`, `questions`, `test_sessions`, `test_answers`, and `todos`.
- No duplicate user, student, question, test, or answer table is introduced.
- `questions` is the right place to add an optional embedding column for existing SAT question retrieval.
- Uploaded SAT retrieval should use source/chunk tables because uploaded files are not the same concept as generated questions.
- AI memory should be a separate table because it stores compact tutoring facts/preferences, not raw chat history or test answers.

## Remaining Verification Needed

To fully verify constraints, data types, foreign keys, indexes, and installed extensions, one of these is still required:

- Supabase CLI access with `supabase db dump --schema public`
- A direct Postgres connection string for `pg_dump`/`psql`
- A Supabase secret API key with access to the OpenAPI schema endpoint
