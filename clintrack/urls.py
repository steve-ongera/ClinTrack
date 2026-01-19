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
]


