# ClinTrack - Clinical Research Participant Locator System

[![Django](https://img.shields.io/badge/Django-4.2+-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-success.svg)]()

A comprehensive, role-based clinical research management system designed to streamline participant tracking, adverse event monitoring, and staff attendance management for research institutions.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## 🎯 Overview

ClinTrack is a Django-based web application built to address the critical need for efficient participant management in clinical research settings. The system replaces traditional paper-based tracking with a secure, digital solution that enables real-time access to participant contact information, location data, and adverse event tracking.

### Key Objectives

- **Digitize Participant Records**: Eliminate paper-based systems and reduce data retrieval time
- **Enhance Safety Monitoring**: Track and report Suspected Unexpected Serious Adverse Reactions (SUSARs)
- **Improve Accountability**: Monitor staff attendance and system access
- **Ensure Data Security**: Implement role-based access control and comprehensive audit trails
- **Support Multiple Studies**: Manage multiple concurrent research studies from a single platform

## ✨ Features

### Core Functionality

#### 🔐 Authentication & Authorization
- Secure user registration and login system
- Role-based access control (Admin, Coordinator, Staff, Viewer)
- Session management with timeout protection
- Password reset and recovery mechanisms

#### 👥 Participant Management
- **Comprehensive Participant Profiles**
  - Unique participant ID generation
  - Dual contact numbers (primary & secondary)
  - Detailed location tracking (village, sub-location, county)
  - Landmark-based directions
  - Study enrollment status tracking
- **Advanced Search & Filtering**
  - Search by participant ID, name, phone number, or location
  - Filter by study, status, enrollment date
  - Export participant lists to CSV/Excel
- **Full CRUD Operations**
  - Create, Read, Update, Delete with permission controls
  - Audit trail for all modifications

#### 🚨 SUSAR Tracking
- Comprehensive adverse event documentation
- Severity and outcome classification
- Causality assessment tools
- IRB and sponsor reporting workflows
- Follow-up tracking and management
- Automated notifications for critical events

#### 📊 Staff Management
- Login/logout time tracking
- Location-based attendance monitoring
- IP address logging for security
- Duration calculations and reporting
- Activity dashboards

#### 📝 Audit & Compliance
- Complete audit log of all system activities
- User action tracking (Create, Update, Delete, View)
- JSON-formatted change tracking
- IP address and timestamp logging
- Compliance report generation

### Study Management
- Multi-study support within single installation
- Study-specific participant isolation
- Active/inactive study status management
- Study timeline tracking

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 4.2+
- **Database**: PostgreSQL 14+ (recommended) / SQLite (development)
- **API**: Django REST Framework 3.14+
- **Authentication**: Django Token Authentication

### Frontend (Coming Soon)
- **Framework**: React.js / Vue.js
- **UI Components**: Tailwind CSS / Material-UI
- **State Management**: Redux / Vuex

### Additional Technologies
- **Phone Number Validation**: django-phonenumber-field
- **CORS Handling**: django-cors-headers
- **File Handling**: Pillow
- **Data Export**: pandas, openpyxl

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- PostgreSQL 14+ (for production)
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/steveongera/clintrack.git
cd clintrack
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Environment Configuration

Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration (PostgreSQL)
DB_NAME=clintrack_db
DB_USER=clintrack_user
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432

# Email Configuration (for password reset)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Security Settings
SESSION_COOKIE_AGE=3600
SESSION_SAVE_EVERY_REQUEST=True
SECURE_SSL_REDIRECT=False
```

### Step 5: Database Setup

```bash
# Create database migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Step 6: Seed Initial Data

```bash
# Seed studies and realistic Kenyan participant data
python manage.py seed_data --years=2 --participants=500
```

### Step 7: Run Development Server

```bash
python manage.py runserver
```

Access the application at `http://localhost:8000`

## ⚙️ Configuration

### Database Configuration

#### Development (SQLite)
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

#### Production (PostgreSQL)
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}
```

### Role-Based Permissions

| Role | Participants | SUSAR | Reports | User Mgmt | Settings |
|------|-------------|-------|---------|-----------|----------|
| Admin | Full CRUD | Full CRUD | All | Full CRUD | Full |
| Coordinator | Full CRUD | Full CRUD | All | View | View |
| Staff | Create, View, Update | Create, View | Own | None | None |
| Viewer | View Only | View | Own | None | None |

## 📖 Usage

### Creating a New Participant

1. Navigate to **Participants** → **Add New**
2. Select the study (Gates MRI or GB43374/OLE)
3. Enter participant details:
   - Personal information (name, DOB, gender)
   - Contact numbers (at least primary phone)
   - Location details (village, sub-location, county, landmarks)
4. Set enrollment status
5. Click **Save**

### Recording a SUSAR

1. Navigate to **SUSAR** → **Report New**
2. Select participant from dropdown
3. Enter event details:
   - Description of adverse event
   - Onset date and detection date
   - Severity and outcome
4. Complete causality assessment
5. Document actions taken
6. Mark reporting status (IRB, Sponsor)
7. Click **Submit**

### Searching for Participants

Use the global search bar or advanced filters:
- **Quick Search**: Enter participant ID, name, or phone number
- **Advanced Filters**: Filter by study, status, location, enrollment date range
- **Export Results**: Download filtered results as CSV or Excel

### Tracking Staff Attendance

Staff attendance is automatically logged on login. To manually log:
1. Navigate to **Staff** → **Attendance**
2. View login/logout times
3. Generate attendance reports by date range

## 📁 Project Structure

```
clintrack/
├── clintrack_project/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── clintrack/                  # Main application
│   ├── models.py              # Database models
│   ├── views.py               # View controllers
│   ├── serializers.py         # API serializers
│   ├── urls.py                # URL routing
│   ├── admin.py               # Admin interface
│   ├── permissions.py         # Custom permissions
│   └── management/
│       └── commands/
│           └── seed_data.py   # Data seeding script
├── templates/                  # HTML templates
├── static/                     # Static files (CSS, JS, images)
├── media/                      # User uploaded files
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── README.md                  # This file
└── manage.py                  # Django management script
```

## 🔒 Security

ClinTrack implements multiple layers of security:

- **Authentication**: Token-based authentication with session management
- **Authorization**: Role-based access control (RBAC)
- **Audit Logging**: Complete audit trail of all user actions
- **Data Encryption**: Sensitive data encrypted at rest
- **IP Tracking**: IP address logging for security monitoring
- **CSRF Protection**: Built-in Django CSRF protection
- **XSS Prevention**: Input sanitization and output encoding
- **SQL Injection Prevention**: ORM-based database queries

### Security Best Practices

1. Always use HTTPS in production
2. Regularly update dependencies
3. Use strong, unique passwords
4. Enable two-factor authentication (when available)
5. Regular security audits and penetration testing
6. Backup data regularly
7. Monitor audit logs for suspicious activity

## 🤝 Contributing

Contributions are welcome! This is a personal innovation project, but I appreciate community input.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Coding Standards

- Follow PEP 8 style guide for Python code
- Write meaningful commit messages
- Include docstrings for all functions and classes
- Add unit tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Steve Ongera**

- Email: [steveongera001@gmail.com](mailto:steveongera001@gmail.com)
- GitHub: [@steveongera](https://github.com/steveongera)
- LinkedIn: [Steve Ongera](https://linkedin.com/in/steveongera)

## 🙏 Acknowledgments

- Inspired by the need for efficient clinical research management
- Built to support healthcare professionals in resource-constrained settings
- Thanks to the Django and Python communities for excellent documentation

## 📞 Support

For support, bug reports, or feature requests:

- **Email**: steveongera001@gmail.com
- **Issues**: [GitHub Issues](https://github.com/steveongera/clintrack/issues)
- **Discussions**: [GitHub Discussions](https://github.com/steveongera/clintrack/discussions)

## 🗺️ Roadmap

### Version 1.0 (Current)
- ✅ Core participant management
- ✅ SUSAR tracking
- ✅ Staff attendance
- ✅ Role-based access control
- ✅ Audit logging

### Version 1.1 (Planned)
- [ ] Advanced reporting and analytics
- [ ] Email notifications
- [ ] SMS integration for participant reminders
- [ ] Mobile application (Android/iOS)
- [ ] Data visualization dashboards
- [ ] Export to regulatory formats

### Version 2.0 (Future)
- [ ] Multi-language support (English, Swahili)
- [ ] Integration with electronic health records (EHR)
- [ ] AI-powered data quality checks
- [ ] Blockchain-based audit trails
- [ ] Cloud deployment options

---

**Project Type**: Personal Innovation Project  
**Status**: Active Development  
**Last Updated**: January 2026

© 2024-2026 Steve Ongera. All Rights Reserved.