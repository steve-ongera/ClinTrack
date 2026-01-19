"""
ClinTrack Data Seeding Command
Seeds realistic Kenyan clinical research data spanning 2 years

Usage:
    python manage.py seed_data --years=2 --participants=500
    python manage.py seed_data --clear  # Clear existing data first
    python manage.py seed_data --participants=1000 --susars=50
"""

import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from clintrack.models import Study, Participant, SUSAR, StaffAttendance

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with realistic Kenyan clinical research data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--years',
            type=int,
            default=2,
            help='Number of years of historical data to generate (default: 2)'
        )
        parser.add_argument(
            '--participants',
            type=int,
            default=500,
            help='Number of participants to create (default: 500)'
        )
        parser.add_argument(
            '--susars',
            type=int,
            default=30,
            help='Number of SUSARs to create (default: 30)'
        )
        parser.add_argument(
            '--staff',
            type=int,
            default=10,
            help='Number of staff members to create (default: 10)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding'
        )

    def handle(self, *args, **options):
        years = options['years']
        num_participants = options['participants']
        num_susars = options['susars']
        num_staff = options['staff']
        clear_data = options['clear']

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('ClinTrack Data Seeding Started'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        if clear_data:
            self.clear_existing_data()

        # Seed in order
        studies = self.create_studies()
        staff_users = self.create_staff_members(num_staff)
        participants = self.create_participants(studies, staff_users, num_participants, years)
        self.create_susars(participants, staff_users, num_susars, years)
        self.create_staff_attendance(staff_users, years)

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 70))
        self.stdout.write(self.style.SUCCESS('✅ Data Seeding Completed Successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.print_summary(studies, staff_users, participants)

    def clear_existing_data(self):
        """Clear existing data from the database"""
        self.stdout.write(self.style.WARNING('\n🗑️  Clearing existing data...'))
        
        StaffAttendance.objects.all().delete()
        SUSAR.objects.all().delete()
        Participant.objects.all().delete()
        Study.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        
        self.stdout.write(self.style.SUCCESS('✓ Existing data cleared'))

    def create_studies(self):
        """Create the two main studies"""
        self.stdout.write(self.style.HTTP_INFO('\n📚 Creating Studies...'))
        
        studies = []
        
        gates_study, created = Study.objects.get_or_create(
            code='GATES-MRI',
            defaults={
                'name': 'Gates MRI Study',
                'description': 'Gates Foundation funded MRI research study focusing on malaria vaccine development',
                'start_date': datetime.now().date() - timedelta(days=730),
                'is_active': True
            }
        )
        studies.append(gates_study)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {gates_study.name}'))
        
        ole_study, created = Study.objects.get_or_create(
            code='GB43374-OLE',
            defaults={
                'name': 'GB43374/OLE Study',
                'description': 'Open Label Extension study for GB43374 vaccine trial',
                'start_date': datetime.now().date() - timedelta(days=700),
                'is_active': True
            }
        )
        studies.append(ole_study)
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {ole_study.name}'))
        
        return studies

    def create_staff_members(self, count):
        """Create staff user accounts"""
        self.stdout.write(self.style.HTTP_INFO(f'\n👥 Creating {count} Staff Members...'))
        
        kenyan_first_names = [
            'John', 'Mary', 'Peter', 'Jane', 'David', 'Grace', 'James', 'Elizabeth',
            'Michael', 'Sarah', 'Daniel', 'Faith', 'Joseph', 'Ruth', 'Samuel', 'Esther',
            'Kevin', 'Ann', 'Brian', 'Lucy', 'Dennis', 'Catherine', 'Eric', 'Rose',
            'Patrick', 'Agnes', 'Francis', 'Susan', 'George', 'Margaret'
        ]
        
        kenyan_last_names = [
            'Kamau', 'Wanjiru', 'Otieno', 'Achieng', 'Mwangi', 'Njeri', 'Omondi', 'Nyambura',
            'Kipchoge', 'Wambui', 'Mutua', 'Chebet', 'Odhiambo', 'Wangari', 'Kimani', 'Jepkosgei',
            'Karanja', 'Muthoni', 'Chege', 'Kerubo', 'Ngugi', 'Njoki', 'Kibet', 'Wanyama',
            'Ongeri', 'Nyokabi', 'Koech', 'Wairimu', 'Rotich', 'Mumbua'
        ]
        
        roles = ['admin', 'coordinator', 'staff', 'viewer']
        staff_users = []
        
        for i in range(count):
            first_name = random.choice(kenyan_first_names)
            last_name = random.choice(kenyan_last_names)
            username = f"{first_name.lower()}.{last_name.lower()}{i+1}"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': f"{username}@clintrack.co.ke",
                    'role': roles[i % len(roles)],
                    'phone_number': f'+254{random.randint(700000000, 799999999)}',
                    'is_active': True,
                    'is_staff': True if i < 3 else False
                }
            )
            
            if created:
                user.set_password('ClinTrack2024!')
                user.save()
                staff_users.append(user)
                self.stdout.write(f'  ✓ Created: {user.username} ({user.get_role_display()})')
        
        return staff_users

    def create_participants(self, studies, staff_users, count, years):
        """Create realistic Kenyan participant records"""
        self.stdout.write(self.style.HTTP_INFO(f'\n🏥 Creating {count} Participants...'))
        
        # Kenyan names
        first_names = [
            'Akinyi', 'Atieno', 'Awuor', 'Adhiambo', 'Akoth', 'Apiyo', 'Benta', 'Beatrice',
            'Caroline', 'Charity', 'Christine', 'Doreen', 'Diana', 'Emily', 'Eunice', 'Esther',
            'Faith', 'Florence', 'Gladys', 'Grace', 'Hellen', 'Ivy', 'Jane', 'Janet',
            'Joyce', 'Judith', 'Joy', 'Kamene', 'Kerubo', 'Kemunto', 'Kwamboka', 'Lucy',
            'Lydia', 'Margaret', 'Mary', 'Mercy', 'Monica', 'Nancy', 'Naomi', 'Njeri',
            'Njoki', 'Nyambura', 'Nyokabi', 'Patience', 'Phyllis', 'Priscilla', 'Rachel', 'Rebecca',
            'Rose', 'Ruth', 'Salome', 'Sarah', 'Susan', 'Tabitha', 'Teresa', 'Violet',
            'Wanjiru', 'Wangari', 'Wairimu', 'Wambui', 'Amos', 'Andrew', 'Anthony', 'Benjamin',
            'Brian', 'Charles', 'Daniel', 'David', 'Dennis', 'Duncan', 'Edwin', 'Eric',
            'Evans', 'Francis', 'Fred', 'Geoffrey', 'George', 'Henry', 'Isaac', 'James',
            'John', 'Joseph', 'Joshua', 'Kennedy', 'Kevin', 'Martin', 'Michael', 'Moses',
            'Nicholas', 'Patrick', 'Paul', 'Peter', 'Philip', 'Richard', 'Robert', 'Samuel',
            'Simon', 'Stephen', 'Thomas', 'Timothy', 'Victor', 'Vincent', 'William'
        ]
        
        last_names = [
            'Kamau', 'Mwangi', 'Njoroge', 'Wanjiru', 'Nyambura', 'Karanja', 'Kimani', 'Njeri',
            'Otieno', 'Omondi', 'Odhiambo', 'Achieng', 'Adhiambo', 'Onyango', 'Owino', 'Ouma',
            'Mutua', 'Muthoka', 'Musyoka', 'Ndunda', 'Kivuva', 'Muema', 'Kyalo', 'Mumbua',
            'Kipchoge', 'Kibet', 'Koech', 'Rotich', 'Cheruiyot', 'Lagat', 'Keter', 'Jepkosgei',
            'Wafula', 'Wekesa', 'Barasa', 'Nekesa', 'Wanyama', 'Namukose', 'Simiyu', 'Mukhwana',
            'Muturi', 'Waweru', 'Waithaka', 'Mureithi', 'Kariuki', 'Ngugi', 'Macharia', 'Gichuki',
            'Chege', 'Githinji', 'Gitonga', 'Wachira', 'Mbugua', 'Kinyanjui', 'Githuku', 'Gachanja',
            'Ongeri', 'Onyancha', 'Nyamweya', 'Mogaka', 'Omare', 'Momanyi', 'Nyakerario', 'Bosire'
        ]
        
        # Kenyan locations - Coastal region (Mtwapa area)
        locations = [
            'Mtwapa', 'Shanzu', 'Bamburi', 'Nyali', 'Kongowea', 'Junda', 'Kisauni',
            'Mtopanga', 'Kikambala', 'Vipingo', 'Takaungu', 'Kilifi', 'Mnarani',
            'Tezo', 'Chumani', 'Mtwapa Creek', 'Jumba Ruins', 'Kanamai', 'Shimo La Tewa',
            'Bombolulu', 'Mishomoroni', 'Majaoni', 'Bangladesh', 'Magongo', 'Ziwa La Ngombe'
        ]
        
        sub_locations = [
            'Township', 'Market Area', 'Chief\'s Camp', 'Shopping Centre', 'Beach Front',
            'Makao Mapya', 'Industrial Area', 'Residential Estate', 'Village Center'
        ]
        
        landmarks = [
            'Near Mtwapa Mall', 'Opposite Police Station', 'Next to Benki Kuu',
            'Behind Primary School', 'Near Health Centre', 'Opposite Chief\'s Office',
            'Next to Mosque', 'Near Catholic Church', 'Behind Market',
            'Opposite Petrol Station', 'Near Water Tank', 'Next to Post Office',
            'Behind Bus Stop', 'Near Community Hall', 'Opposite Dispensary'
        ]
        
        statuses = ['active', 'completed', 'withdrawn', 'lost', 'screening']
        
        participants = []
        start_date = datetime.now() - timedelta(days=years * 365)
        
        for i in range(count):
            study = random.choice(studies)
            
            # Generate enrollment date within the time range
            days_offset = random.randint(0, years * 365)
            enrollment_date = start_date + timedelta(days=days_offset)
            
            # Generate participant ID
            participant_id = f"{study.code}-{str(i+1).zfill(4)}"
            
            # Generate realistic age (18-65 years old)
            age_years = random.randint(18, 65)
            dob = enrollment_date.date() - timedelta(days=age_years * 365)
            
            # Status logic - newer participants more likely to be active
            days_since_enrollment = (datetime.now().date() - enrollment_date.date()).days
            if days_since_enrollment < 180:
                status = random.choice(['active', 'screening', 'active', 'active'])
            elif days_since_enrollment < 365:
                status = random.choice(['active', 'active', 'completed'])
            else:
                status = random.choice(statuses)
            
            participant = Participant.objects.create(
                participant_id=participant_id,
                study=study,
                first_name=random.choice(first_names),
                last_name=random.choice(last_names),
                date_of_birth=dob,
                gender=random.choice(['M', 'F']),
                primary_phone=f'+254{random.randint(700000000, 799999999)}',
                secondary_phone=f'+254{random.randint(700000000, 799999999)}' if random.random() > 0.3 else None,
                email=f'participant{i+1}@email.com' if random.random() > 0.5 else '',
                location=random.choice(locations),
                sub_location=random.choice(sub_locations),
                county='Kilifi',
                nearest_landmark=random.choice(landmarks),
                status=status,
                enrollment_date=enrollment_date.date(),
                created_by=random.choice(staff_users),
                created_at=enrollment_date
            )
            
            participants.append(participant)
            
            if (i + 1) % 100 == 0:
                self.stdout.write(f'  ✓ Created {i + 1}/{count} participants...')
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created all {count} participants'))
        return participants

    def create_susars(self, participants, staff_users, count, years):
        """Create SUSAR records"""
        self.stdout.write(self.style.HTTP_INFO(f'\n⚠️  Creating {count} SUSAR Records...'))
        
        event_descriptions = [
            'Fever with chills reported 24 hours post-vaccination',
            'Severe headache and nausea reported by participant',
            'Injection site reaction with swelling and redness',
            'Allergic reaction with mild rash on upper body',
            'Dizziness and fatigue lasting more than 48 hours',
            'Muscle pain and weakness in lower extremities',
            'Respiratory distress with difficulty breathing',
            'Gastrointestinal symptoms including vomiting and diarrhea',
            'Syncope episode during clinic visit',
            'Cardiac palpitations and chest discomfort',
            'Neurological symptoms including numbness and tingling',
            'Severe joint pain affecting daily activities'
        ]
        
        actions = [
            'Participant advised to rest and stay hydrated. Paracetamol prescribed.',
            'Emergency response activated. Participant transported to hospital.',
            'Topical corticosteroid applied. Follow-up scheduled.',
            'Antihistamine administered. Vital signs monitored.',
            'Participant observed for 4 hours. Symptoms resolved.',
            'Referred to specialist for further evaluation.',
            'Hospitalization required. IV fluids administered.',
            'Symptomatic treatment provided. Daily monitoring initiated.'
        ]
        
        severities = ['mild', 'moderate', 'severe']
        outcomes = ['recovered', 'recovering', 'not_recovered', 'recovered_sequelae']
        
        start_date = datetime.now() - timedelta(days=years * 365)
        
        for i in range(count):
            participant = random.choice(participants)
            
            # SUSAR more likely in recently enrolled participants
            max_days = min((datetime.now().date() - participant.enrollment_date).days, years * 365)
            if max_days > 0:
                days_offset = random.randint(0, max_days)
                onset_date = participant.enrollment_date + timedelta(days=days_offset)
                
                detection_date = onset_date + timedelta(hours=random.randint(1, 72))
                
                severity = random.choice(severities)
                is_severe = severity == 'severe'
                
                susar = SUSAR.objects.create(
                    susar_id=f"SUSAR-{datetime.now().year}-{str(i+1).zfill(4)}",
                    participant=participant,
                    event_description=random.choice(event_descriptions),
                    onset_date=onset_date,
                    detection_date=detection_date,
                    severity=severity,
                    outcome=random.choice(outcomes),
                    is_related_to_study=random.choice([True, False, True]),
                    causality_assessment='Under investigation' if random.random() > 0.5 else 'Possibly related to study intervention',
                    actions_taken=random.choice(actions),
                    hospitalization_required=is_severe,
                    reported_to_irb=is_severe or random.random() > 0.5,
                    irb_report_date=onset_date + timedelta(days=random.randint(1, 7)) if is_severe else None,
                    reported_to_sponsor=is_severe or random.random() > 0.6,
                    sponsor_report_date=onset_date + timedelta(days=random.randint(1, 5)) if is_severe else None,
                    follow_up_required=True,
                    reported_by=random.choice(staff_users)
                )
                
                if (i + 1) % 10 == 0:
                    self.stdout.write(f'  ✓ Created {i + 1}/{count} SUSARs...')
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created all {count} SUSAR records'))

    def create_staff_attendance(self, staff_users, years):
        """Create staff attendance records"""
        self.stdout.write(self.style.HTTP_INFO('\n📅 Creating Staff Attendance Records...'))
        
        start_date = datetime.now() - timedelta(days=years * 365)
        total_records = 0
        
        for user in staff_users:
            # Create attendance for random workdays
            current_date = start_date
            while current_date < datetime.now():
                # Skip weekends
                if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                    # 85% chance of attendance on workdays
                    if random.random() > 0.15:
                        login_time = current_date + timedelta(
                            hours=random.randint(7, 9),
                            minutes=random.randint(0, 59)
                        )
                        
                        # 95% chance they logged out
                        if random.random() > 0.05:
                            logout_time = login_time + timedelta(
                                hours=random.randint(7, 10),
                                minutes=random.randint(0, 59)
                            )
                        else:
                            logout_time = None
                        
                        StaffAttendance.objects.create(
                            staff=user,
                            login_time=login_time,
                            logout_time=logout_time,
                            location='Mtwapa Research Center',
                            ip_address=f'192.168.1.{random.randint(10, 250)}'
                        )
                        total_records += 1
                
                current_date += timedelta(days=1)
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {total_records} attendance records'))

    def print_summary(self, studies, staff_users, participants):
        """Print summary of created data"""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('📊 DATA SEEDING SUMMARY'))
        self.stdout.write('=' * 70)
        
        self.stdout.write(f'\n📚 Studies Created: {len(studies)}')
        for study in studies:
            participant_count = Participant.objects.filter(study=study).count()
            self.stdout.write(f'   • {study.name}: {participant_count} participants')
        
        self.stdout.write(f'\n👥 Staff Members: {len(staff_users)}')
        for role in ['admin', 'coordinator', 'staff', 'viewer']:
            count = User.objects.filter(role=role).count()
            self.stdout.write(f'   • {role.title()}: {count}')
        
        self.stdout.write(f'\n🏥 Participants: {len(participants)}')
        for status in ['active', 'completed', 'withdrawn', 'lost', 'screening']:
            count = Participant.objects.filter(status=status).count()
            self.stdout.write(f'   • {status.title()}: {count}')
        
        susar_count = SUSAR.objects.count()
        self.stdout.write(f'\n⚠️  SUSARs: {susar_count}')
        
        attendance_count = StaffAttendance.objects.count()
        self.stdout.write(f'\n📅 Attendance Records: {attendance_count}')
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('✅ You can now login with any staff account:'))
        self.stdout.write(self.style.WARNING('   Username: john.kamau1 (or any created username)'))
        self.stdout.write(self.style.WARNING('   Password: ClinTrack2024!'))
        self.stdout.write('=' * 70 + '\n')