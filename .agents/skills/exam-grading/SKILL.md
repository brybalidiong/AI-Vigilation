---
name: exam-grading
description: Update or debug question grading, partial credit, and instructor scoring in OnlineInvigilator. Use for grading behavior rather than general dashboard styling.
---

# Exam grading

1. Read `exambackend/accounts/grading.py` and the relevant question, answer, and submission models in `exambackend/accounts/models.py`.
2. Trace the affected handler in `exambackend/accounts/views.py`. Read the instructor or student dashboard only if the grading change affects its payload or display.
3. Make the smallest change that satisfies the request. Preserve existing rules unless explicitly changed: multiple choice is case-insensitive; identification supports alternatives separated by `|`; enumeration allows partial credit; essays require manual grading. Keep the question's `case_sensitive` option working for identification and enumeration.
4. Verify the changed behavior with a focused example or regression test. For grading helper changes, run `python manage.py test accounts.tests.GradingTests` from `exambackend` using `USE_LOCAL_SQLITE=1`. For instructor scoring changes, also run `accounts.tests.InstructorSubjectiveGradingTests`. Build the frontend if its code changed.

Report the rule changed and the verification result. Never expose answer keys in student responses before the exam flow permits them.
