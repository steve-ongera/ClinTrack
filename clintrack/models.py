# ClinTrack - Clinical Research Participant Locator System
# Complete Django Models and Setup Guide

"""
INSTALLATION REQUIREMENTS:
pip install django djangorestframework django-cors-headers pillow django-phonenumber-field phonenumbers
"""

# ============================================
# models.py
# ============================================

from django.db import models
from django.contrib.auth.models import AbstractUser
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone

# Custom User Model with Role-Based Access
class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('coordinator', 'Study Coordinator'),
        ('staff', 'Research Staff'),
        ('viewer', 'Viewer Only'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    phone_number = PhoneNumberField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# Study Model
class Study(models.Model):
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'studies'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


# Participant Model - Core of the Locator System
class Participant(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('U', 'Prefer not to say'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('withdrawn', 'Withdrawn'),
        ('lost', 'Lost to Follow-up'),
        ('screening', 'Screening'),
    ]
    
    # Participant Identifiers
    participant_id = models.CharField(max_length=50, unique=True, db_index=True)
    study = models.ForeignKey(Study, on_delete=models.PROTECT, related_name='participants')
    
    # Personal Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='U')
    
    # Contact Information
    primary_phone = PhoneNumberField()
    secondary_phone = PhoneNumberField(blank=True, null=True)
    email = models.EmailField(blank=True)
    
    # Location Information
    location = models.CharField(max_length=200, help_text="Village/Estate/Area")
    sub_location = models.CharField(max_length=200, blank=True)
    county = models.CharField(max_length=100, blank=True)
    nearest_landmark = models.TextField(blank=True, help_text="Directions or nearest landmark")
    
    # Study Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='screening')
    enrollment_date = models.DateField(null=True, blank=True)
    
    # Additional Information
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_participants')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'participants'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['participant_id']),
            models.Index(fields=['study', 'status']),
            models.Index(fields=['last_name', 'first_name']),
        ]
    
    def __str__(self):
        return f"{self.participant_id} - {self.first_name} {self.last_name}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


# SUSAR (Suspected Unexpected Serious Adverse Reaction) Tracking
class SUSAR(models.Model):
    SEVERITY_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('life_threatening', 'Life Threatening'),
        ('fatal', 'Fatal'),
    ]
    
    OUTCOME_CHOICES = [
        ('recovered', 'Recovered/Resolved'),
        ('recovering', 'Recovering/Resolving'),
        ('not_recovered', 'Not Recovered'),
        ('recovered_sequelae', 'Recovered with Sequelae'),
        ('fatal', 'Fatal'),
        ('unknown', 'Unknown'),
    ]
    
    susar_id = models.CharField(max_length=50, unique=True, db_index=True)
    participant = models.ForeignKey(Participant, on_delete=models.PROTECT, related_name='susars')
    
    # Event Details
    event_description = models.TextField()
    onset_date = models.DateTimeField()
    detection_date = models.DateTimeField(default=timezone.now)
    
    # Severity and Outcome
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default='unknown')
    
    # Causality
    is_related_to_study = models.BooleanField(default=False)
    causality_assessment = models.TextField(blank=True)
    
    # Actions Taken
    actions_taken = models.TextField()
    hospitalization_required = models.BooleanField(default=False)
    
    # Reporting
    reported_to_irb = models.BooleanField(default=False)
    irb_report_date = models.DateField(null=True, blank=True)
    reported_to_sponsor = models.BooleanField(default=False)
    sponsor_report_date = models.DateField(null=True, blank=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(default=True)
    follow_up_notes = models.TextField(blank=True)
    
    # Audit Trail
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reported_susars')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'susars'
        ordering = ['-onset_date']
        verbose_name = 'SUSAR'
        verbose_name_plural = 'SUSARs'
    
    def __str__(self):
        return f"{self.susar_id} - {self.participant.participant_id}"


# Staff Attendance/Login Tracking
class StaffAttendance(models.Model):
    staff = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'staff_attendance'
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.staff.username} - {self.login_time.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def duration(self):
        if self.logout_time:
            return self.logout_time - self.login_time
        return None


# Audit Log for tracking all changes
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    changes = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} - {self.timestamp}"

