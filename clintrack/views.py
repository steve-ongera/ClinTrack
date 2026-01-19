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
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from datetime import timedelta
import json

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
    last_7_days = end_date - timedelta(days=7)
    
    # === KEY METRICS ===
    total_participants = Participant.objects.count()
    active_participants = Participant.objects.filter(status='active').count()
    completed_participants = Participant.objects.filter(status='completed').count()
    screening_participants = Participant.objects.filter(status='screening').count()
    lost_participants = Participant.objects.filter(status='lost').count()
    withdrawn_participants = Participant.objects.filter(status='withdrawn').count()
    
    active_studies = Study.objects.filter(is_active=True).count()
    total_studies = Study.objects.count()
    
    total_susars = SUSAR.objects.count()
    pending_susars = SUSAR.objects.filter(follow_up_required=True).count()
    critical_susars = SUSAR.objects.filter(
        severity__in=['severe', 'life_threatening', 'fatal']
    ).count()
    
    # Monthly participants (last 30 days)
    monthly_participants = Participant.objects.filter(
        created_at__gte=last_30_days
    ).count()
    
    # Calculate growth percentage
    previous_month = last_30_days - timedelta(days=30)
    previous_month_count = Participant.objects.filter(
        created_at__gte=previous_month,
        created_at__lt=last_30_days
    ).count()
    
    if previous_month_count > 0:
        monthly_growth = round(((monthly_participants - previous_month_count) / previous_month_count) * 100, 1)
    else:
        monthly_growth = 100 if monthly_participants > 0 else 0
    
    # === PARTICIPANT STATUS BREAKDOWN (for doughnut chart) ===
    status_breakdown = Participant.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    status_data = {
        'labels': [item['status'].title() for item in status_breakdown],
        'data': [item['count'] for item in status_breakdown],
        'colors': ['#00d25b', '#ffab00', '#fc424a', '#8e32e9', '#6c757d']
    }
    
    # === STUDY DISTRIBUTION (for doughnut chart) ===
    study_distribution = Study.objects.annotate(
        participant_count=Count('participants')
    ).order_by('-participant_count')[:5]
    
    study_data = {
        'labels': [study.code for study in study_distribution],
        'data': [study.participant_count for study in study_distribution],
        'colors': ['#00d25b', '#ffab00', '#fc424a', '#8e32e9', '#00d0ff']
    }
    
    # === GENDER DISTRIBUTION (for doughnut chart) ===
    gender_breakdown = Participant.objects.values('gender').annotate(
        count=Count('id')
    )
    
    gender_map = {'M': 'Male', 'F': 'Female', 'O': 'Other', 'U': 'Not Specified'}
    gender_data = {
        'labels': [gender_map.get(item['gender'], item['gender']) for item in gender_breakdown],
        'data': [item['count'] for item in gender_breakdown],
        'colors': ['#00d25b', '#fc424a', '#ffab00', '#8e32e9']
    }
    
    # === ENROLLMENT TRENDS - Last 30 days (for line chart) ===
    enrollment_daily = Participant.objects.filter(
        enrollment_date__gte=last_30_days
    ).annotate(
        day=TruncDay('enrollment_date')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    # Fill in missing days with 0
    enrollment_trend_labels = []
    enrollment_trend_data = []
    current_date = last_30_days.date()
    enrollment_dict = {item['day']: item['count'] for item in enrollment_daily}
    
    while current_date <= end_date.date():
        enrollment_trend_labels.append(current_date.strftime('%b %d'))
        enrollment_trend_data.append(enrollment_dict.get(current_date, 0))
        current_date += timedelta(days=1)
    
    enrollment_trend = {
        'labels': enrollment_trend_labels,
        'data': enrollment_trend_data
    }
    
    # === SUSAR TRENDS - Last 30 days (for bar chart) ===
    susar_daily = SUSAR.objects.filter(
        onset_date__gte=last_30_days
    ).annotate(
        day=TruncDay('onset_date')
    ).values('day').annotate(
        count=Count('id')
    ).order_by('day')
    
    susar_trend_labels = []
    susar_trend_data = []
    current_date = last_30_days.date()
    susar_dict = {item['day']: item['count'] for item in susar_daily}
    
    while current_date <= end_date.date():
        susar_trend_labels.append(current_date.strftime('%b %d'))
        susar_trend_data.append(susar_dict.get(current_date, 0))
        current_date += timedelta(days=1)
    
    susar_trend = {
        'labels': susar_trend_labels,
        'data': susar_trend_data
    }
    
    # === ENROLLMENT BY MONTH - Last 12 months (for main chart) ===
    enrollment_monthly = Participant.objects.filter(
        enrollment_date__gte=start_date
    ).annotate(
        month=TruncMonth('enrollment_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    monthly_labels = []
    monthly_data = []
    current_month = start_date.date().replace(day=1)
    enrollment_month_dict = {item['month']: item['count'] for item in enrollment_monthly}
    
    for _ in range(12):
        monthly_labels.append(current_month.strftime('%b %Y'))
        monthly_data.append(enrollment_month_dict.get(current_month, 0))
        # Move to next month
        if current_month.month == 12:
            current_month = current_month.replace(year=current_month.year + 1, month=1)
        else:
            current_month = current_month.replace(month=current_month.month + 1)
    
    enrollment_monthly_trend = {
        'labels': monthly_labels,
        'data': monthly_data
    }
    
    # === RECENT PARTICIPANTS ===
    recent_participants = Participant.objects.select_related(
        'study', 'created_by'
    ).order_by('-created_at')[:7]
    
    # === UPCOMING FOLLOW-UPS (Mock data - you can create a FollowUp model) ===
    upcoming_followups = []  # Placeholder - implement based on your follow-up system
    
    # === TOP LOCATIONS ===
    top_locations = Participant.objects.values('location').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # === STAFF ACTIVITY ===
    staff_activity = User.objects.filter(
        attendances__login_time__gte=last_7_days
    ).annotate(
        login_count=Count('attendances')
    ).order_by('-login_count')[:5]
    
    context = {
        'today': timezone.now().date(),
        'user_role': 'Administrator',
        
        # Key Metrics
        'total_participants': total_participants,
        'active_participants': active_participants,
        'completed_participants': completed_participants,
        'screening_participants': screening_participants,
        'lost_participants': lost_participants,
        'withdrawn_participants': withdrawn_participants,
        'active_studies': active_studies,
        'total_studies': total_studies,
        'total_susars': total_susars,
        'pending_susars': pending_susars,
        'critical_susars': critical_susars,
        'monthly_participants': monthly_participants,
        'monthly_growth': monthly_growth,
        
        # Chart Data (as JSON for JavaScript)
        'status_data': json.dumps(status_data),
        'study_data': json.dumps(study_data),
        'gender_data': json.dumps(gender_data),
        'enrollment_trend': json.dumps(enrollment_trend),
        'susar_trend': json.dumps(susar_trend),
        'enrollment_monthly_trend': json.dumps(enrollment_monthly_trend),
        
        # Lists
        'recent_participants': recent_participants,
        'upcoming_followups': upcoming_followups,
        'top_locations': top_locations,
        'staff_activity': staff_activity,
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