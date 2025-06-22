# -*- coding: utf-8 -*-
import os
import json
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Common diseases and their corresponding specializations
COMMON_DISEASES = {
    'Heart Disease': 'Cardiology',
    'Diabetes': 'Endocrinology',
    'Arthritis': 'Rheumatology',
    'Asthma': 'Pulmonology',
    'Depression': 'Psychiatry',
    'High Blood Pressure': 'Cardiology',
    'Migraine': 'Neurology',
    'Thyroid Disorders': 'Endocrinology',
    'Allergies': 'Allergy and Immunology',
    'Back Pain': 'Orthopedics'
}

# Template filter for date formatting
@app.template_filter('format_date')
def format_date_filter(date_str, format='%A, %B %d, %Y'):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime(format)
    except (ValueError, TypeError):
        return date_str

# Data storage initialization
def init_data_dirs():
    """Create necessary directories for data storage"""
    os.makedirs('data/patients', exist_ok=True)
    os.makedirs('data/doctors', exist_ok=True)
    os.makedirs('data/appointments', exist_ok=True)
    os.makedirs('data/availability', exist_ok=True)
    
    # Create sample doctors if none exist
    if len(os.listdir('data/doctors')) == 0:
        specialties = ['Cardiology', 'Dermatology', 'Neurology', 'Pediatrics', 'Orthopedics']
        locations = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']
        for i in range(1, 6):
            doctor_data = {
                'id': str(uuid.uuid4()),
                'full_name': f'Dr. Smith {i}',
                'email': f'dr.smith{i}@example.com',
                'phone': f'123456789{i}',
                'password': generate_password_hash(f'doctor{i}'),
                'specialization': specialties[i-1],
                'location': locations[i-1],
                'consultation_fee': 500,
                'bio': f'Experienced {specialties[i-1]} specialist with 10+ years of practice',
                'created_at': datetime.now().isoformat()
            }
            save_data('doctors', doctor_data['id'], doctor_data)
            
            # Set default availability (Mon-Fri, 9AM-5PM)
            for day in range(5):
                availability_data = {
                    'id': str(uuid.uuid4()),
                    'doctor_id': doctor_data['id'],
                    'day_of_week': day,
                    'start_time': '09:00',
                    'end_time': '17:00',
                    'is_available': True
                }
                save_data('availability', availability_data['id'], availability_data)

def save_data(data_type, data_id, data):
    """Save data to a JSON file"""
    with open(f'data/{data_type}/{data_id}.json', 'w') as f:
        json.dump(data, f, indent=4)

def load_data(data_type, data_id):
    """Load data from a JSON file"""
    try:
        with open(f'data/{data_type}/{data_id}.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def load_all(data_type):
    """Load all data files of a specific type"""
    data = []
    for filename in os.listdir(f'data/{data_type}'):
        if filename.endswith('.json'):
            item = load_data(data_type, filename[:-5])
            if item:
                data.append(item)
    return data

def find_data(data_type, field, value):
    """Find data by field value"""
    for item in load_all(data_type):
        if item.get(field) == value:
            return item
    return None

def filter_data(data_type, filters):
    """Filter data by multiple criteria"""
    results = []
    for item in load_all(data_type):
        match = True
        for field, value in filters.items():
            if item.get(field) != value:
                match = False
                break
        if match:
            results.append(item)
    return results

# Decorators
def patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'patient':
            flash('Please login as patient to access this page', 'danger')
            return redirect(url_for('patient_login'))
        return f(*args, **kwargs)
    return decorated_function

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_type' not in session or session['user_type'] != 'doctor':
            flash('Please login as doctor to access this page', 'danger')
            return redirect(url_for('doctor_login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# Patient routes
@app.route('/patient/register', methods=['GET', 'POST'])
def patient_register():
    if request.method == 'POST':
        patient_data = {
            'id': str(uuid.uuid4()),
            'full_name': request.form['full_name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'password': generate_password_hash(request.form['password']),
            'created_at': datetime.now().isoformat()
        }
        
        if find_data('patients', 'email', patient_data['email']):
            flash('Email already exists!', 'danger')
        else:
            save_data('patients', patient_data['id'], patient_data)
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('patient_login'))
    
    return render_template('patient/register.html')

@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        patient = find_data('patients', 'email', request.form['email'])
        if patient and check_password_hash(patient['password'], request.form['password']):
            session['user_id'] = patient['id']
            session['user_type'] = 'patient'
            session['full_name'] = patient['full_name']
            flash('Login successful!', 'success')
            return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid email or password!', 'danger')
    
    return render_template('patient/login.html')

@app.route('/patient/dashboard')
@patient_required
def patient_dashboard():
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get all patient appointments
    appointments = []
    for appt in load_all('appointments'):
        if appt['patient_id'] == session['user_id']:
            doctor = load_data('doctors', appt['doctor_id'])
            if doctor:
                appt_data = {
                    **appt,
                    'doctor_name': doctor['full_name'],
                    'specialization': doctor['specialization'],
                    'location': doctor['location']
                }
                appointments.append(appt_data)
    
    # Separate upcoming and past appointments
    upcoming = [a for a in appointments 
               if a['status'] == 'booked' and a['date'] >= today]
    past = [a for a in appointments 
           if a['status'] == 'completed' or a['date'] < today]
    
    # Sort appointments
    upcoming.sort(key=lambda x: (x['date'], x['time']))
    past.sort(key=lambda x: (x['date'], x['time']), reverse=True)
    
    return render_template('patient/dashboard.html', 
                         upcoming=upcoming, 
                         past=past,
                         common_diseases=COMMON_DISEASES.keys())

@app.route('/find-doctors/<disease>')
@patient_required
def find_doctors_by_disease(disease):
    if disease not in COMMON_DISEASES:
        flash('Invalid disease selection', 'danger')
        return redirect(url_for('patient_dashboard'))
    
    specialization = COMMON_DISEASES[disease]
    doctors = filter_data('doctors', {'specialization': specialization})
    
    return render_template('patient/doctors_list.html',
                         disease=disease,
                         specialization=specialization,
                         doctors=doctors)

@app.route('/patient/search', methods=['GET', 'POST'])
@patient_required
def doctor_search():
    doctors = load_all('doctors')
    specialties = sorted(set(d['specialization'] for d in doctors))
    locations = sorted(set(d['location'] for d in doctors))
    
    if request.method == 'POST':
        specialization = request.form.get('specialization')
        location = request.form.get('location')
        doctors = [d for d in doctors 
                  if (not specialization or d['specialization'] == specialization) and
                     (not location or d['location'] == location)]
    
    return render_template('patient/search.html',
                         doctors=doctors,
                         specialties=specialties,
                         locations=locations)

@app.route('/patient/book/<doctor_id>', methods=['GET', 'POST'])
@patient_required
def book_appointment(doctor_id):
    doctor = load_data('doctors', doctor_id)
    if not doctor:
        flash('Doctor not found', 'danger')
        return redirect(url_for('doctor_search'))
    
    if request.method == 'POST':
        date = request.form['date']
        time = request.form['time']
        
        # Check if slot is available
        existing = filter_data('appointments', {
            'doctor_id': doctor_id,
            'date': date,
            'time': time,
            'status': 'booked'
        })
        
        if existing:
            flash('This time slot is already booked!', 'danger')
        else:
            appointment_data = {
                'id': str(uuid.uuid4()),
                'patient_id': session['user_id'],
                'doctor_id': doctor_id,
                'date': date,
                'time': time,
                'status': 'booked',
                'notes': request.form.get('notes', ''),
                'created_at': datetime.now().isoformat()
            }
            save_data('appointments', appointment_data['id'], appointment_data)
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('patient_dashboard'))
    
    # Get available slots for the next 7 days
    available_slots = []
    for i in range(7):
        day = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
        day_of_week = (datetime.now() + timedelta(days=i)).weekday()
        
        # Get doctor's availability for this day
        availability = filter_data('availability', {
            'doctor_id': doctor_id,
            'day_of_week': day_of_week,
            'is_available': True
        })
        
        if availability:
            for avail in availability:
                # Get booked slots for this day
                booked = filter_data('appointments', {
                    'doctor_id': doctor_id,
                    'date': day,
                    'status': 'booked'
                })
                booked_times = [appt['time'] for appt in booked]
                
                # Generate available slots
                start = datetime.strptime(avail['start_time'], '%H:%M')
                end = datetime.strptime(avail['end_time'], '%H:%M')
                
                current = start
                while current + timedelta(minutes=30) <= end:
                    slot_time = current.strftime('%H:%M')
                    if slot_time not in booked_times:
                        available_slots.append({
                            'date': day,
                            'day_name': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                                        'Friday', 'Saturday', 'Sunday'][day_of_week],
                            'slot_time': slot_time
                        })
                    current += timedelta(minutes=30)
    
    return render_template('patient/book.html', 
                         doctor=doctor, 
                         available_slots=available_slots)

@app.route('/patient/cancel/<appointment_id>')
@patient_required
def cancel_appointment(appointment_id):
    appointment = load_data('appointments', appointment_id)
    if appointment and appointment['patient_id'] == session['user_id']:
        appointment['status'] = 'cancelled'
        save_data('appointments', appointment_id, appointment)
        flash('Appointment cancelled successfully', 'success')
    else:
        flash('Appointment not found or you are not authorized to cancel it', 'danger')
    return redirect(url_for('patient_dashboard'))

# Doctor routes
@app.route('/doctor/register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        doctor_data = {
            'id': str(uuid.uuid4()),
            'full_name': request.form['full_name'],
            'email': request.form['email'],
            'phone': request.form['phone'],
            'password': generate_password_hash(request.form['password']),
            'specialization': request.form['specialization'],
            'location': request.form['location'],
            'consultation_fee': 500,
            'bio': request.form.get('bio', ''),
            'created_at': datetime.now().isoformat()
        }
        
        if find_data('doctors', 'email', doctor_data['email']):
            flash('Email already exists!', 'danger')
        else:
            save_data('doctors', doctor_data['id'], doctor_data)
            
            # Set default availability (Mon-Fri, 9AM-5PM)
            for day in range(5):
                availability_data = {
                    'id': str(uuid.uuid4()),
                    'doctor_id': doctor_data['id'],
                    'day_of_week': day,
                    'start_time': '09:00',
                    'end_time': '17:00',
                    'is_available': True
                }
                save_data('availability', availability_data['id'], availability_data)
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('doctor_login'))
    
    return render_template('doctor/register.html')

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        doctor = find_data('doctors', 'email', request.form['email'])
        if doctor and check_password_hash(doctor['password'], request.form['password']):
            session['user_id'] = doctor['id']
            session['user_type'] = 'doctor'
            session['full_name'] = doctor['full_name']
            flash('Login successful!', 'success')
            return redirect(url_for('doctor_dashboard'))
        else:
            flash('Invalid email or password!', 'danger')
    
    return render_template('doctor/login.html')

@app.route('/doctor/dashboard')
@doctor_required
def doctor_dashboard():
    today = datetime.now().strftime('%Y-%m-%d')
    today_formatted = datetime.now().strftime('%A, %B %d, %Y')
    
    # Get appointments
    appointments = []
    for appt in load_all('appointments'):
        if appt['doctor_id'] == session['user_id']:
            patient = load_data('patients', appt['patient_id'])
            if patient:
                appt_data = {
                    **appt,
                    'patient_name': patient['full_name'],
                    'patient_phone': patient['phone']
                }
                appointments.append(appt_data)
    
    # Categorize appointments
    todays_appointments = [a for a in appointments 
                         if a['date'] == today and a['status'] == 'booked']
    upcoming = [a for a in appointments 
               if a['date'] > today and a['status'] == 'booked']
    past = [a for a in appointments 
           if a['status'] == 'completed' or a['date'] < today]
    
    # Sort appointments
    todays_appointments.sort(key=lambda x: x['time'])
    upcoming.sort(key=lambda x: (x['date'], x['time']))
    past.sort(key=lambda x: (x['date'], x['time']), reverse=True)
    
    return render_template('doctor/dashboard.html',
                         todays_appointments=todays_appointments,
                         upcoming=upcoming,
                         past=past,
                         today_formatted=today_formatted)

@app.route('/doctor/availability', methods=['GET', 'POST'])
@doctor_required
def manage_availability():
    if request.method == 'POST':
        # Remove existing availability
        for avail in load_all('availability'):
            if avail['doctor_id'] == session['user_id']:
                os.remove(f"data/availability/{avail['id']}.json")
        
        # Add new availability
        days = request.form.getlist('day')
        start_times = request.form.getlist('start_time')
        end_times = request.form.getlist('end_time')
        
        for day, start_time, end_time in zip(days, start_times, end_times):
            if day and start_time and end_time:
                availability_data = {
                    'id': str(uuid.uuid4()),
                    'doctor_id': session['user_id'],
                    'day_of_week': int(day),
                    'start_time': start_time,
                    'end_time': end_time,
                    'is_available': True
                }
                save_data('availability', availability_data['id'], availability_data)
        
        flash('Availability updated successfully!', 'success')
        return redirect(url_for('doctor_dashboard'))
    
    # Get current availability
    availability = filter_data('availability', {'doctor_id': session['user_id']})
    availability.sort(key=lambda x: (x['day_of_week'], x['start_time']))
    
    days = [
        {'id': 0, 'name': 'Monday'},
        {'id': 1, 'name': 'Tuesday'},
        {'id': 2, 'name': 'Wednesday'},
        {'id': 3, 'name': 'Thursday'},
        {'id': 4, 'name': 'Friday'},
        {'id': 5, 'name': 'Saturday'},
        {'id': 6, 'name': 'Sunday'}
    ]
    
    return render_template('doctor/availability.html', 
                         availability=availability, 
                         days=days)

@app.route('/doctor/appointment/<appointment_id>/<action>')
@doctor_required
def manage_appointment(appointment_id, action):
    valid_actions = ['complete', 'cancel']
    if action not in valid_actions:
        flash('Invalid action', 'danger')
        return redirect(url_for('doctor_dashboard'))
    
    appointment = load_data('appointments', appointment_id)
    if appointment and appointment['doctor_id'] == session['user_id']:
        if action == 'complete':
            appointment['status'] = 'completed'
            flash('Appointment marked as completed', 'success')
        elif action == 'cancel':
            appointment['status'] = 'cancelled'
            flash('Appointment cancelled', 'success')
        
        save_data('appointments', appointment_id, appointment)
    else:
        flash('Appointment not found or you are not authorized to modify it', 'danger')
    
    return redirect(url_for('doctor_dashboard'))

# API endpoints
@app.route('/api/doctor/<doctor_id>/slots')
def get_available_slots(doctor_id):
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date parameter is required'}), 400
    
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_of_week = date_obj.weekday()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Get doctor's availability
    availability = filter_data('availability', {
        'doctor_id': doctor_id,
        'day_of_week': day_of_week,
        'is_available': True
    })
    
    # Get booked slots
    booked_slots = [a['time'] for a in load_all('appointments')
                  if a['doctor_id'] == doctor_id and
                  a['date'] == date_str and
                  a['status'] == 'booked']
    
    # Generate available slots
    available_slots = []
    for avail in availability:
        start = datetime.strptime(avail['start_time'], '%H:%M')
        end = datetime.strptime(avail['end_time'], '%H:%M')
        current = start
        
        while current + timedelta(minutes=30) <= end:
            slot_time = current.strftime('%H:%M')
            if slot_time not in booked_slots:
                available_slots.append(slot_time)
            current += timedelta(minutes=30)
    
    return jsonify({'slots': available_slots})

if __name__ == '__main__':
    init_data_dirs()
    app.run(debug=True)