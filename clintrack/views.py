# ============================================
# views.py - ClinTrack Views
# ============================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone
from datetime import timedelta, datetime
from django.http import JsonResponse
from .models import User, Study, Participant, SUSAR, StaffAttendance, AuditLog
from django.contrib.auth import get_user_model

User = get_user_model()


# ============================================
# Authentication Views
# ============================================

def login_view(request):
    """
    Handle user login and redirect to role-based dashboard
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Log attendance
            StaffAttendance.objects.create(
                staff=user,
                login_time=timezone.now(),
                ip_address=get_client_ip(request)
            )
            
            # Log audit
            AuditLog.objects.create(
                user=user,
                action='view',
                model_name='User',
                object_id=str(user.id),
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            
            # Redirect based on role
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'auth/login.html')


def logout_view(request):
    """
    Handle user logout and update attendance
    """
    if request.user.is_authenticated:
        # Update last attendance record
        try:
            last_attendance = StaffAttendance.objects.filter(
                staff=request.user,
                logout_time__isnull=True
            ).latest('login_time')
            last_attendance.logout_time = timezone.now()
            last_attendance.save()
        except StaffAttendance.DoesNotExist:
            pass
        
        messages.success(request, 'You have been logged out successfully')
        logout(request)
    
    return redirect('login')


# ============================================
# Dashboard Views - Role Based
# ============================================

@login_required
def dashboard(request):
    """
    Main dashboard - redirects to role-specific dashboard
    """
    user = request.user
    
    # Redirect based on role
    if user.role == 'admin':
        return admin_dashboard(request)
    elif user.role == 'coordinator':
        return coordinator_dashboard(request)
    elif user.role == 'staff':
        return staff_dashboard(request)
    elif user.role == 'viewer':
        return viewer_dashboard(request)
    else:
        return admin_dashboard(request)  # Default


@login_required
def admin_dashboard(request):
    """
    Administrator Dashboard - Full system overview with analytics
    """
    # Date filters
    end_date = timezone.now()
    start_date = end_date - timedelta(days=365)
    last_30_days = end_date - timedelta(days=30)
    
    # === KEY METRICS ===
    total_participants = Participant.objects.count()
    active_participants = Participant.objects.filter(status='active').count()
    total_studies = Study.objects.filter(is_active=True).count()
    total_susars = SUSAR.objects.count()
    critical_susars = SUSAR.objects.filter(
        severity__in=['severe', 'life_threatening', 'fatal']
    ).count()
    
    # Recent additions (last 30 days)
    recent_participants = Participant.objects.filter(
        created_at__gte=last_30_days
    ).count()
    recent_susars = SUSAR.objects.filter(
        created_at__gte=last_30_days
    ).count()
    
    # === PARTICIPANT STATUS BREAKDOWN ===
    status_breakdown = Participant.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # === STUDY BREAKDOWN ===
    study_breakdown = Study.objects.annotate(
        participant_count=Count('participants'),
        active_count=Count('participants', filter=Q(participants__status='active')),
        susar_count=Count('participants__susars')
    ).order_by('-participant_count')
    
    # === ENROLLMENT TRENDS (Last 12 months) ===
    enrollment_trends = Participant.objects.filter(
        enrollment_date__gte=start_date.date()
    ).annotate(
        month=TruncMonth('enrollment_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # === SUSAR TRENDS (Last 12 months) ===
    susar_trends = SUSAR.objects.filter(
        onset_date__gte=start_date
    ).annotate(
        month=TruncMonth('onset_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # === SUSAR SEVERITY BREAKDOWN ===
    susar_severity = SUSAR.objects.values('severity').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # === GENDER DISTRIBUTION ===
    gender_distribution = Participant.objects.values('gender').annotate(
        count=Count('id')
    )
    
    # === TOP LOCATIONS ===
    top_locations = Participant.objects.values('location').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # === STAFF ACTIVITY (Last 7 days) ===
    last_7_days = end_date - timedelta(days=7)
    staff_activity = User.objects.filter(
        attendances__login_time__gte=last_7_days
    ).annotate(
        login_count=Count('attendances')
    ).order_by('-login_count')[:10]
    
    # === RECENT ACTIVITIES ===
    recent_audit_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
    recent_participants_list = Participant.objects.select_related('study', 'created_by').order_by('-created_at')[:5]
    recent_susars_list = SUSAR.objects.select_related('participant', 'reported_by').order_by('-created_at')[:5]
    
    context = {
        'user_role': 'Administrator',
        'total_participants': total_participants,
        'active_participants': active_participants,
        'total_studies': total_studies,
        'total_susars': total_susars,
        'critical_susars': critical_susars,
        'recent_participants': recent_participants,
        'recent_susars': recent_susars,
        'status_breakdown': status_breakdown,
        'study_breakdown': study_breakdown,
        'enrollment_trends': list(enrollment_trends),
        'susar_trends': list(susar_trends),
        'susar_severity': susar_severity,
        'gender_distribution': gender_distribution,
        'top_locations': top_locations,
        'staff_activity': staff_activity,
        'recent_audit_logs': recent_audit_logs,
        'recent_participants_list': recent_participants_list,
        'recent_susars_list': recent_susars_list,
    }
    
    return render(request, 'dashboards/admin_dashboard.html', context)


@login_required
def coordinator_dashboard(request):
    """
    Study Coordinator Dashboard - Study management and participant oversight
    """
    end_date = timezone.now()
    last_30_days = end_date - timedelta(days=30)
    last_7_days = end_date - timedelta(days=7)
    
    # === KEY METRICS ===
    total_participants = Participant.objects.count()
    active_participants = Participant.objects.filter(status='active').count()
    screening_participants = Participant.objects.filter(status='screening').count()
    total_susars = SUSAR.objects.count()
    pending_susars = SUSAR.objects.filter(
        follow_up_required=True,
        outcome__in=['recovering', 'not_recovered', 'unknown']
    ).count()
    
    # === STUDY BREAKDOWN ===
    study_breakdown = Study.objects.annotate(
        total=Count('participants'),
        active=Count('participants', filter=Q(participants__status='active')),
        screening=Count('participants', filter=Q(participants__status='screening')),
        susars=Count('participants__susars')
    )
    
    # === WEEKLY ENROLLMENT (Last 8 weeks) ===
    eight_weeks_ago = end_date - timedelta(weeks=8)
    weekly_enrollment = Participant.objects.filter(
        enrollment_date__gte=eight_weeks_ago.date()
    ).annotate(
        week=TruncWeek('enrollment_date')
    ).values('week').annotate(
        count=Count('id')
    ).order_by('week')
    
    # === RECENT SUSARS REQUIRING FOLLOW-UP ===
    pending_susars_list = SUSAR.objects.filter(
        follow_up_required=True
    ).select_related('participant', 'reported_by').order_by('-onset_date')[:10]
    
    # === RECENT PARTICIPANTS ===
    recent_participants = Participant.objects.select_related('study').order_by('-created_at')[:10]
    
    # === STATUS BREAKDOWN ===
    status_breakdown = Participant.objects.values('status').annotate(count=Count('id'))
    
    context = {
        'user_role': 'Study Coordinator',
        'total_participants': total_participants,
        'active_participants': active_participants,
        'screening_participants': screening_participants,
        'total_susars': total_susars,
        'pending_susars': pending_susars,
        'study_breakdown': study_breakdown,
        'weekly_enrollment': list(weekly_enrollment),
        'pending_susars_list': pending_susars_list,
        'recent_participants': recent_participants,
        'status_breakdown': status_breakdown,
    }
    
    return render(request, 'dashboards/coordinator_dashboard.html', context)


@login_required
def staff_dashboard(request):
    """
    Research Staff Dashboard - Daily operations and participant management
    """
    end_date = timezone.now()
    last_7_days = end_date - timedelta(days=7)
    today = end_date.date()
    
    # === MY METRICS ===
    my_participants = Participant.objects.filter(created_by=request.user).count()
    my_recent_participants = Participant.objects.filter(
        created_by=request.user,
        created_at__gte=last_7_days
    ).count()
    
    # === TODAY'S ACTIVITIES ===
    participants_today = Participant.objects.filter(
        created_at__date=today
    ).count()
    
    susars_today = SUSAR.objects.filter(
        detection_date__date=today
    ).count()
    
    # === QUICK STATS ===
    total_active = Participant.objects.filter(status='active').count()
    total_screening = Participant.objects.filter(status='screening').count()
    pending_followups = SUSAR.objects.filter(
        follow_up_required=True,
        outcome__in=['recovering', 'not_recovered']
    ).count()
    
    # === MY RECENT PARTICIPANTS ===
    my_recent_list = Participant.objects.filter(
        created_by=request.user
    ).select_related('study').order_by('-created_at')[:10]
    
    # === RECENT SYSTEM ACTIVITIES ===
    recent_participants = Participant.objects.select_related('study', 'created_by').order_by('-created_at')[:5]
    recent_susars = SUSAR.objects.select_related('participant', 'reported_by').order_by('-created_at')[:5]
    
    # === STUDY BREAKDOWN ===
    study_stats = Study.objects.annotate(
        total=Count('participants'),
        active=Count('participants', filter=Q(participants__status='active'))
    )
    
    context = {
        'user_role': 'Research Staff',
        'my_participants': my_participants,
        'my_recent_participants': my_recent_participants,
        'participants_today': participants_today,
        'susars_today': susars_today,
        'total_active': total_active,
        'total_screening': total_screening,
        'pending_followups': pending_followups,
        'my_recent_list': my_recent_list,
        'recent_participants': recent_participants,
        'recent_susars': recent_susars,
        'study_stats': study_stats,
    }
    
    return render(request, 'dashboards/staff_dashboard.html', context)


@login_required
def viewer_dashboard(request):
    """
    Viewer Dashboard - Read-only overview
    """
    # === SUMMARY METRICS ===
    total_participants = Participant.objects.count()
    active_participants = Participant.objects.filter(status='active').count()
    total_studies = Study.objects.filter(is_active=True).count()
    total_susars = SUSAR.objects.count()
    
    # === STUDY BREAKDOWN ===
    study_breakdown = Study.objects.annotate(
        participant_count=Count('participants'),
        active_count=Count('participants', filter=Q(participants__status='active'))
    )
    
    # === STATUS BREAKDOWN ===
    status_breakdown = Participant.objects.values('status').annotate(count=Count('id'))
    
    # === RECENT PARTICIPANTS ===
    recent_participants = Participant.objects.select_related('study').order_by('-created_at')[:10]
    
    context = {
        'user_role': 'Viewer',
        'total_participants': total_participants,
        'active_participants': active_participants,
        'total_studies': total_studies,
        'total_susars': total_susars,
        'study_breakdown': study_breakdown,
        'status_breakdown': status_breakdown,
        'recent_participants': recent_participants,
    }
    
    return render(request, 'dashboards/viewer_dashboard.html', context)


# ============================================
# API Endpoints for Charts (JSON)
# ============================================

@login_required
def enrollment_chart_data(request):
    """
    API endpoint for enrollment trend chart data
    """
    months = int(request.GET.get('months', 12))
    start_date = timezone.now() - timedelta(days=months * 30)
    
    data = Participant.objects.filter(
        enrollment_date__gte=start_date.date()
    ).annotate(
        month=TruncMonth('enrollment_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    chart_data = {
        'labels': [item['month'].strftime('%b %Y') for item in data],
        'data': [item['count'] for item in data]
    }
    
    return JsonResponse(chart_data)


@login_required
def susar_chart_data(request):
    """
    API endpoint for SUSAR trend chart data
    """
    months = int(request.GET.get('months', 12))
    start_date = timezone.now() - timedelta(days=months * 30)
    
    data = SUSAR.objects.filter(
        onset_date__gte=start_date
    ).annotate(
        month=TruncMonth('onset_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    chart_data = {
        'labels': [item['month'].strftime('%b %Y') for item in data],
        'data': [item['count'] for item in data]
    }
    
    return JsonResponse(chart_data)


@login_required
def status_chart_data(request):
    """
    API endpoint for participant status distribution
    """
    data = Participant.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    chart_data = {
        'labels': [item['status'].title() for item in data],
        'data': [item['count'] for item in data]
    }
    
    return JsonResponse(chart_data)


# ============================================
# Utility Functions
# ============================================

def get_client_ip(request):
    """
    Get client IP address from request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip