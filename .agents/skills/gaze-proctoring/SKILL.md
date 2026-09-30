---
name: gaze-proctoring
description: Update or debug OnlineInvigilator gaze streaming, strike counting, warnings, and exam termination. Use for gaze proctoring rather than face enrollment or general camera UI.
---

# Gaze proctoring

1. Read `docs/GAZE_PROCTORING.md`, then trace the affected flow through `examfrontend/src/views/StudentDashboardView.vue`, `exambackend/accounts/consumers.py`, `gaze_service.py`, and the gaze endpoint in `views.py`.
2. Keep one WebSocket frame in flight at a time. Preserve HTTP fallback, reject stale results, and keep a frame receipt paired with the exact image that was analyzed.
3. Preserve unmirrored inference frames and instructor direction restrictions. Keep backend strike counts authoritative. Current default limits are eight look-away strikes and five no-face strikes; update backend, frontend, and documentation together if the request changes them.
4. Verify with `node --test tests/gaze-loop.test.js` from `examfrontend` and `python manage.py test accounts.test_gaze_pipeline` from `exambackend` using `USE_LOCAL_SQLITE=1`, as relevant to the change. Build the frontend if its code changed. Report missing model assets or dependencies if they block live inference.

Report the behavior changed and checks performed. Use synthetic frames or mocks for automated tests; keep real webcam evidence out of test fixtures and logs.
