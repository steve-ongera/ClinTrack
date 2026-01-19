# ============================================
# admin.py - Admin Interface Configuration
# ============================================

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Study, Participant, SUSAR, StaffAttendance, AuditLog

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'created_at']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number')}),
    )

@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'start_date', 'end_date']
    list_filter = ['is_active']
    search_fields = ['name', 'code']

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['participant_id', 'get_full_name', 'study', 'status', 'primary_phone', 'location']
    list_filter = ['study', 'status', 'gender']
    search_fields = ['participant_id', 'first_name', 'last_name', 'primary_phone']
    readonly_fields = ['created_at', 'updated_at', 'created_by']

@admin.register(SUSAR)
class SUSARAdmin(admin.ModelAdmin):
    list_display = ['susar_id', 'participant', 'severity', 'outcome', 'onset_date', 'reported_to_irb']
    list_filter = ['severity', 'outcome', 'reported_to_irb', 'reported_to_sponsor']
    search_fields = ['susar_id', 'participant__participant_id', 'event_description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'login_time', 'logout_time', 'location']
    list_filter = ['login_time', 'staff']
    readonly_fields = ['login_time']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'object_id', 'timestamp']
    list_filter = ['action', 'model_name', 'timestamp']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'changes', 'timestamp']

