# OnlineInvigilator project knowledge

## Purpose

AI-Vigilation is a capstone online exam platform. It supports exam creation, student submissions, question grading, identity verification, live proctoring, and instructor integrity reports.

## User roles

| Role | Main activities |
| --- | --- |
| Student | Access assigned exams, verify identity, answer questions, and view results. |
| Instructor | Manage courses and exams, grade responses, and review integrity reports. |
| Admin | Manage users and courses, assign instructors, and oversee the platform. |

## Architecture

- **Frontend:** Vue 3, Vite, Vue Router, Axios, and Firebase JavaScript SDK in `examfrontend/`.
- **Device access:** The frontend entry point shows a blocking message on phones and tablets, including iPads requesting desktop mode, before it initializes the router or Firebase. Users must open the site on a laptop or desktop computer. This client-side check identifies common devices but cannot guarantee exclusion when browser device properties are deliberately spoofed.
- **Backend:** Django, Django REST Framework, and Channels in `exambackend/`.
- **Database:** PostgreSQL/Supabase, with an optional local SQLite configuration.
- **Identity:** Firebase integration, DNSC student ID OCR in `exambackend/accounts/student_id_service.py`, and OpenCV YuNet/SFace models in `exambackend/accounts/face_service.py`. Students upload the front of their DNSC ID; the backend reads the school header, STUDENT label, and printed first/last name, compares the name with the admin-managed account name, and stores an embedding from the ID portrait. The exam precheck compares the webcam face with that portrait. A failed or unreadable ID is rejected without changing verification state. Previously approved face photos require a new ID upload. OCR/name matching does not establish that an ID card is genuine.
- **Exam face liveness:** The verification dialog first confirms a clearly visible face and shows the live camera preview. It then prompts the student to blink before the ID portrait comparison. A short webcam sequence is analyzed on the backend for both eyes open, closed, then reopened; a single still photo cannot pass. The matching face is taken from the reopened frame. This basic motion check does not establish camera authenticity and may still be defeated by a replayed video or a manipulated client.
- **Proctoring:** Gaze tracking uses MediaPipe and TensorFlow Lite; gadget detection lives in `exambackend/accounts/gadget_service.py`.

Role dashboards live in `examfrontend/src/views/`. Most API logic is in `exambackend/accounts/views.py`, with REST routes in `urls.py` and database models in `models.py`.

Admins create courses and assign one or more active instructors to each course.
A course belongs to one institute (IC, ITED, IASS, or ILEGG) or the separate
Minor courses group. Institute courses can be assigned only to instructors in
that institute; minor courses can be assigned to instructors from any institute.
The original instructor field remains the lead instructor for legacy data and
student-facing labels; additional instructors share access to exams and rosters.
Existing courses inherit the lead instructor's institute during migration when
it is known. Admin reassignment preserves the course, exams, and student sets.
Instructors cannot create or delete courses. They can change an assigned course
banner and archive a course from their own active list. Each instructor has an
independent archive; restoring returns the course to that instructor's list.
Archiving does not remove exams, student records, or other instructors' access.

Exam uploads remain drafts. Publishing an exam sends a Django Channels event to
students enrolled in the course; their open dashboards refetch the authorized exam
list. The local in-memory channel layer supports one backend process. Deployments
with multiple processes set `REDIS_URL` for a shared Redis channel layer.
Each course has a reusable Question Bank organized into named batches. Instructors
create questions or import Aiken multiple-choice and blank-line-separated essay
prompts only on the course Question Bank page. For each question or import, they
choose an existing course batch or create a named batch. A new exam draft starts empty;
the instructor selects questions from the available bank batches before
publishing. Exam questions are independent copies linked to their bank source.
Deleting a bank question or an entire batch removes those sources but preserves questions already in
draft or published exams. Existing exam questions are added to the bank by the
question-bank migration and grouped by source exam in the batch migration. The
instructor exam preview stays compact and lets instructors reveal each answer.
New essay questions and essay imports let instructors set points and a maximum
word count. The point value is used for manual grading. Students see a live word
counter, and the server rejects answers above a configured limit. Older essay
questions without a word limit remain unrestricted.
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

Published exams shuffle question order and multiple-choice options for each student and attempt. The order stays the same if a student refreshes an active attempt; answers are still graded against their choice text.
Instructors can choose whether students may return to earlier questions when creating an exam. Existing exams allow it by default. In one-way exams, Next saves and locks the current answer on the server; refreshing resumes at the next question, and final grading uses locked answers for earlier questions.

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
- During an exam, a separate iris-visibility check uses the same analyzed gaze frame. The exam controls remain covered until a recent visible-iris result is confirmed; ordinary prescription glasses can pass when at least one iris is clear. The HTTP observation stores the latest confirmation for server-side answer and submission checks. The timer continues while visibility is being restored.

See [gaze documentation](docs/GAZE_PROCTORING.md) and the custom [gaze-proctoring skill](.agents/skills/gaze-proctoring/SKILL.md).

## Browser exam restrictions

Before an exam, students grant camera/microphone access and explicitly share their entire screen. The browser's display chooser must return a monitor capture; sharing just a tab or window cannot show what appears after switching away. Browser blur is recorded immediately so a fast tab change cannot be lost while waiting for a visibility callback. Leaving the exam tab or window, including minimizing it, records a persistent warning above other exam overlays and attempts to store a shared-display image linked to its Action Log event. The screen image is captured after a short delay so the shared monitor can show the destination tab; an immediate capture can still contain the exam page. Screen images are taken directly from the shared monitor track when supported, with a preview-video fallback for visible windows. Split-screen or window resizing and browser-visible screenshot attempts are logged separately, each with their own screen evidence and short action label. These browser events share a five-warning termination limit, while the submitted tab-switch count includes only departures from the exam window. Screenshot shortcuts visible to the browser receive a short focus-change grace period so their OS overlay does not also count as a tab switch. Stopping screen sharing during the exam also terminates it. Browser-visible copy, cut, and right-click attempts are logged, as are face-visibility and multiple-face notices when shown. Web browsers cannot read the URL of another tab or reliably prevent or detect operating-system screenshots; a screen image may also be unavailable if the student returns immediately or the capture stream fails. These restrictions do not alter gaze or gadget detection.

The precheck also requests browser display information and blocks exam entry if another display is connected or display checking is unavailable or denied. During an exam, display connection changes are monitored; an additional display shows a persistent warning until disconnected, adds one shared browser warning per continuous connection, and appears in the Action Log as an extended-monitor event. The site does not capture the additional display or observe activity on it. Browser display APIs have limited support and cannot detect every hardware configuration or operating-system workaround.

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
