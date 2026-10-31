# Online Invigilator — Database ERD

**Database:** Supabase PostgreSQL (schema: `public`)

## How to export as PDF

### Option A — HTML (recommended)
1. Open `docs/database-erd.html` in Chrome or Edge.
2. Press `Ctrl+P` → **Save as PDF**.
3. Set orientation to **Landscape**.

### Option B — Markdown + Mermaid CLI
```bash
npx @mermaid-js/mermaid-cli -i docs/database-erd.mmd -o docs/database-erd.pdf
```

---

## Entity Relationship Diagram

```mermaid
erDiagram
    auth_user ||--o| accounts_userprofile : "has"
    auth_user ||--o{ accounts_subject : "teaches"
    auth_user ||--o{ accounts_subject_additional_instructors : "shares courses"
    accounts_subject ||--o{ accounts_subject_additional_instructors : "has instructors"
    auth_user ||--o{ accounts_studentset : "creates"

    accounts_subject ||--o{ accounts_studentset : "has rosters"
    accounts_subject ||--o{ accounts_subjectenrollment : "enrolls"
    accounts_subject ||--o{ accounts_examset : "has exams"

    accounts_studentset ||--o{ accounts_enrolledstudent : "contains"
    accounts_studentset }o--o{ accounts_examset : "assigned to"

    accounts_examset ||--o{ accounts_examsubmission : "submissions"
    accounts_examset ||--o{ accounts_examquestion : "questions"
    accounts_examset ||--o{ accounts_studentanswer : "answers"

    accounts_examquestion ||--o{ accounts_studentanswer : "answered"

    auth_user {
        int id PK
        varchar username
        varchar email
    }

    accounts_userprofile {
        bigint id PK
        int user_id FK
        varchar role
        varchar institute
        boolean is_enrolled
    }

    accounts_subject {
        bigint id PK
        int instructor_id FK
        varchar name
        varchar code
        varchar category
    }

    accounts_subject_additional_instructors {
        bigint id PK
        bigint subject_id FK
        int user_id FK
    }

    accounts_studentset {
        bigint id PK
        bigint subject_id FK
        int created_by_id FK
        varchar name
    }

    accounts_enrolledstudent {
        bigint id PK
        bigint student_set_id FK
        varchar email
    }

    accounts_subjectenrollment {
        bigint id PK
        bigint subject_id FK
        varchar email
    }

    accounts_examset {
        bigint id PK
        bigint subject_id FK
        varchar title
        int max_attempts
        int time_limit
    }

    accounts_examset_assigned_sets {
        bigint examset_id FK
        bigint studentset_id FK
    }

    accounts_examsubmission {
        bigint id PK
        bigint exam_set_id FK
        varchar student_email
        numeric score
        varchar gaze_model_code
    }

    accounts_examquestion {
        bigint id PK
        bigint exam_set_id FK
        varchar question_type
        jsonb choices
    }

    accounts_studentanswer {
        bigint id PK
        bigint exam_set_id FK
        bigint question_id FK
        varchar student_email
        boolean is_correct
    }
```

## Table summary

| Table | Function |
|-------|----------|
| `auth_user` | Login accounts |
| `accounts_userprofile` | Role and profile data |
| `accounts_subject` | Courses |
| `accounts_studentset` | Student rosters |
| `accounts_enrolledstudent` | Emails in a roster |
| `accounts_subjectenrollment` | Emails enrolled in a course |
| `accounts_examset` | Exams/assignments |
| `accounts_examset_assigned_sets` | Exam ↔ roster assignment |
| `accounts_examsubmission` | Student exam attempts |
| `accounts_examquestion` | Exam questions |
| `accounts_studentanswer` | Student answers |
