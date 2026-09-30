# Frontend Figma copy

The expanded app prototype is documented in `connected-app-manifest.json`. All 60 screens are reachable from sign-in. It now has 1,412 interactive controls, 173 conditional actions, role flow menus, dropdown options, sample form entry, required-field validation, question flags, answer selection, add/remove editor rows, confirmation dialogs, and session reset. The destination and variable-reference audit found no invalid references.

Use Present on prototype page 169:35, starting at login 170:35. The floating Flows control opens all role and scenario screens. Click fields to populate sample values. Free keyboard entry, real file uploads, camera access and backend requests are simulated rather than performed by Figma.

The `Frontend prototype — AI-Vigilation` page (169:35) adds clickable role flows across 60 copied screens and three logout overlays. Use Present and select a flow starting point. It has 503 clickable nodes, 185 Default/Hover component sets, and three automatic transitions. Hover styling was measured from the actual Vue components. The 900 ms identity-success delay matches the source; verification and loading responses are simulated.

See `prototype-manifest.json` for the prototype frame IDs and verification results. Form entry, filtering, camera verification, and backend mutations remain represented by synthetic design states. Original copied pages are preserved.

Editable frontend designs were copied to the existing AI-VIGILATION Figma file. See manifest.json for page and frame IDs.

These preview files render the actual Vue components with isolated synthetic fixtures. Lifecycle callbacks are disabled so no backend, camera, or proctoring services run. The application source was not changed.

Run from examfrontend: `node node_modules/vite/bin/vite.js --config output/figma/vite.config.mjs --configLoader native`.

The capture IDs in capture-plan.json have already been consumed. Do not reuse them. To inspect a screen without capturing, open `http://127.0.0.1:5174/output/figma/preview.html?screen=student-dashboard`.

Verification covered page inventory, editable text counts, frame overlap, and visual comparisons of login, course detail, instructor dashboard, question editor, admin student list, profile editing, and mobile layouts. Native Arial controls use metrically similar Arimo in Figma.
