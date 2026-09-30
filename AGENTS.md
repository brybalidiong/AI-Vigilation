# OnlineInvigilator project guide

AI-Vigilation is an online exam platform with student, instructor, and admin roles. It uses Vue 3 and Vite for the frontend, Django REST Framework and Channels for the backend, and Firebase, Azure Face API, and local gaze/gadget models for identity and proctoring.

Read [knowledge.md](knowledge.md) for project architecture, roles, grading behavior, and proctoring context.

## Where to work

- `examfrontend/src/views/`: role dashboards and exam-taking UI.
- `examfrontend/src/components/`: shared UI, face verification, and proctoring overlay.
- `examfrontend/src/router/index.js`: frontend routes and role guards.
- `exambackend/accounts/views.py` and `urls.py`: REST handlers and routes.
- `exambackend/accounts/models.py` and `migrations/`: database models and schema changes.
- `exambackend/accounts/grading.py`: question grading rules.
- `exambackend/accounts/consumers.py`, `gaze_service.py`, and `gadget_service.py`: live proctoring.
- `exambackend/gaze_tracker/`: gaze inference and model assets.
- `docs/GAZE_PROCTORING.md`: gaze flow; `docs/database-erd.md`: database reference.

Read the relevant implementation before editing. If documentation and code disagree, verify the behavior and update the affected documentation.

## Working rules

- Keep changes focused on the requested feature and follow nearby code conventions.
- Enforce roles and exam ownership on the backend; frontend route guards alone are insufficient.
- Keep API fields consistent between Django handlers and Vue callers.
- Preserve exam timing, attempt limits, grading, and proctoring behavior unless the request changes them.
- Add a Django migration when a model change affects the database schema.
- Keep credentials, student photos, webcam evidence, and real student data out of source control and test fixtures. Use synthetic data for verification.

## Local commands

Use the project's Python environment and installed Node dependencies.

| Task | Directory | Command |
| --- | --- | --- |
| Start backend | `exambackend` | `python manage.py runserver` |
| Check Django configuration | `exambackend` | `python manage.py check` |
| Run backend tests | `exambackend` | `python manage.py test accounts` |
| Start frontend | `examfrontend` | `npm run dev` |
| Build frontend | `examfrontend` | `npm run build` |
| Test gaze loop | `examfrontend` | `node --test tests/gaze-loop.test.js` |

Run checks relevant to the change and report any missing dependencies or services. There is no frontend `npm test` script. For isolated backend tests, set `USE_LOCAL_SQLITE=1` in the test process; in PowerShell, use `$env:USE_LOCAL_SQLITE = '1'` before the test command. Do not use a shared Supabase database for tests.

The student dashboard reads `VITE_BACKEND_URL`, defaulting to `http://localhost:8000`. Backend database configuration is in `exambackend/exambackend/settings.py`. Gaze model binaries are excluded from Git; see `exambackend/scripts/sync_gaze_assets.py` and `GAZE_ASSETS_DIR` when inference assets are missing.

## Four project skills

Skills are stored in `.agents/skills/` so they travel with this project. Load only the skill relevant to the task.

| Skill | Origin | Use |
| --- | --- | --- |
| [playwright](.agents/skills/playwright/SKILL.md) | OpenAI provider | Browser checks for login, dashboards, and exam flows. |
| [security-best-practices](.agents/skills/security-best-practices/SKILL.md) | OpenAI provider | Requested security reviews or secure coding guidance for Python and JavaScript. |
| [exam-grading](.agents/skills/exam-grading/SKILL.md) | Custom | Update or debug question grading and instructor scoring. |
| [gaze-proctoring](.agents/skills/gaze-proctoring/SKILL.md) | Custom | Update or debug gaze frames, warnings, and exam termination. |

Provider source: `openai/skills`, paths `skills/.curated/playwright` and `skills/.curated/security-best-practices`, downloaded on 2026-09-29. Their original instructions and supporting files are retained. Their examples may assume a user-level install: resolve paths from the actual project skill folder. On Windows, Playwright CLI can be invoked with `npx --package @playwright/cli playwright-cli`; its bundled `.sh` wrapper requires Bash. Installing these skills does not install browser runtimes or application dependencies.

Example requests: "Use $exam-grading to fix enumeration partial credit" or "Use $gaze-proctoring to investigate repeated gaze warnings."
