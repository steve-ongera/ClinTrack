# ============================================
# forms.py - ClinTrack Forms
# ============================================

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Participant, Study, SUSAR, User, StaffAttendance


# ============================================
# PARTICIPANT FORM
# ============================================

class ParticipantForm(forms.ModelForm):
    """Form for creating and updating participants"""
    
    class Meta:
        model = Participant
        fields = [
            'participant_id', 'study', 'first_name', 'last_name',
            'date_of_birth', 'gender', 'primary_phone', 'secondary_phone',
            'email', 'location', 'sub_location', 'county',
            'nearest_landmark', 'status', 'enrollment_date', 'notes'
        ]
        widgets = {
            'participant_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., STUDY-001'
            }),
            'study': forms.Select(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'primary_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254712345678'
            }),
            'secondary_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254712345678 (Optional)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com (Optional)'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Village/Estate/Area'
            }),
            'sub_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sub-location (Optional)'
            }),
            'county': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'County (Optional)'
            }),
            'nearest_landmark': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Nearest landmark or directions'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'enrollment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Additional notes (Optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make certain fields required
        self.fields['participant_id'].required = True
        self.fields['study'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['primary_phone'].required = True
        self.fields['location'].required = True
        
        # Filter only active studies
        self.fields['study'].queryset = Study.objects.filter(is_active=True)


# ============================================
# STUDY FORM
# ============================================

class StudyForm(forms.ModelForm):
    """Form for creating and updating studies"""
    
    class Meta:
        model = Study
        fields = [
            'name', 'code', 'description', 'start_date',
            'end_date', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Study Name'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Study Code (e.g., STD-001)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Study description'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError(
                'End date cannot be earlier than start date.'
            )
        
        return cleaned_data


# ============================================
# SUSAR FORM
# ============================================

class SUSARForm(forms.ModelForm):
    """Form for creating and updating SUSAR reports"""
    
    class Meta:
        model = SUSAR
        fields = [
            'susar_id', 'participant', 'event_description',
            'onset_date', 'detection_date', 'severity', 'outcome',
            'is_related_to_study', 'causality_assessment',
            'actions_taken', 'hospitalization_required',
            'reported_to_irb', 'irb_report_date',
            'reported_to_sponsor', 'sponsor_report_date',
            'follow_up_required', 'follow_up_notes'
        ]
        widgets = {
            'susar_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., SUSAR-2024-001'
            }),
            'participant': forms.Select(attrs={
                'class': 'form-control'
            }),
            'event_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed description of the adverse event'
            }),
            'onset_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'detection_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'severity': forms.Select(attrs={'class': 'form-control'}),
            'outcome': forms.Select(attrs={'class': 'form-control'}),
            'is_related_to_study': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'causality_assessment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Assessment of causality (Optional)'
            }),
            'actions_taken': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Actions taken in response to the event'
            }),
            'hospitalization_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'reported_to_irb': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'irb_report_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'reported_to_sponsor': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'sponsor_report_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'follow_up_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'follow_up_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Follow-up notes (Optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make required fields explicit
        self.fields['susar_id'].required = True
        self.fields['participant'].required = True
        self.fields['event_description'].required = True
        self.fields['onset_date'].required = True
        self.fields['severity'].required = True
        self.fields['actions_taken'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate IRB reporting
        reported_to_irb = cleaned_data.get('reported_to_irb')
        irb_report_date = cleaned_data.get('irb_report_date')
        
        if reported_to_irb and not irb_report_date:
            raise forms.ValidationError(
                'IRB report date is required when reported to IRB.'
            )
        
        # Validate sponsor reporting
        reported_to_sponsor = cleaned_data.get('reported_to_sponsor')
        sponsor_report_date = cleaned_data.get('sponsor_report_date')
        
        if reported_to_sponsor and not sponsor_report_date:
            raise forms.ValidationError(
                'Sponsor report date is required when reported to sponsor.'
            )
        
        return cleaned_data


# ============================================
# USER/STAFF FORM
# ============================================

class UserForm(UserCreationForm):
    """Form for creating new staff users"""
    
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'phone_number', 'role', 'is_active', 'password1', 'password2'
        ]
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254712345678'
            }),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
        
        # Make fields required
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True


class UserUpdateForm(forms.ModelForm):
    """Form for updating existing staff users (without password)"""
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email',
            'phone_number', 'role', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254712345678'
            }),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


# ============================================
# STAFF ATTENDANCE FORM
# ============================================

class StaffAttendanceForm(forms.ModelForm):
    """Form for staff attendance logging"""
    
    class Meta:
        model = StaffAttendance
        fields = ['staff', 'login_time', 'logout_time', 'location', 'notes']
        widgets = {
            'staff': forms.Select(attrs={'class': 'form-control'}),
            'login_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'logout_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Work location'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes (Optional)'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        login_time = cleaned_data.get('login_time')
        logout_time = cleaned_data.get('logout_time')
        
        if login_time and logout_time and logout_time < login_time:
            raise forms.ValidationError(
                'Logout time cannot be earlier than login time.'
            )
        
        return cleaned_data


# ============================================
# SEARCH FORMS
# ============================================

class ParticipantSearchForm(forms.Form):
    """Advanced participant search form"""
    
    participant_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Participant ID'
        })
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number'
        })
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Location'
        })
    )
    study = forms.ModelChoiceField(
        queryset=Study.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='All Studies'
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Participant.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )