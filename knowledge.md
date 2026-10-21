# OnlineInvigilator project knowledge

## Purpose

AI-Vigilation is a capstone online exam platform. It supports exam creation, student submissions, question grading, identity verification, live proctoring, and instructor integrity reports.

## User roles

| Role | Main activities |
| --- | --- |
| Student | Access assigned exams, verify identity, answer questions, and view results. |
| Instructor | Manage courses and exams, grade responses, and review integrity reports. |
| Admin | Manage users and oversee the platform. |

## Architecture

- **Frontend:** Vue 3, Vite, Vue Router, Axios, and Firebase JavaScript SDK in `examfrontend/`.
- **Device access:** The frontend entry point shows a blocking message on phones and tablets, including iPads requesting desktop mode, before it initializes the router or Firebase. Users must open the site on a laptop or desktop computer. This client-side check identifies common devices but cannot guarantee exclusion when browser device properties are deliberately spoofed.
- **Backend:** Django, Django REST Framework, and Channels in `exambackend/`.
- **Database:** PostgreSQL/Supabase, with an optional local SQLite configuration.
- **Identity:** Firebase integration, DNSC student ID OCR in `exambackend/accounts/student_id_service.py`, and OpenCV YuNet/SFace models in `exambackend/accounts/face_service.py`. Students upload the front of their DNSC ID; the backend reads the school header, STUDENT label, and printed first/last name, compares the name with the admin-managed account name, and stores an embedding from the ID portrait. The exam precheck compares the webcam face with that portrait. A failed or unreadable ID is rejected without changing verification state. Previously approved face photos require a new ID upload. OCR/name matching does not establish that an ID card is genuine.
- **Proctoring:** Gaze tracking uses MediaPipe and TensorFlow Lite; gadget detection lives in `exambackend/accounts/gadget_service.py`.

Role dashboards live in `examfrontend/src/views/`. Most API logic is in `exambackend/accounts/views.py`, with REST routes in `urls.py` and database models in `models.py`.

Exam uploads remain drafts. Publishing an exam sends a Django Channels event to
students enrolled in the course; their open dashboards refetch the authorized exam
list. The local in-memory channel layer supports one backend process. Deployments
with multiple processes set `REDIS_URL` for a shared Redis channel layer.
Production settings read credentials, hosts, origins, and media storage from
environment variables. See [deployment guide](docs/DEPLOYMENT.md).
The planned first deployment serves Vue from Vercel and Django/Daphne behind
Caddy on an Azure for Students Linux VM, with Redis for Channels and the
existing Supabase project for PostgreSQL and private S3-compatible media
storage. Student credit is finite; verify the model dependencies on Linux and
load test before a real exam.

## Question grading

The grading helper is `exambackend/accounts/grading.py`.

| Question type | Current behavior |
| --- | --- |
| Multiple choice | Case-insensitive answer matching. |
| Identification | Normalized text matching; accepted alternatives use `|`. Supports case-sensitive matching. |
| Enumeration | Partial credit based on matched expected items. Supports case-sensitive matching. |
| Essay | Requires manual grading. |

For grading changes, use the custom [exam-grading skill](.agents/skills/exam-grading/SKILL.md).

## Gaze proctoring

The current gaze and gadget detection behavior is a protected baseline. Work on
dashboards, exam flows, APIs, styling, performance, or deployment must preserve
both detectors unless the user explicitly requests a change to gaze detection or
gadget detection. This includes their model inference, sensitivity thresholds,
frame cadence, direction or object labels, warnings, evidence capture, and strike
handling. Shared files can still be edited for other features, but those detector
paths and their behavior should remain unchanged. For an explicitly requested
detector change, update only the relevant detector behavior and verify it with
focused tests.

During an exam, `StudentDashboardView.vue` sends webcam frames through the gaze WebSocket. One frame is sent at a time; HTTP fallback supports strike counting when the WebSocket is unavailable.

- WebSocket route: `/ws/student/exams/<exam_id>/proctoring/gaze/`.
- HTTP route: `POST /api/student/exams/<exam_id>/proctoring/gaze/`.
- A signed frame receipt associates an inference result with the exact analyzed image.
- Inference receives unmirrored pixels even when the preview is mirrored.
- Instructor settings control which gaze directions are restricted.
- Current default termination limits are eight look-away strikes and five no-face strikes.

See [gaze documentation](docs/GAZE_PROCTORING.md) and the custom [gaze-proctoring skill](.agents/skills/gaze-proctoring/SKILL.md).

## Browser exam restrictions

Before an exam, students grant camera/microphone access and explicitly share their entire screen. The browser's display chooser must return a monitor capture; sharing just a tab or window cannot show what appears after switching away. Leaving the exam tab or window, including minimizing it, records a tab-switch warning and attempts to store a screen image linked to that event. The fifth warning terminates the attempt. Stopping screen sharing during the exam also terminates it. Screenshot shortcuts that reach the page are logged as attempts. Web browsers cannot read the URL of another tab or reliably prevent or detect operating-system screenshots; a screen image may also be unavailable if the student returns immediately or the capture stream fails. These restrictions do not alter gaze or gadget detection.

## Configuration facts

- The student dashboard reads `VITE_BACKEND_URL`, defaulting to `http://localhost:8000`.
- Backend configuration is in `exambackend/exambackend/settings.py`; it loads `exambackend/.env`.
- `USE_LOCAL_SQLITE=1` selects local SQLite for isolated development and tests.
- Gaze model binaries are excluded from Git. See `exambackend/scripts/sync_gaze_assets.py`; `GAZE_ASSETS_DIR` can override the asset location.
- Credentials and real student photos or webcam evidence must stay out of committed documentation and fixtures.

## Skills and supporting documents

The project has two provider skills and two simple custom skills in `.agents/skills/`:

| Skill | Origin | Purpose |
| --- | --- | --- |
| [playwright](.agents/skills/playwright/SKILL.md) | OpenAI provider | Browser automation and UI-flow checks. |
| [security-best-practices](.agents/skills/security-best-practices/SKILL.md) | OpenAI provider | Requested security reviews and secure coding guidance. |
| [exam-grading](.agents/skills/exam-grading/SKILL.md) | Custom | Project-specific grading changes. |
| [gaze-proctoring](.agents/skills/gaze-proctoring/SKILL.md) | Custom | Project-specific gaze behavior changes. |

Use [AGENTS.md](AGENTS.md) for coding instructions and verification commands, [README.md](README.md) for setup, and [the database reference](docs/database-erd.md) for model relationships. Confirm facts against the implementation when changing behavior, and update this file when those facts change.
