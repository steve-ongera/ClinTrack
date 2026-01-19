# ============================================
# admin.py - Professional Admin Interface
# ============================================

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from .models import User, Study, Participant, SUSAR, StaffAttendance, AuditLog

# Custom admin site header and title
admin.site.site_header = format_html(
    '<strong>ClinTrack</strong> <span style="font-size: 0.9em; color: #6c757d;">V1.0</span>'
)
admin.site.site_title = "ClinTrack Administration"
admin.site.index_title = "Clinical Research Management Dashboard"

# Custom filters
class ActiveStatusFilter(admin.SimpleListFilter):
    title = 'active status'
    parameter_name = 'active_status'
    
    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('screening', 'Screening'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(status='active')
        if self.value() == 'inactive':
            return queryset.filter(status__in=['completed', 'withdrawn', 'lost'])
        if self.value() == 'screening':
            return queryset.filter(status='screening')

class FollowUpRequiredFilter(admin.SimpleListFilter):
    title = 'follow-up required'
    parameter_name = 'follow_up'
    
    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(follow_up_required=True)
        if self.value() == 'no':
            return queryset.filter(follow_up_required=False)

class SeverityFilter(admin.SimpleListFilter):
    title = 'severity level'
    parameter_name = 'severity_level'
    
    def lookups(self, request, model_admin):
        return (
            ('critical', 'Critical (Severe+)'),
            ('moderate', 'Moderate'),
            ('mild', 'Mild'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'critical':
            return queryset.filter(severity__in=['severe', 'life_threatening', 'fatal'])
        if self.value() == 'moderate':
            return queryset.filter(severity='moderate')
        if self.value() == 'mild':
            return queryset.filter(severity='mild')

# Admin Actions
@admin.action(description='Mark selected studies as active')
def make_active(modeladmin, request, queryset):
    queryset.update(is_active=True)
    modeladmin.message_user(request, f"{queryset.count()} studies marked as active.", messages.SUCCESS)

@admin.action(description='Mark selected studies as inactive')
def make_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)
    modeladmin.message_user(request, f"{queryset.count()} studies marked as inactive.", messages.WARNING)

@admin.action(description='Export selected participants data')
def export_participants(modeladmin, request, queryset):
    modeladmin.message_user(request, f"Exporting data for {queryset.count()} participants...", messages.INFO)

@admin.action(description='Mark SUSARs as reported to IRB')
def mark_reported_to_irb(modeladmin, request, queryset):
    updated = queryset.update(reported_to_irb=True, irb_report_date=timezone.now().date())
    modeladmin.message_user(request, f"{updated} SUSARs marked as reported to IRB.", messages.SUCCESS)

# Custom CSS for admin - Simplified approach
class ClinTrackAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
            )
        }

# Model Admins
@admin.register(User)
class UserAdmin(ClinTrackAdmin, BaseUserAdmin):
    list_display = ['username', 'email', 'role_badge', 'is_active_badge', 'created_at_formatted']
    list_filter = ['role', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('ClinTrack Information', {
            'fields': ('role', 'phone_number'),
            'classes': ('collapse', 'wide'),
        }),
    )
    
    def role_badge(self, obj):
        colors = {
            'admin': 'danger',
            'coordinator': 'warning',
            'staff': 'primary',
            'viewer': 'secondary',
        }
        color = colors.get(obj.role, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    role_badge.admin_order_field = 'role'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge bg-success">Active</span>')
        return format_html('<span class="badge bg-secondary">Inactive</span>')
    is_active_badge.short_description = 'Status'
    is_active_badge.admin_order_field = 'is_active'
    
    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_formatted.short_description = 'Created'
    created_at_formatted.admin_order_field = 'created_at'

@admin.register(Study)
class StudyAdmin(ClinTrackAdmin):
    list_display = ['name', 'code', 'participant_count', 'active_status', 'dates']
    list_filter = ['is_active', 'start_date']
    search_fields = ['name', 'code', 'description']
    actions = [make_active, make_inactive]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description'),
            'classes': ('wide',),
        }),
        ('Study Timeline', {
            'fields': ('start_date', 'end_date', 'is_active'),
            'classes': ('collapse',),
        }),
        ('Statistics', {
            'fields': ('get_participant_stats',),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['get_participant_stats']
    
    def participant_count(self, obj):
        total = obj.participants.count()
        active = obj.participants.filter(status='active').count()
        return format_html(
            '{} <small class="text-muted">({} active)</small>',
            total,
            active
        )
    participant_count.short_description = 'Participants'
    
    def active_status(self, obj):
        if obj.is_active:
            return format_html('<span class="badge bg-success">Active</span>')
        return format_html('<span class="badge bg-secondary">Inactive</span>')
    active_status.short_description = 'Status'
    
    def dates(self, obj):
        if obj.start_date and obj.end_date:
            return format_html(
                '{} - {}',
                obj.start_date.strftime('%Y-%m'),
                obj.end_date.strftime('%Y-%m')
            )
        elif obj.start_date:
            return format_html(
                'Started {}',
                obj.start_date.strftime('%Y-%m')
            )
        return '-'
    dates.short_description = 'Timeline'
    
    def get_participant_stats(self, obj):
        status_counts = obj.participants.values('status').annotate(count=Count('id'))
        stats_html = '<ul class="list-unstyled">'
        for stat in status_counts:
            stats_html += f'<li><strong>{stat["status"].title()}:</strong> {stat["count"]}</li>'
        stats_html += '</ul>'
        return format_html(stats_html)
    get_participant_stats.short_description = 'Participant Statistics'

@admin.register(Participant)
class ParticipantAdmin(ClinTrackAdmin):
    list_display = ['participant_id', 'full_name', 'study_link', 'status_pill', 'location', 'contact_info']
    list_filter = [ActiveStatusFilter, 'study', 'gender', 'county']
    search_fields = ['participant_id', 'first_name', 'last_name', 'primary_phone', 'email']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'get_related_susars']
    actions = [export_participants]
    fieldsets = (
        ('Identification', {
            'fields': ('participant_id', 'study'),
            'classes': ('wide',),
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'gender'),
            'classes': ('collapse',),
        }),
        ('Contact Information', {
            'fields': ('primary_phone', 'secondary_phone', 'email'),
            'classes': ('collapse',),
        }),
        ('Location Information', {
            'fields': ('location', 'sub_location', 'county', 'nearest_landmark'),
            'classes': ('collapse',),
        }),
        ('Study Status', {
            'fields': ('status', 'enrollment_date', 'notes'),
            'classes': ('wide',),
        }),
        ('Related SUSARs', {
            'fields': ('get_related_susars',),
            'classes': ('collapse',),
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def full_name(self, obj):
        return format_html(
            '<strong>{}</strong><br><small class="text-muted">{}</small>',
            obj.get_full_name(),
            f"DOB: {obj.date_of_birth or 'N/A'}"
        )
    full_name.short_description = 'Name'
    full_name.admin_order_field = 'last_name'
    
    def study_link(self, obj):
        url = reverse('admin:clintrack_study_change', args=[obj.study.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.study.code
        )
    study_link.short_description = 'Study'
    study_link.admin_order_field = 'study'
    
    def status_pill(self, obj):
        colors = {
            'active': 'success',
            'screening': 'warning',
            'completed': 'info',
            'withdrawn': 'secondary',
            'lost': 'danger',
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge rounded-pill bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_pill.short_description = 'Status'
    status_pill.admin_order_field = 'status'
    
    def contact_info(self, obj):
        return format_html(
            '{}<br><small class="text-muted">{}</small>',
            obj.primary_phone,
            obj.email or 'No email'
        )
    contact_info.short_description = 'Contact'
    
    def get_related_susars(self, obj):
        susars = obj.susars.all()
        if susars:
            html = '<ul class="list-unstyled">'
            for susar in susars:
                url = reverse('admin:clintrack_susar_change', args=[susar.id])
                html += f'''
                <li class="mb-2">
                    <a href="{url}">{susar.susar_id}</a>
                    <br>
                    <small>
                        <span class="badge bg-{'danger' if susar.severity in ['severe', 'life_threatening', 'fatal'] else 'warning'}">
                            {susar.get_severity_display()}
                        </span>
                        {susar.onset_date.strftime('%Y-%m-%d')}
                    </small>
                </li>
                '''
            html += '</ul>'
            return format_html(html)
        return format_html('<span class="text-muted">No SUSARs reported</span>')
    get_related_susars.short_description = 'Related SUSARs'

@admin.register(SUSAR)
class SUSARAdmin(ClinTrackAdmin):
    list_display = ['susar_id', 'participant_link', 'severity_badge', 'outcome_badge', 'follow_up_status', 'dates']
    list_filter = [FollowUpRequiredFilter, SeverityFilter, 'outcome', 'reported_to_irb', 'reported_to_sponsor', 'onset_date']
    search_fields = ['susar_id', 'participant__participant_id', 'event_description']
    readonly_fields = ['created_at', 'updated_at', 'get_timeline']
    actions = [mark_reported_to_irb]
    fieldsets = (
        ('Basic Information', {
            'fields': ('susar_id', 'participant'),
            'classes': ('wide',),
        }),
        ('Event Details', {
            'fields': ('event_description', 'onset_date', 'detection_date'),
            'classes': ('wide',),
        }),
        ('Severity & Outcome', {
            'fields': ('severity', 'outcome', 'causality_assessment'),
            'classes': ('collapse',),
        }),
        ('Medical Response', {
            'fields': ('actions_taken', 'hospitalization_required'),
            'classes': ('collapse',),
        }),
        ('Regulatory Reporting', {
            'fields': ('reported_to_irb', 'irb_report_date', 'reported_to_sponsor', 'sponsor_report_date'),
            'classes': ('collapse',),
        }),
        ('Follow-up', {
            'fields': ('follow_up_required', 'follow_up_notes'),
            'classes': ('wide',),
        }),
        ('Timeline', {
            'fields': ('get_timeline', 'reported_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def participant_link(self, obj):
        url = reverse('admin:clintrack_participant_change', args=[obj.participant.id])
        return format_html(
            '<a href="{}">{}</a><br><small class="text-muted">{}</small>',
            url,
            obj.participant.participant_id,
            obj.participant.get_full_name()
        )
    participant_link.short_description = 'Participant'
    participant_link.admin_order_field = 'participant'
    
    def severity_badge(self, obj):
        colors = {
            'mild': 'success',
            'moderate': 'warning',
            'severe': 'danger',
            'life_threatening': 'dark',
            'fatal': 'dark',
        }
        color = colors.get(obj.severity, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_severity_display()
        )
    severity_badge.short_description = 'Severity'
    severity_badge.admin_order_field = 'severity'
    
    def outcome_badge(self, obj):
        colors = {
            'recovered': 'success',
            'recovering': 'info',
            'not_recovered': 'warning',
            'recovered_sequelae': 'info',
            'fatal': 'danger',
            'unknown': 'secondary',
        }
        color = colors.get(obj.outcome, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_outcome_display()
        )
    outcome_badge.short_description = 'Outcome'
    outcome_badge.admin_order_field = 'outcome'
    
    def follow_up_status(self, obj):
        if obj.follow_up_required:
            return format_html(
                '<span class="badge bg-warning text-dark">Follow-up Required</span>'
            )
        return format_html(
            '<span class="badge bg-success">Complete</span>'
        )
    follow_up_status.short_description = 'Follow-up'
    
    def dates(self, obj):
        return format_html(
            'Onset: {}<br>Detected: {}',
            obj.onset_date.strftime('%Y-%m-%d'),
            obj.detection_date.strftime('%Y-%m-%d')
        )
    dates.short_description = 'Dates'
    
    def get_timeline(self, obj):
        timeline = f'''
        <div style="position: relative; padding-left: 20px;">
            <div style="position: absolute; left: 6px; top: 0; bottom: 0; width: 2px; background: #dee2e6;"></div>
            <div style="position: relative; margin-bottom: 20px;">
                <div style="position: absolute; left: -20px; top: 0; width: 12px; height: 12px; border-radius: 50%; background: #0033c4; border: 2px solid white;"></div>
                <div style="margin-left: 10px;">
                    <strong>Onset Date:</strong> {obj.onset_date.strftime('%Y-%m-%d %H:%M')}
                </div>
            </div>
            <div style="position: relative; margin-bottom: 20px;">
                <div style="position: absolute; left: -20px; top: 0; width: 12px; height: 12px; border-radius: 50%; background: #00cff4; border: 2px solid white;"></div>
                <div style="margin-left: 10px;">
                    <strong>Detection Date:</strong> {obj.detection_date.strftime('%Y-%m-%d %H:%M')}
                </div>
            </div>
        '''
        if obj.irb_report_date:
            timeline += f'''
            <div style="position: relative; margin-bottom: 20px;">
                <div style="position: absolute; left: -20px; top: 0; width: 12px; height: 12px; border-radius: 50%; background: #00d284; border: 2px solid white;"></div>
                <div style="margin-left: 10px;">
                    <strong>Reported to IRB:</strong> {obj.irb_report_date}
                </div>
            </div>
            '''
        if obj.created_at:
            timeline += f'''
            <div style="position: relative; margin-bottom: 20px;">
                <div style="position: absolute; left: -20px; top: 0; width: 12px; height: 12px; border-radius: 50%; background: #a0a0a0; border: 2px solid white;"></div>
                <div style="margin-left: 10px;">
                    <strong>Record Created:</strong> {obj.created_at.strftime('%Y-%m-%d %H:%M')}
                </div>
            </div>
            '''
        timeline += '</div>'
        return format_html(timeline)
    get_timeline.short_description = 'Event Timeline'

@admin.register(StaffAttendance)
class StaffAttendanceAdmin(ClinTrackAdmin):
    list_display = ['staff', 'login_time_formatted', 'logout_time_formatted', 'duration', 'location_badge']
    list_filter = ['login_time', 'staff__role']
    search_fields = ['staff__username', 'staff__email', 'location', 'ip_address']
    readonly_fields = ['login_time', 'ip_address']
    
    def login_time_formatted(self, obj):
        return obj.login_time.strftime('%Y-%m-%d %H:%M')
    login_time_formatted.short_description = 'Login Time'
    login_time_formatted.admin_order_field = 'login_time'
    
    def logout_time_formatted(self, obj):
        if obj.logout_time:
            return obj.logout_time.strftime('%Y-%m-%d %H:%M')
        return format_html('<span class="badge bg-warning text-dark">Active</span>')
    logout_time_formatted.short_description = 'Logout Time'
    
    def duration(self, obj):
        if obj.logout_time:
            delta = obj.logout_time - obj.login_time
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m"
        return format_html('<span class="badge bg-success">In Session</span>')
    duration.short_description = 'Duration'
    
    def location_badge(self, obj):
        if obj.location:
            return format_html(
                '<span class="badge bg-info">{}</span>',
                obj.location[:20]
            )
        return format_html('<span class="text-muted">Unknown</span>')
    location_badge.short_description = 'Location'

@admin.register(AuditLog)
class AuditLogAdmin(ClinTrackAdmin):
    list_display = ['user', 'action_badge', 'model_name', 'object_link', 'timestamp_formatted']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__username', 'object_id', 'changes']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'changes', 'timestamp', 'ip_address']
    date_hierarchy = 'timestamp'
    
    def action_badge(self, obj):
        colors = {
            'create': 'success',
            'update': 'primary',
            'delete': 'danger',
            'view': 'info',
        }
        color = colors.get(obj.action, 'secondary')
        icons = {
            'create': 'plus-circle',
            'update': 'pencil',
            'delete': 'trash',
            'view': 'eye',
        }
        icon = icons.get(obj.action, 'circle')
        return format_html(
            '<span class="badge bg-{}"><i class="bi bi-{}"></i> {}</span>',
            color,
            icon,
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'
    action_badge.admin_order_field = 'action'
    
    def object_link(self, obj):
        # Try to get the admin URL for the object
        try:
            model_class = None
            if obj.model_name.lower() == 'participant':
                model_class = Participant
                field = 'participant_id'
            elif obj.model_name.lower() == 'study':
                model_class = Study
                field = 'code'
            elif obj.model_name.lower() == 'susar':
                model_class = SUSAR
                field = 'susar_id'
            elif obj.model_name.lower() == 'user':
                model_class = User
                field = 'username'
            
            if model_class:
                try:
                    instance = model_class.objects.get(id=obj.object_id)
                    url = reverse(f'admin:clintrack_{obj.model_name.lower()}_change', args=[obj.object_id])
                    display_value = getattr(instance, field, obj.object_id)
                    return format_html('<a href="{}">{}</a>', url, display_value)
                except (model_class.DoesNotExist, ValueError):
                    pass
        except:
            pass
        
        return format_html('<code>{}</code>', obj.object_id)
    object_link.short_description = 'Object'
    
    def timestamp_formatted(self, obj):
        return format_html(
            '{}<br><small class="text-muted">{}</small>',
            obj.timestamp.strftime('%Y-%m-%d'),
            obj.timestamp.strftime('%H:%M:%S')
        )
    timestamp_formatted.short_description = 'Timestamp'

# Quick actions panel
def get_admin_quick_actions(request):
    return {
        'total_participants': Participant.objects.count(),
        'active_studies': Study.objects.filter(is_active=True).count(),
        'pending_susars': SUSAR.objects.filter(follow_up_required=True).count(),
        'today_logins': StaffAttendance.objects.filter(login_time__date=timezone.now().date()).count(),
    }