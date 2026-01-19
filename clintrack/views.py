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
    
    # === WEEKLY ENROLLMENT (Last 8 weeks) ===
    eight_weeks_ago = end_date - timedelta(weeks=8)
    
    # Generate weekly enrollment data for chart
    weekly_data = []
    weekly_labels = []
    
    # Create list of last 8 weeks
    for i in range(8):
        week_start = end_date - timedelta(weeks=i)
        week_start = week_start - timedelta(days=week_start.weekday())  # Start of week (Monday)
        week_end = week_start + timedelta(days=6)
        
        week_participants = Participant.objects.filter(
            enrollment_date__gte=week_start.date(),
            enrollment_date__lte=week_end.date()
        ).count()
        
        weekly_data.insert(0, week_participants)
        weekly_labels.insert(0, f"W{week_start.isocalendar()[1]}")
    
    # === STUDY BREAKDOWN ===
    study_breakdown = Study.objects.annotate(
        total=Count('participants'),
        active=Count('participants', filter=Q(participants__status='active')),
        screening=Count('participants', filter=Q(participants__status='screening')),
        susars=Count('participants__susars')
    )
    
    # Prepare study data for chart
    study_data = {
        'labels': [],
        'participant_counts': [],
        'susar_counts': [],
        'colors': []
    }
    
    study_colors = [
        'rgba(0, 51, 196, 0.8)',      # Primary blue
        'rgba(0, 210, 132, 0.8)',     # Success green
        'rgba(255, 87, 48, 0.8)',     # Warning orange
        'rgba(0, 207, 244, 0.8)',     # Info cyan
        'rgba(160, 160, 160, 0.8)',   # Secondary gray
        'rgba(255, 8, 84, 0.8)',      # Danger pink
    ]
    
    for i, study in enumerate(study_breakdown):
        study_data['labels'].append(study.code[:15])
        study_data['participant_counts'].append(study.total)
        study_data['susar_counts'].append(study.susars)
        study_data['colors'].append(study_colors[i % len(study_colors)])
    
    # === STATUS BREAKDOWN ===
    status_breakdown = Participant.objects.values('status').annotate(count=Count('id'))
    
    # Prepare status data for chart
    status_data = {
        'labels': [],
        'data': [],
        'colors': []
    }
    
    status_mapping = {
        'active': {'label': 'Active', 'color': 'rgba(0, 210, 132, 0.8)'},
        'screening': {'label': 'Screening', 'color': 'rgba(255, 87, 48, 0.8)'},
        'completed': {'label': 'Completed', 'color': 'rgba(0, 207, 244, 0.8)'},
        'withdrawn': {'label': 'Withdrawn', 'color': 'rgba(160, 160, 160, 0.8)'},
        'lost': {'label': 'Lost to Follow-up', 'color': 'rgba(255, 8, 84, 0.8)'},
    }
    
    for status in status_breakdown:
        status_key = status['status']
        if status_key in status_mapping:
            status_data['labels'].append(status_mapping[status_key]['label'])
            status_data['data'].append(status['count'])
            status_data['colors'].append(status_mapping[status_key]['color'])
    
    # === MONTHLY SUSAR TREND ===
    monthly_susar_data = []
    monthly_susar_labels = []
    
    for i in range(6):  # Last 6 months
        month_start = end_date - timedelta(days=30*i)
        month_start = month_start.replace(day=1)
        if i == 0:
            month_end = end_date
        else:
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month - timedelta(days=next_month.day)
        
        month_susars = SUSAR.objects.filter(
            detection_date__gte=month_start,
            detection_date__lte=month_end
        ).count()
        
        monthly_susar_data.insert(0, month_susars)
        monthly_susar_labels.insert(0, month_start.strftime('%b'))
    
    # === PENDING SUSARS BY SEVERITY ===
    pending_by_severity = SUSAR.objects.filter(
        follow_up_required=True
    ).values('severity').annotate(count=Count('id'))
    
    severity_data = {
        'labels': [],
        'data': [],
        'colors': []
    }
    
    severity_colors = {
        'mild': 'rgba(0, 210, 132, 0.8)',
        'moderate': 'rgba(255, 171, 0, 0.8)',
        'severe': 'rgba(255, 87, 48, 0.8)',
        'life_threatening': 'rgba(255, 8, 84, 0.8)',
        'fatal': 'rgba(108, 117, 125, 0.8)',
    }
    
    for item in pending_by_severity:
        severity_key = item['severity']
        severity_data['labels'].append(severity_key.capitalize())
        severity_data['data'].append(item['count'])
        severity_data['colors'].append(severity_colors.get(severity_key, 'rgba(160, 160, 160, 0.8)'))
    
    # === RECENT SUSARS REQUIRING FOLLOW-UP ===
    pending_susars_list = SUSAR.objects.filter(
        follow_up_required=True
    ).select_related('participant', 'reported_by').order_by('-onset_date')[:10]
    
    # === RECENT PARTICIPANTS ===
    recent_participants = Participant.objects.select_related('study').order_by('-created_at')[:10]
    
    context = {
        'user_role': 'Study Coordinator',
        'total_participants': total_participants,
        'active_participants': active_participants,
        'screening_participants': screening_participants,
        'total_susars': total_susars,
        'pending_susars': pending_susars,
        'study_breakdown': study_breakdown,
        'pending_susars_list': pending_susars_list,
        'recent_participants': recent_participants,
        'status_breakdown': status_breakdown,
        
        # Chart Data
        'weekly_enrollment_data': weekly_data,
        'weekly_enrollment_labels': weekly_labels,
        'study_data_json': json.dumps(study_data),
        'status_data_json': json.dumps(status_data),
        'monthly_susar_data': monthly_susar_data,
        'monthly_susar_labels': monthly_susar_labels,
        'severity_data_json': json.dumps(severity_data),
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


# ============================================
# views.py - ClinTrack Views
# ============================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Participant, Study, SUSAR, User, StaffAttendance, AuditLog
from .forms import (
    ParticipantForm, StudyForm, SUSARForm, 
    UserForm, StaffAttendanceForm
)

# ============================================
# PARTICIPANT VIEWS
# ============================================

@login_required
def participant_list(request):
    """List all participants with filters"""
    participants = Participant.objects.select_related('study', 'created_by').all()
    
    # Filters
    search = request.GET.get('search', '')
    study_filter = request.GET.get('study', '')
    status_filter = request.GET.get('status', '')
    
    if search:
        participants = participants.filter(
            Q(participant_id__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(primary_phone__icontains=search)
        )
    
    if study_filter:
        participants = participants.filter(study_id=study_filter)
    
    if status_filter:
        participants = participants.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(participants, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    studies = Study.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'studies': studies,
        'search': search,
        'study_filter': study_filter,
        'status_filter': status_filter,
        'status_choices': Participant.STATUS_CHOICES,
    }
    return render(request, 'participants/participant_list.html', context)


@login_required
def participant_detail(request, pk):
    """View participant details"""
    participant = get_object_or_404(Participant, pk=pk)
    susars = participant.susars.all().order_by('-onset_date')
    
    context = {
        'participant': participant,
        'susars': susars,
    }
    return render(request, 'participants/participant_detail.html', context)


@login_required
def participant_create(request):
    """Create new participant"""
    if request.user.role not in ['admin', 'coordinator']:
        messages.error(request, 'You do not have permission to add participants.')
        return redirect('participant_list')
    
    if request.method == 'POST':
        form = ParticipantForm(request.POST)
        if form.is_valid():
            participant = form.save(commit=False)
            participant.created_by = request.user
            participant.save()
            messages.success(request, f'Participant {participant.participant_id} created successfully.')
            return redirect('participant_detail', pk=participant.pk)
    else:
        form = ParticipantForm()
    
    context = {'form': form}
    return render(request, 'participants/participant_form.html', context)


@login_required
def participant_update(request, pk):
    """Update participant"""
    participant = get_object_or_404(Participant, pk=pk)
    
    if request.user.role not in ['admin', 'coordinator']:
        messages.error(request, 'You do not have permission to edit participants.')
        return redirect('participant_detail', pk=pk)
    
    if request.method == 'POST':
        form = ParticipantForm(request.POST, instance=participant)
        if form.is_valid():
            form.save()
            messages.success(request, 'Participant updated successfully.')
            return redirect('participant_detail', pk=pk)
    else:
        form = ParticipantForm(instance=participant)
    
    context = {'form': form, 'participant': participant}
    return render(request, 'participants/participant_form.html', context)


@login_required
def participant_delete(request, pk):
    """Delete participant"""
    if request.user.role != 'admin':
        messages.error(request, 'Only administrators can delete participants.')
        return redirect('participant_list')
    
    participant = get_object_or_404(Participant, pk=pk)
    
    if request.method == 'POST':
        participant.delete()
        messages.success(request, 'Participant deleted successfully.')
        return redirect('participant_list')
    
    context = {'participant': participant}
    return render(request, 'participants/participant_confirm_delete.html', context)


@login_required
def participant_search(request):
    """Advanced participant search"""
    results = []
    
    if request.method == 'GET' and request.GET:
        query = Q()
        
        participant_id = request.GET.get('participant_id', '')
        first_name = request.GET.get('first_name', '')
        last_name = request.GET.get('last_name', '')
        phone = request.GET.get('phone', '')
        location = request.GET.get('location', '')
        
        if participant_id:
            query &= Q(participant_id__icontains=participant_id)
        if first_name:
            query &= Q(first_name__icontains=first_name)
        if last_name:
            query &= Q(last_name__icontains=last_name)
        if phone:
            query &= Q(primary_phone__icontains=phone) | Q(secondary_phone__icontains=phone)
        if location:
            query &= Q(location__icontains=location)
        
        results = Participant.objects.filter(query).select_related('study')[:50]
    
    context = {'results': results}
    return render(request, 'participants/participant_search.html', context)


# ============================================
# STUDY VIEWS
# ============================================

@login_required
def study_list(request):
    """List all studies"""
    studies = Study.objects.annotate(
        participant_count=Count('participants')
    ).order_by('-is_active', 'name')
    
    context = {'studies': studies}
    return render(request, 'studies/study_list.html', context)


@login_required
def study_detail(request, pk):
    """View study details"""
    study = get_object_or_404(Study, pk=pk)
    participants = study.participants.all()[:20]
    
    stats = {
        'total': study.participants.count(),
        'active': study.participants.filter(status='active').count(),
        'completed': study.participants.filter(status='completed').count(),
        'screening': study.participants.filter(status='screening').count(),
    }
    
    context = {
        'study': study,
        'participants': participants,
        'stats': stats,
    }
    return render(request, 'studies/study_detail.html', context)


@login_required
def study_create(request):
    """Create new study"""
    if request.user.role != 'admin':
        messages.error(request, 'Only administrators can create studies.')
        return redirect('study_list')
    
    if request.method == 'POST':
        form = StudyForm(request.POST)
        if form.is_valid():
            study = form.save()
            messages.success(request, f'Study {study.code} created successfully.')
            return redirect('study_detail', pk=study.pk)
    else:
        form = StudyForm()
    
    context = {'form': form}
    return render(request, 'studies/study_form.html', context)


@login_required
def study_update(request, pk):
    """Update study"""
    study = get_object_or_404(Study, pk=pk)
    
    if request.user.role != 'admin':
        messages.error(request, 'Only administrators can edit studies.')
        return redirect('study_detail', pk=pk)
    
    if request.method == 'POST':
        form = StudyForm(request.POST, instance=study)
        if form.is_valid():
            form.save()
            messages.success(request, 'Study updated successfully.')
            return redirect('study_detail', pk=pk)
    else:
        form = StudyForm(instance=study)
    
    context = {'form': form, 'study': study}
    return render(request, 'studies/study_form.html', context)


# ============================================
# SUSAR VIEWS
# ============================================

@login_required
def susars_list(request):
    """List all SUSAR reports"""
    susars = SUSAR.objects.select_related('participant', 'reported_by').all()
    
    # Filters
    severity_filter = request.GET.get('severity', '')
    follow_up_filter = request.GET.get('follow_up', '')
    
    if severity_filter:
        susars = susars.filter(severity=severity_filter)
    
    if follow_up_filter == 'pending':
        susars = susars.filter(follow_up_required=True)
    
    paginator = Paginator(susars, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'severity_choices': SUSAR.SEVERITY_CHOICES,
        'severity_filter': severity_filter,
    }
    return render(request, 'susars/susars_list.html', context)


@login_required
def susars_detail(request, pk):
    """View SUSAR details"""
    susar = get_object_or_404(SUSAR, pk=pk)
    
    context = {'susar': susar}
    return render(request, 'susars/susars_detail.html', context)


@login_required
def susars_create(request):
    """Create new SUSAR report"""
    if request.user.role == 'viewer':
        messages.error(request, 'Viewers cannot create SUSAR reports.')
        return redirect('susars_list')
    
    if request.method == 'POST':
        form = SUSARForm(request.POST)
        if form.is_valid():
            susar = form.save(commit=False)
            susar.reported_by = request.user
            susar.save()
            messages.success(request, f'SUSAR {susar.susar_id} reported successfully.')
            return redirect('susars_detail', pk=susar.pk)
    else:
        form = SUSARForm()
    
    context = {'form': form}
    return render(request, 'susars/susars_form.html', context)


@login_required
def susars_update(request, pk):
    """Update SUSAR report"""
    susar = get_object_or_404(SUSAR, pk=pk)
    
    if request.user.role == 'viewer':
        messages.error(request, 'Viewers cannot edit SUSAR reports.')
        return redirect('susars_detail', pk=pk)
    
    if request.method == 'POST':
        form = SUSARForm(request.POST, instance=susar)
        if form.is_valid():
            form.save()
            messages.success(request, 'SUSAR updated successfully.')
            return redirect('susars_detail', pk=pk)
    else:
        form = SUSARForm(instance=susar)
    
    context = {'form': form, 'susar': susar}
    return render(request, 'susars/susars_form.html', context)


@login_required
def susars_pending(request):
    """List pending follow-up SUSARs"""
    susars = SUSAR.objects.filter(
        follow_up_required=True
    ).select_related('participant', 'reported_by')
    
    context = {'susars': susars}
    return render(request, 'susars/susars_pending.html', context)


# ============================================
# USER/STAFF Management VIEWS
# ============================================

@login_required
def users_list(request):
    """List all staff members"""
    if request.user.role != 'admin':
        messages.error(request, 'Only administrators can view staff list.')
        return redirect('dashboard')
    
    users = User.objects.all().order_by('-is_active', 'username')
    
    context = {'users': users}
    return render(request, 'users/users_list.html', context)


@login_required
def users_create(request):
    """Create new staff member"""
    if request.user.role != 'admin':
        messages.error(request, 'Only administrators can create staff accounts.')
        return redirect('users_list')
    
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully.')
            return redirect('users_list')
    else:
        form = UserForm()
    
    context = {'form': form}
    return render(request, 'users/users_form.html', context)


@login_required
def users_profile(request):
    """View/Edit user profile"""
    context = {'user': request.user}
    return render(request, 'users/users_profile.html', context)


# ============================================
# views.py
# ============================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Avg, Max, Min, Sum
from django.db.models.functions import TruncMonth, TruncWeek, ExtractMonth, TruncDay
from django.utils import timezone
from datetime import timedelta, datetime
import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
import csv
from django.core.paginator import Paginator

from .models import User, Study, Participant, SUSAR, StaffAttendance, AuditLog

# ============================================
# USER SETTINGS VIEWS
# ============================================

@login_required
def users_settings(request):
    """Main user settings page with analytics"""
    # Security metrics
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Calculate password age (assuming password last changed field exists)
    password_age = (timezone.now() - request.user.date_joined).days
    
    # Login count this month
    login_count = StaffAttendance.objects.filter(
        staff=request.user,
        login_time__gte=thirty_days_ago
    ).count()
    
    # Unique locations
    unique_locations = StaffAttendance.objects.filter(
        staff=request.user
    ).values('location').distinct().count()
    
    from django.db.models import Avg, F, ExpressionWrapper, DurationField

    avg_session = StaffAttendance.objects.filter(
        staff=request.user,
        logout_time__isnull=False
    ).aggregate(
        avg_duration=Avg(
            ExpressionWrapper(
                F('logout_time') - F('login_time'),
                output_field=DurationField()
            )
        )
    )

    avg_session_hours = round((avg_session['avg_duration'].total_seconds() / 3600) if avg_session['avg_duration'] else 0, 1)
    
    # Active sessions
    active_sessions = StaffAttendance.objects.filter(
        staff=request.user,
        logout_time__isnull=True
    ).order_by('-login_time')
    
    # Current IP
    current_ip = request.META.get('REMOTE_ADDR', 'Unknown')
    
    context = {
        'security_metrics': {
            'password_age': password_age,
            'login_count': login_count,
            'unique_locations': unique_locations,
            'avg_session': avg_session_hours,
        },
        'active_sessions': active_sessions[:5],
        'current_ip': current_ip,
        'current_session_start': active_sessions.first().login_time if active_sessions.exists() else timezone.now(),
    }
    
    return render(request, 'users/users_settings.html', context)

@login_required
@require_POST
def update_profile(request):
    """Update user profile information"""
    user = request.user
    
    # Get form data
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip()
    phone_number = request.POST.get('phone_number', '').strip()
    
    # Basic validation
    if not first_name or not last_name:
        messages.error(request, 'First name and last name are required.')
        return redirect('users_settings')
    
    if not email:
        messages.error(request, 'Email address is required.')
        return redirect('users_settings')
    
    # Check if email is already in use by another user
    if email != user.email and User.objects.filter(email=email).exists():
        messages.error(request, 'This email address is already in use.')
        return redirect('users_settings')
    
    # Update user
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.phone_number = phone_number if phone_number else None
    user.save()
    
    # Log the change
    AuditLog.objects.create(
        user=user,
        action='update',
        model_name='User',
        object_id=str(user.id),
        changes={
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone_number': phone_number
        },
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    messages.success(request, 'Profile updated successfully.')
    return redirect('users_settings')

@login_required
@require_POST
def update_password(request):
    """Update user password"""
    user = request.user
    
    current_password = request.POST.get('current_password', '')
    new_password = request.POST.get('new_password', '')
    confirm_password = request.POST.get('confirm_password', '')
    
    # Validate current password
    if not user.check_password(current_password):
        messages.error(request, 'Current password is incorrect.')
        return redirect('users_settings')
    
    # Validate new password
    if not new_password:
        messages.error(request, 'New password is required.')
        return redirect('users_settings')
    
    if len(new_password) < 8:
        messages.error(request, 'Password must be at least 8 characters long.')
        return redirect('users_settings')
    
    if new_password != confirm_password:
        messages.error(request, 'New passwords do not match.')
        return redirect('users_settings')
    
    # Set new password
    user.set_password(new_password)
    user.save()
    
    # Keep user logged in
    update_session_auth_hash(request, user)
    
    # Log the change
    AuditLog.objects.create(
        user=user,
        action='update',
        model_name='User',
        object_id=str(user.id),
        changes={'password': 'updated'},
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    messages.success(request, 'Password updated successfully.')
    return redirect('users_settings')

@login_required
@require_POST
def update_notifications(request):
    """Update user notification preferences"""
    user = request.user
    
    # Get notification preferences
    notification_preferences = {
        'notify_susar': bool(request.POST.get('notify_susar')),
        'notify_enrollment': bool(request.POST.get('notify_enrollment')),
        'notify_updates': bool(request.POST.get('notify_updates')),
        'notify_reports': bool(request.POST.get('notify_reports')),
        'notify_login': bool(request.POST.get('notify_login')),
        'notify_security': bool(request.POST.get('notify_security')),
        'notify_maintenance': bool(request.POST.get('notify_maintenance')),
        'notification_frequency': request.POST.get('notification_frequency', 'daily'),
    }
    
    # Save to user profile (you might want to create a UserProfile model for this)
    # For now, we'll store it in a JSON field if available, or as a simple example
    if hasattr(user, 'notification_preferences'):
        user.notification_preferences = notification_preferences
        user.save()
    
    messages.success(request, 'Notification preferences updated successfully.')
    return redirect('users_settings')

@login_required
@require_POST
def update_appearance(request):
    """Update user appearance preferences"""
    user = request.user
    
    appearance_preferences = {
        'theme': request.POST.get('theme', 'light'),
        'language': request.POST.get('language', 'en'),
        'timezone': request.POST.get('timezone', 'Africa/Nairobi'),
        'date_format': request.POST.get('date_format', 'dmy'),
        'density': request.POST.get('density', 'normal'),
    }
    
    # Save to user profile (you might want to create a UserProfile model for this)
    # For now, we'll store it in session
    request.session['appearance_preferences'] = appearance_preferences
    
    messages.success(request, 'Appearance settings updated successfully.')
    return redirect('users_settings')

@login_required
def setup_2fa(request):
    """Setup Two-Factor Authentication"""
    # In a real implementation, you would integrate with a 2FA library like django-otp
    # This is a placeholder view
    context = {
        'qr_code_url': '#',  # Placeholder for QR code URL
        'secret_key': 'ABCDEFGHIJKLMNOP',  # Placeholder for secret key
    }
    return render(request, 'users/setup_2fa.html', context)

@login_required
@require_POST
def revoke_session(request):
    """Revoke a specific session"""
    session_id = request.POST.get('session_id')
    
    try:
        session = StaffAttendance.objects.get(
            id=session_id,
            staff=request.user,
            logout_time__isnull=True
        )
        session.logout_time = timezone.now()
        session.save()
        
        messages.success(request, 'Session revoked successfully.')
    except StaffAttendance.DoesNotExist:
        messages.error(request, 'Session not found or already logged out.')
    
    return redirect('users_settings')

@login_required
@require_POST
def revoke_all_sessions(request):
    """Revoke all sessions except current one"""
    current_session_id = request.session.session_key
    
    # Revoke all active sessions except current
    active_sessions = StaffAttendance.objects.filter(
        staff=request.user,
        logout_time__isnull=True
    ).exclude(
        id__in=[request.session.get('attendance_id', 0)]
    )
    
    count = active_sessions.count()
    active_sessions.update(logout_time=timezone.now())
    
    messages.success(request, f'Revoked {count} other sessions.')
    return redirect('users_settings')

@login_required
def export_personal_data(request):
    """Export user's personal data"""
    user = request.user
    
    # Gather user data
    user_data = {
        'profile': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.get_role_display(),
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        },
        'activity': [],
        'sessions': [],
        'audit_logs': [],
    }
    
    # Add attendance data
    attendance_data = StaffAttendance.objects.filter(staff=user).order_by('-login_time')[:100]
    for attendance in attendance_data:
        user_data['sessions'].append({
            'login_time': attendance.login_time.isoformat(),
            'logout_time': attendance.logout_time.isoformat() if attendance.logout_time else None,
            'location': attendance.location,
            'ip_address': str(attendance.ip_address),
            'duration': str(attendance.duration) if attendance.duration else None,
        })
    
    # Add audit logs
    audit_logs = AuditLog.objects.filter(user=user).order_by('-timestamp')[:100]
    for log in audit_logs:
        user_data['audit_logs'].append({
            'timestamp': log.timestamp.isoformat(),
            'action': log.get_action_display(),
            'model_name': log.model_name,
            'object_id': log.object_id,
            'changes': log.changes,
            'ip_address': str(log.ip_address),
        })
    
    # Create JSON response
    response = JsonResponse(user_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="clintrack-data-{user.username}-{timezone.now().date()}.json"'
    
    return response

@login_required
def download_activity_log(request):
    """Download user activity log as CSV"""
    user = request.user
    
    # Get user's audit logs
    audit_logs = AuditLog.objects.filter(user=user).order_by('-timestamp')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="activity-log-{user.username}-{timezone.now().date()}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'Action', 'Model', 'Object ID', 'Changes', 'IP Address'])
    
    for log in audit_logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.get_action_display(),
            log.model_name,
            log.object_id,
            str(log.changes) if log.changes else '',
            str(log.ip_address) if log.ip_address else ''
        ])
    
    return response

@login_required
@require_POST
def delete_account(request):
    """Delete user account"""
    user = request.user
    
    # Double confirmation
    confirmation = request.POST.get('confirmation', '')
    
    if confirmation != 'DELETE':
        messages.error(request, 'Invalid confirmation. Account deletion cancelled.')
        return redirect('users_settings')
    
    # In a real implementation, you might want to:
    # 1. Anonymize data instead of deleting
    # 2. Send confirmation email
    # 3. Keep audit trail
    # 4. Schedule deletion after a grace period
    
    # For now, just mark as inactive and logout
    user.is_active = False
    user.save()
    
    # Log the action
    AuditLog.objects.create(
        user=user,
        action='delete',
        model_name='User',
        object_id=str(user.id),
        changes={'status': 'deactivated'},
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    # Logout user
    from django.contrib.auth import logout
    logout(request)
    
    messages.success(request, 'Your account has been deactivated. You can contact support to restore it within 30 days.')
    return redirect('login')


# ============================================
# ATTENDANCE VIEWS (for attendance_list.html)
# ============================================

@login_required
def attendance_list(request):
    """Staff attendance list with analytics"""
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    role = request.GET.get('role')
    status = request.GET.get('status')
    
    # Base queryset
    attendance_qs = StaffAttendance.objects.select_related('staff').order_by('-login_time')
    
    # Apply filters
    if start_date:
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        attendance_qs = attendance_qs.filter(login_time__gte=start_datetime)
    
    if end_date:
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        attendance_qs = attendance_qs.filter(login_time__lte=end_datetime)
    
    if role:
        attendance_qs = attendance_qs.filter(staff__role=role)
    
    if status == 'active':
        attendance_qs = attendance_qs.filter(logout_time__isnull=True)
    elif status == 'completed':
        attendance_qs = attendance_qs.filter(logout_time__isnull=False)
    
    # Pagination
    paginator = Paginator(attendance_qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # Total logins today
    total_logins_today = StaffAttendance.objects.filter(
        login_time__gte=today_start,
        login_time__lte=today_end
    ).count()
    
    # Currently logged in
    currently_logged_in = StaffAttendance.objects.filter(
        logout_time__isnull=True
    ).count()
    
    # Average session duration (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    avg_session = StaffAttendance.objects.filter(
        logout_time__isnull=False,
        login_time__gte=week_ago
    ).aggregate(
        avg_duration=Avg('logout_time' - 'login_time')
    )
    avg_session_hours = round((avg_session['avg_duration'].total_seconds() / 3600) if avg_session['avg_duration'] else 0, 1)
    
    # Longest session today
    longest_session = StaffAttendance.objects.filter(
        login_time__gte=today_start,
        login_time__lte=today_end,
        logout_time__isnull=False
    ).annotate(
        duration=Max('logout_time' - 'login_time')
    ).order_by('-duration').first()
    
    longest_session_hours = round((longest_session.duration.total_seconds() / 3600) if longest_session else 0, 1)
    
    # Attendance rate (percentage of staff who logged in today)
    total_staff = User.objects.filter(is_active=True).count()
    staff_logged_in_today = StaffAttendance.objects.filter(
        login_time__gte=today_start,
        login_time__lte=today_end
    ).values('staff').distinct().count()
    
    attendance_rate = round((staff_logged_in_today / total_staff * 100) if total_staff > 0 else 0, 1)
    
    # On-time rate (logged in before 9 AM)
    on_time_count = StaffAttendance.objects.filter(
        login_time__gte=today_start,
        login_time__lte=today_end,
        login_time__hour__lt=9
    ).count()
    
    on_time_rate = round((on_time_count / total_logins_today * 100) if total_logins_today > 0 else 0, 1)
    
    # Login growth (compared to yesterday)
    yesterday = today - timedelta(days=1)
    yesterday_start = timezone.make_aware(datetime.combine(yesterday, datetime.min.time()))
    yesterday_end = timezone.make_aware(datetime.combine(yesterday, datetime.max.time()))
    
    logins_yesterday = StaffAttendance.objects.filter(
        login_time__gte=yesterday_start,
        login_time__lte=yesterday_end
    ).count()
    
    login_growth = round(((total_logins_today - logins_yesterday) / logins_yesterday * 100) if logins_yesterday > 0 else 0, 1)
    
    # Active staff (unique users logged in today)
    active_staff = StaffAttendance.objects.filter(
        login_time__gte=today_start,
        login_time__lte=today_end
    ).values('staff__username').distinct().count()
    
    context = {
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date,
        'role': role,
        'status': status,
        'stats': {
            'total_logins': total_logins_today,
            'active_sessions': currently_logged_in,
            'avg_duration': avg_session_hours,
            'attendance_rate': attendance_rate,
            'on_time_rate': on_time_rate,
            'login_growth': login_growth,
            'active_staff': active_staff,
            'longest_session': longest_session_hours,
        },
        'roles': User.ROLE_CHOICES,
    }
    
    return render(request, 'attendance/attendance_list.html', context)

# ============================================
# ATTENDANCE VIEWS
# ============================================

@login_required
def attendance_list(request):
    """List staff attendance"""
    if request.user.role != 'admin':
        messages.error(request, 'Only administrators can view attendance.')
        return redirect('dashboard')
    
    attendances = StaffAttendance.objects.select_related('staff').all()
    
    paginator = Paginator(attendances, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'page_obj': page_obj}
    return render(request, 'attendance/attendance_list.html', context)


# ============================================
# AUDIT LOG VIEWS
# ============================================

@login_required
def audit_logs(request):
    """View audit logs"""
    if request.user.role != 'admin':
        messages.error(request, 'Only administrators can view audit logs.')
        return redirect('dashboard')
    
    logs = AuditLog.objects.select_related('user').all()
    
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {'page_obj': page_obj}
    return render(request, 'audit/audit_logs.html', context)


# ============================================
# REPORTS VIEWS
# ============================================
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, DurationField
from django.db.models.functions import TruncMonth
from datetime import timedelta
import json

@login_required
def reports_index(request):
    """Enhanced Reports dashboard with atomic analysis graphs"""
    if request.user.role not in ['admin', 'coordinator']:
        messages.error(request, 'You do not have permission to view reports.')
        return redirect('dashboard')
    
    # Get date filters from request
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    study_id = request.GET.get('study')
    
    # Set default date range (last 6 months)
    if not start_date:
        start_date = (timezone.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = timezone.now().strftime('%Y-%m-%d')
    
    # Convert to datetime objects
    start_datetime = timezone.datetime.strptime(start_date, '%Y-%m-%d')
    end_datetime = timezone.datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    
    # Base querysets with filters
    participants_qs = Participant.objects.filter(
        created_at__gte=start_datetime,
        created_at__lte=end_datetime
    )
    
    susars_qs = SUSAR.objects.filter(
        created_at__gte=start_datetime,
        created_at__lte=end_datetime
    )
    
    # Filter by study if specified
    if study_id:
        participants_qs = participants_qs.filter(study_id=study_id)
        susars_qs = susars_qs.filter(participant__study_id=study_id)
    
    # 1. PARTICIPANT ENROLLMENT TRENDS
    # Daily enrollment
    daily_enrollment = []
    for i in range((end_datetime - start_datetime).days):
        date = start_datetime + timedelta(days=i)
        count = Participant.objects.filter(enrollment_date=date.date()).count()
        daily_enrollment.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # Monthly enrollment
    monthly_enrollment = Participant.objects.filter(
        enrollment_date__gte=start_datetime.date(),
        enrollment_date__lte=end_datetime.date()
    ).annotate(
        month=TruncMonth('enrollment_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # 2. PARTICIPANT STATUS DISTRIBUTION
    status_distribution = Participant.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 3. STUDY-WISE PARTICIPANT DISTRIBUTION
    study_distribution = Study.objects.annotate(
        participant_count=Count('participants'),
        active_count=Count('participants', filter=Q(participants__status='active')),
        completed_count=Count('participants', filter=Q(participants__status='completed'))
    ).order_by('-participant_count')
    
    # 4. GENDER DISTRIBUTION
    gender_distribution = Participant.objects.values('gender').annotate(
        count=Count('id')
    )
    
    # 5. AGE DISTRIBUTION
    age_distribution = []
    age_ranges = [
        ('<18', Q(date_of_birth__gte=timezone.now() - timedelta(days=18*365))),
        ('18-30', Q(date_of_birth__lt=timezone.now() - timedelta(days=18*365)) & 
                  Q(date_of_birth__gte=timezone.now() - timedelta(days=30*365))),
        ('31-45', Q(date_of_birth__lt=timezone.now() - timedelta(days=30*365)) & 
                  Q(date_of_birth__gte=timezone.now() - timedelta(days=45*365))),
        ('46-60', Q(date_of_birth__lt=timezone.now() - timedelta(days=45*365)) & 
                  Q(date_of_birth__gte=timezone.now() - timedelta(days=60*365))),
        ('>60', Q(date_of_birth__lt=timezone.now() - timedelta(days=60*365)))
    ]
    
    for label, query in age_ranges:
        count = Participant.objects.filter(query).count()
        age_distribution.append({'label': label, 'count': count})
    
    # 6. SUSAR ANALYSIS
    susar_severity_distribution = SUSAR.objects.values('severity').annotate(
        count=Count('id')
    ).order_by('-count')
    
    susar_outcome_distribution = SUSAR.objects.values('outcome').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Monthly SUSAR trend
    monthly_susar_trend = SUSAR.objects.filter(
        created_at__gte=start_datetime,
        created_at__lte=end_datetime
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # 7. ATTENDANCE ANALYSIS
    staff_attendance = StaffAttendance.objects.filter(
        login_time__gte=start_datetime,
        login_time__lte=end_datetime
    ).values('staff__username').annotate(
        login_count=Count('id'),
        avg_duration=Avg(F('logout_time') - F('login_time'))
    ).order_by('-login_count')[:10]
    
    # 8. STUDY COMPLETION RATES
    study_completion = []
    for study in Study.objects.filter(is_active=True):
        total = study.participants.count()
        completed = study.participants.filter(status='completed').count()
        if total > 0:
            completion_rate = (completed / total) * 100
            study_completion.append({
                'study': study.name,
                'code': study.code,
                'total': total,
                'completed': completed,
                'completion_rate': round(completion_rate, 1)
            })
    
    # 9. LOST TO FOLLOW-UP ANALYSIS
    # Calculate days since enrollment for lost participants
    lost_analysis = Participant.objects.filter(status='lost').values(
        'study__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Calculate average enrollment days separately for each study
    for item in lost_analysis:
        study_name = item['study__name']
        lost_participants = Participant.objects.filter(
            status='lost',
            study__name=study_name
        )
        
        # Calculate average days since enrollment
        total_days = 0
        participant_count = 0
        for participant in lost_participants:
            if participant.enrollment_date:
                days_diff = (timezone.now().date() - participant.enrollment_date).days
                total_days += days_diff
                participant_count += 1
        
        if participant_count > 0:
            item['avg_enrollment_days'] = round(total_days / participant_count, 1)
        else:
            item['avg_enrollment_days'] = 0
    
    # 10. AUDIT LOG SUMMARY
    audit_summary = AuditLog.objects.filter(
        timestamp__gte=start_datetime,
        timestamp__lte=end_datetime
    ).values('action').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Prepare data for charts
    context = {
        # Filter parameters
        'start_date': start_date,
        'end_date': end_date,
        'study_id': study_id,
        'studies': Study.objects.all(),
        
        # Chart data
        'daily_enrollment': json.dumps(daily_enrollment),
        'monthly_enrollment': json.dumps(list(monthly_enrollment), default=str),
        'status_distribution': json.dumps(list(status_distribution)),
        'study_distribution': json.dumps([
            {
                'name': study.name,
                'code': study.code,
                'total': study.participant_count,
                'active': study.active_count,
                'completed': study.completed_count
            } for study in study_distribution
        ]),
        'gender_distribution': json.dumps(list(gender_distribution)),
        'age_distribution': json.dumps(age_distribution),
        'susar_severity_distribution': json.dumps(list(susar_severity_distribution)),
        'susar_outcome_distribution': json.dumps(list(susar_outcome_distribution)),
        'monthly_susar_trend': json.dumps(list(monthly_susar_trend), default=str),
        'staff_attendance': json.dumps([
            {
                'staff': item['staff__username'],
                'login_count': item['login_count'],
                'avg_duration': item['avg_duration'].total_seconds() / 3600 if item['avg_duration'] else 0
            } for item in staff_attendance
        ]),
        'study_completion': json.dumps(study_completion),
        'lost_analysis': json.dumps(list(lost_analysis), default=str),
        'audit_summary': json.dumps(list(audit_summary)),
        
        # Summary statistics
        'total_participants': participants_qs.count(),
        'total_susars': susars_qs.count(),
        'avg_participants_per_study': round(participants_qs.count() / max(Study.objects.count(), 1), 1),
        'participant_growth_rate': calculate_growth_rate(participants_qs, 'enrollment_date'),
        'susar_resolution_rate': calculate_susar_resolution_rate(susars_qs),
        'avg_study_duration': calculate_avg_study_duration(),
        'follow_up_compliance': calculate_follow_up_compliance(susars_qs),
        
        # Data for tables
        'top_studies': study_distribution[:5],
        'recent_susars': SUSAR.objects.order_by('-onset_date')[:10],
        'recent_participants': Participant.objects.order_by('-created_at')[:10],
        'staff_activity': staff_attendance,
    }
    
    return render(request, 'reports/reports_index.html', context)


# Helper functions for calculations
def calculate_growth_rate(queryset, date_field):
    """Calculate month-over-month growth rate"""
    current_month = timezone.now().month
    previous_month = current_month - 1 if current_month > 1 else 12
    
    current_count = queryset.filter(
        **{f'{date_field}__month': current_month}
    ).count()
    
    previous_count = queryset.filter(
        **{f'{date_field}__month': previous_month}
    ).count()
    
    if previous_count > 0:
        return round(((current_count - previous_count) / previous_count) * 100, 1)
    return 0.0

def calculate_susar_resolution_rate(susars_qs):
    """Calculate SUSAR resolution rate"""
    resolved = susars_qs.filter(
        Q(outcome='recovered') | Q(outcome='recovered_sequelae')
    ).count()
    
    total = susars_qs.count()
    
    if total > 0:
        return round((resolved / total) * 100, 1)
    return 0.0

def calculate_avg_study_duration():
    """Calculate average study duration in days"""
    from django.db.models import Avg
    from django.db.models.functions import Cast
    from django.db.models import IntegerField
    
    studies = Study.objects.filter(start_date__isnull=False, end_date__isnull=False)
    
    total_days = 0
    count = 0
    
    for study in studies:
        duration = (study.end_date - study.start_date).days
        total_days += duration
        count += 1
    
    if count > 0:
        return round(total_days / count, 1)
    return 0.0

def calculate_follow_up_compliance(susars_qs):
    """Calculate follow-up compliance rate"""
    with_follow_up = susars_qs.filter(
        follow_up_required=True,
        follow_up_notes__isnull=False
    ).exclude(follow_up_notes='').count()
    
    total_follow_up = susars_qs.filter(follow_up_required=True).count()
    
    if total_follow_up > 0:
        return round((with_follow_up / total_follow_up) * 100, 1)
    return 0.0