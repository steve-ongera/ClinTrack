# ============================================
# urls.py - ClinTrack URL Configuration
# ============================================

from django.urls import path
from . import views


urlpatterns = [
    # ============================================
    # Authentication URLs
    # ============================================
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ============================================
    # Dashboard URLs - Role Based
    # ============================================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/coordinator/', views.coordinator_dashboard, name='coordinator_dashboard'),
    path('dashboard/staff/', views.staff_dashboard, name='staff_dashboard'),
    path('dashboard/viewer/', views.viewer_dashboard, name='viewer_dashboard'),
    
    # ============================================
    # API Endpoints for Charts (JSON)
    # ============================================
    path('api/charts/enrollment/', views.enrollment_chart_data, name='enrollment_chart_data'),
    path('api/charts/susar/', views.susar_chart_data, name='susar_chart_data'),
    path('api/charts/status/', views.status_chart_data, name='status_chart_data'),
    
    # Participants
    path('participants/', views.participant_list, name='participant_list'),
    path('participants/create/', views.participant_create, name='participant_create'),
    path('participants/<int:pk>/', views.participant_detail, name='participant_detail'),
    path('participants/<int:pk>/edit/', views.participant_update, name='participant_update'),
    path('participants/<int:pk>/delete/', views.participant_delete, name='participant_delete'),
    path('participants/search/', views.participant_search, name='participant_search'),
    
    # Studies
    path('studies/', views.study_list, name='study_list'),
    path('studies/create/', views.study_create, name='study_create'),
    path('studies/<int:pk>/', views.study_detail, name='study_detail'),
    path('studies/<int:pk>/edit/', views.study_update, name='study_update'),
    
    # SUSARs
    path('susars/', views.susars_list, name='susars_list'),
    path('susars/create/', views.susars_create, name='susars_create'),
    path('susars/<int:pk>/', views.susars_detail, name='susars_detail'),
    path('susars/<int:pk>/edit/', views.susars_update, name='susars_update'),
    path('susars/pending/', views.susars_pending, name='susars_pending'),
    
    # Users/Staff
    path('staff/', views.users_list, name='users_list'),
    path('staff/create/', views.users_create, name='users_create'),
    path('profile/', views.users_profile, name='users_profile'),
    path('settings/', views.users_settings, name='users_settings'),
    
    # Attendance
    path('attendance/', views.attendance_list, name='attendance_list'),
    
    # Audit Logs
    path('audit/', views.audit_logs, name='audit_logs'),
    
    # Reports
    path('reports/', views.reports_index, name='reports_index'),
]


