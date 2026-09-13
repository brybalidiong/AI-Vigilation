from django.contrib import admin

from .models import ExamSet, EnrolledStudent, StudentSet, Subject, SubjectEnrollment, UserProfile


@admin.register(StudentSet)
class StudentSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    search_fields = ('name',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'is_enrolled')
    list_editable = ('role', 'is_enrolled')
    search_fields = ('user__email',)


@admin.register(EnrolledStudent)
class EnrolledStudentAdmin(admin.ModelAdmin):
    list_display = ('email', 'student_set', 'created_at')
    search_fields = ('email',)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'instructor', 'created_at')
    search_fields = ('code', 'name', 'instructor__username')


@admin.register(SubjectEnrollment)
class SubjectEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('email', 'subject', 'created_at')
    search_fields = ('email', 'subject__code', 'subject__name')


@admin.register(ExamSet)
class ExamSetAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'created_at')
    search_fields = ('title', 'subject__code', 'subject__name')
