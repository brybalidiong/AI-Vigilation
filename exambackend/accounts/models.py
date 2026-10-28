from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    ]
    INSTITUTE_CHOICES = [
        ('IC', 'Institute of Computing'),
        ('ITED', 'Institute of Teachers Education'),
        ('IASS', 'Institute of Acquatic and Applied Sciences'),
        ('ILEGG', 'Institute of Leadership, Entrepreneurship and Good Governance'),
    ]

    FACE_STATUS_NONE     = 'none'
    FACE_STATUS_PENDING  = 'pending'
    FACE_STATUS_APPROVED = 'approved'
    FACE_STATUS_CHOICES  = [
        (FACE_STATUS_NONE,     'None'),
        (FACE_STATUS_PENDING,  'Pending'),
        (FACE_STATUS_APPROVED, 'Approved'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    institute = models.CharField(max_length=5, choices=INSTITUTE_CHOICES, blank=True, default='')
    is_enrolled = models.BooleanField(default=False)
    google_photo = models.URLField(blank=True, null=True)
    custom_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True, default='')
    face_photo = models.ImageField(upload_to='face_photos/', null=True, blank=True)
    face_encoding = models.TextField(null=True, blank=True)  # JSON-serialized face embedding
    id_verified_at = models.DateTimeField(null=True, blank=True)
    # ── Face approval workflow ──────────────────────────────────────────────
    face_status = models.CharField(
        max_length=10,
        choices=FACE_STATUS_CHOICES,
        default=FACE_STATUS_NONE,
    )
    face_pending_photo = models.ImageField(
        upload_to='face_pending/', null=True, blank=True,
        help_text='Student-submitted photo awaiting admin approval.',
    )
    face_reupload_allowed = models.BooleanField(
        default=False,
        help_text='Admin toggle: when True the student may submit a new face photo.',
    )

    def __str__(self):
        return f'{self.user.email} - {self.role}'



class StudentSet(models.Model):
    """Named roster (e.g. class section) created by an instructor."""

    name = models.CharField(max_length=200)
    subject = models.ForeignKey(
        'Subject',
        on_delete=models.CASCADE,
        related_name='student_sets',
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_sets',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class EnrolledStudent(models.Model):
    """A student allowed to log in; belongs to exactly one roster set."""

    email = models.EmailField()
    student_set = models.ForeignKey(
        StudentSet,
        on_delete=models.CASCADE,
        related_name='students',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['email', 'student_set'],
                name='unique_email_per_student_set',
            ),
        ]

    def __str__(self):
        return self.email


class Subject(models.Model):
    CATEGORY_MINOR = 'MINOR'
    CATEGORY_CHOICES = UserProfile.INSTITUTE_CHOICES + [
        (CATEGORY_MINOR, 'Minor courses'),
    ]
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    category = models.CharField(max_length=5, choices=CATEGORY_CHOICES, blank=True, default='')
    instructor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subjects',
    )
    additional_instructors = models.ManyToManyField(
        User, blank=True, related_name='additional_subjects',
    )
    archived_by = models.ManyToManyField(
        User, blank=True, related_name='archived_subjects',
    )
    announcements = models.TextField(blank=True, default="")
    display_photo = models.ImageField(upload_to='course_photos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['instructor', 'code'],
                name='unique_subject_code_per_instructor',
            ),
        ]

    def __str__(self):
        return f'{self.code} - {self.name}'


class SubjectEnrollment(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['email']
        constraints = [
            models.UniqueConstraint(
                fields=['subject', 'email'],
                name='unique_email_per_subject',
            ),
        ]

    def __str__(self):
        return f'{self.email} @ {self.subject.code}'


class ExamSet(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='exam_sets',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    available_from = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    exam_file = models.FileField(upload_to='exam_uploads/', null=True, blank=True)
    is_final = models.BooleanField(default=False)
    max_attempts = models.PositiveIntegerField(default=1)
    time_limit = models.PositiveIntegerField(default=60)  # Time limit in minutes, 0 for unlimited
    allow_backtracking = models.BooleanField(default=True)
    detect_gaze_above = models.BooleanField(default=True)
    detect_gaze_below = models.BooleanField(default=True)
    detect_gaze_left = models.BooleanField(default=True)
    detect_gaze_right = models.BooleanField(default=True)
    detect_gadgets = models.BooleanField(default=True)
    assigned_sets = models.ManyToManyField('StudentSet', related_name='assigned_exams', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.subject.code}: {self.title}'


class ExamSubmission(models.Model):
    exam_set = models.ForeignKey(
        ExamSet,
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    student_email = models.EmailField()
    is_done = models.BooleanField(default=False)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    integrity_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    # Proctoring flags
    terminated = models.BooleanField(default=False)  # True if exam was force-ended by the system
    tab_switches = models.PositiveSmallIntegerField(default=0)  # Number of times student switched tabs
    attempt_count = models.PositiveIntegerField(default=1)  # Which attempt this submission represents
    question_index = models.PositiveIntegerField(default=0)
    locked_answers = models.JSONField(default=dict, blank=True)
    iris_verified_at = models.DateTimeField(null=True, blank=True)
    gaze_glance_count = models.PositiveSmallIntegerField(default=0)
    gaze_glance_last_frame_hash = models.CharField(max_length=64, blank=True, default='')
    latest_snapshot = models.ImageField(upload_to='snapshots/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['student_email']
        constraints = [
            models.UniqueConstraint(
                fields=['exam_set', 'student_email'],
                name='unique_submission_per_exam_student',
            ),
        ]

    def __str__(self):
        return f'{self.exam_set_id} - {self.student_email}'


class QuestionBankBatch(models.Model):
    """A named group of questions added to a course together."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='question_batches')
    name = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.subject_id}: {self.name}'


class QuestionBankItem(models.Model):
    """Reusable course question; exams receive independent copies."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='question_bank')
    batch = models.ForeignKey(QuestionBankBatch, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    question_type = models.CharField(max_length=20, choices=[
        ('multiple_choice', 'Multiple Choice'),
        ('identification', 'Identification'),
        ('enumeration', 'Enumeration'),
        ('essay', 'Essay'),
    ])
    question_text = models.TextField()
    choices = models.JSONField(null=True, blank=True)
    correct_answer = models.CharField(max_length=2000, null=True, blank=True)
    points = models.PositiveIntegerField(null=True, blank=True)
    max_words = models.PositiveIntegerField(null=True, blank=True)
    case_sensitive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.subject_id}: {self.question_text[:60]}'


class ExamQuestion(models.Model):
    """A single question inside an ExamSet created by the instructor."""

    TYPE_MULTIPLE_CHOICE = 'multiple_choice'
    TYPE_IDENTIFICATION = 'identification'
    TYPE_ENUMERATION = 'enumeration'
    TYPE_ESSAY = 'essay'
    QUESTION_TYPE_CHOICES = [
        (TYPE_MULTIPLE_CHOICE, 'Multiple Choice'),
        (TYPE_IDENTIFICATION, 'Identification'),
        (TYPE_ENUMERATION, 'Enumeration'),
        (TYPE_ESSAY, 'Essay'),
    ]

    exam_set = models.ForeignKey(
        ExamSet,
        on_delete=models.CASCADE,
        related_name='questions',
    )
    bank_item = models.ForeignKey(
        QuestionBankItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='exam_questions',
    )
    order = models.PositiveIntegerField(default=0)
    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPE_CHOICES,
        default=TYPE_MULTIPLE_CHOICE,
    )
    question_text = models.TextField()
    # JSON list of choice strings (Multiple Choice only)
    choices = models.JSONField(null=True, blank=True)
    # Correct answer string (MC / Identification) or newline-separated expected items (Enumeration)
    correct_answer = models.CharField(max_length=2000, null=True, blank=True)
    # Maximum score for essays or expected item count hint for enumeration.
    points = models.PositiveIntegerField(null=True, blank=True)
    # Optional essay answer limit; older questions remain unlimited.
    max_words = models.PositiveIntegerField(null=True, blank=True)
    # Whether grading for Identification / Enumeration is case-sensitive
    case_sensitive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'Q{self.order}: {self.question_text[:60]}'


class StudentAnswer(models.Model):
    """One student's answer to one question in an exam."""

    exam_set = models.ForeignKey(
        ExamSet,
        on_delete=models.CASCADE,
        related_name='student_answers',
    )
    question = models.ForeignKey(
        ExamQuestion,
        on_delete=models.CASCADE,
        related_name='student_answers',
    )
    student_email = models.EmailField()
    answer_text = models.TextField(blank=True, default='')
    # True/False for MC (auto-graded), None for open-ended types (manual grading)
    is_correct = models.BooleanField(null=True, blank=True)
    # Points assigned by the instructor for a subjective answer. A null value
    # means that the answer is still waiting for manual grading.
    awarded_points = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['question__order', 'question__created_at']
        indexes = [
            models.Index(
                fields=['exam_set', 'student_email'],
                name='acct_answer_exam_email_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['exam_set', 'question', 'student_email'],
                name='unique_answer_per_student_question',
            ),
        ]

    def __str__(self):
        return f'{self.student_email} – Q{self.question_id}'


class ExamProctoringEvent(models.Model):
    """Timestamped log of a student action during an exam attempt."""

    SEVERITY_INFO = 'info'
    SEVERITY_WARNING = 'warning'
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_CHOICES = [
        (SEVERITY_INFO, 'Info'),
        (SEVERITY_WARNING, 'Warning'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]

    EVENT_TAB_SWITCH = 'tab_switch'
    EVENT_WINDOW_BLUR = 'window_blur'
    EVENT_WINDOW_FOCUS = 'window_focus'
    EVENT_VISIBILITY_HIDDEN = 'visibility_hidden'
    EVENT_VISIBILITY_VISIBLE = 'visibility_visible'
    EVENT_SPLIT_SCREEN = 'split_screen'
    EVENT_EXTENDED_MONITOR = 'extended_monitor'
    EVENT_COPY_ATTEMPT = 'copy_attempt'
    EVENT_CUT_ATTEMPT = 'cut_attempt'
    EVENT_SCREENSHOT_ATTEMPT = 'screenshot_attempt'
    EVENT_SCREEN_SHARE_STOPPED = 'screen_share_stopped'
    EVENT_RIGHT_CLICK = 'right_click'
    EVENT_EXAM_STARTED = 'exam_started'
    EVENT_EXAM_SUBMITTED = 'exam_submitted'
    EVENT_EXAM_TERMINATED = 'exam_terminated'
    EVENT_TIME_UP = 'time_up'
    EVENT_PERIODIC_CAPTURE = 'periodic_capture'
    EVENT_GAZE_VIOLATION = 'gaze_violation'
    EVENT_GAZE_NO_FACE = 'gaze_no_face'
    EVENT_GADGET_DETECTED = 'gadget_detected'
    EVENT_WARNING_SHOWN = 'warning_shown'
    EVENT_TYPES = [
        (EVENT_TAB_SWITCH, 'Tab switch'),
        (EVENT_WINDOW_BLUR, 'Window blur'),
        (EVENT_WINDOW_FOCUS, 'Window focus'),
        (EVENT_VISIBILITY_HIDDEN, 'Tab hidden'),
        (EVENT_VISIBILITY_VISIBLE, 'Tab visible'),
        (EVENT_SPLIT_SCREEN, 'Split screen'),
        (EVENT_EXTENDED_MONITOR, 'Extended monitor'),
        (EVENT_COPY_ATTEMPT, 'Copy attempt'),
        (EVENT_CUT_ATTEMPT, 'Cut attempt'),
        (EVENT_SCREENSHOT_ATTEMPT, 'Screenshot attempt'),
        (EVENT_SCREEN_SHARE_STOPPED, 'Screen sharing stopped'),
        (EVENT_RIGHT_CLICK, 'Right click'),
        (EVENT_EXAM_STARTED, 'Exam started'),
        (EVENT_EXAM_SUBMITTED, 'Exam submitted'),
        (EVENT_EXAM_TERMINATED, 'Exam terminated'),
        (EVENT_TIME_UP, 'Time up'),
        (EVENT_PERIODIC_CAPTURE, 'Periodic capture'),
        (EVENT_GAZE_VIOLATION, 'Gaze away from screen'),
        (EVENT_GAZE_NO_FACE, 'Face not visible'),
        (EVENT_GADGET_DETECTED, 'Prohibited gadget detected'),
        (EVENT_WARNING_SHOWN, 'Warning displayed'),
    ]

    submission = models.ForeignKey(
        ExamSubmission,
        on_delete=models.CASCADE,
        related_name='proctoring_events',
    )
    attempt_number = models.PositiveIntegerField(default=1)
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES)
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_WARNING,
    )
    message = models.TextField(blank=True, default='')
    source = models.CharField(max_length=80, blank=True, default='')
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['submission', 'attempt_number']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return f'{self.submission_id} [{self.event_type}] @ {self.created_at}'


class ExamProctoringEvidence(models.Model):
    """Screenshot or webcam capture proving proctoring state during an exam."""

    TYPE_WEBCAM = 'webcam'
    TYPE_SCREEN = 'screen'
    EVIDENCE_TYPES = [
        (TYPE_WEBCAM, 'Webcam'),
        (TYPE_SCREEN, 'Screen'),
    ]

    submission = models.ForeignKey(
        ExamSubmission,
        on_delete=models.CASCADE,
        related_name='proctoring_evidence',
    )
    event = models.ForeignKey(
        ExamProctoringEvent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evidence',
    )
    attempt_number = models.PositiveIntegerField(default=1)
    evidence_type = models.CharField(max_length=20, choices=EVIDENCE_TYPES, default=TYPE_WEBCAM)
    image = models.ImageField(upload_to='proctoring_evidence/%Y/%m/')
    caption = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['submission', 'attempt_number']),
        ]

    def __str__(self):
        return f'{self.submission_id} {self.evidence_type} @ {self.created_at}'


class ExamIntegrityReport(models.Model):
    """Summary report for instructors: integrity score proof for one exam attempt."""

    submission = models.ForeignKey(
        ExamSubmission,
        on_delete=models.CASCADE,
        related_name='integrity_reports',
    )
    attempt_number = models.PositiveIntegerField(default=1)
    integrity_score = models.DecimalField(max_digits=6, decimal_places=2)
    event_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    critical_count = models.PositiveIntegerField(default=0)
    evidence_count = models.PositiveIntegerField(default=0)
    tab_switch_count = models.PositiveIntegerField(default=0)
    gaze_violation_count = models.PositiveIntegerField(default=0)
    gaze_no_face_count = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)
    narrative = models.TextField(blank=True, default='')
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['submission', 'attempt_number'],
                name='unique_integrity_report_per_attempt',
            ),
        ]

    def __str__(self):
        return f'Report {self.submission_id} attempt {self.attempt_number} — {self.integrity_score}%'
