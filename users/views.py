from datetime import date, datetime, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.timezone import now

from django.urls import reverse
from django.conf import settings

import numpy
import base64
from PIL import Image
import io

from users.models import (
    Hospital,
    Doctor,
    CustomUser,
    Patient,
    Visit,
    DoctorEditRequest
)

# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////

def is_admin(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_superuser:
            return function(request, *args, **kwargs)
        messages.error(request, 'Unauthorized access. Admin privileges required.')
        return redirect('common_login')
    return wrap

def is_hospital(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.user_type == 'HOSPITAL':
            if 'hospitalID' in kwargs:
                if request.user.userID == int(kwargs['hospitalID']):
                    return function(request, *args, **kwargs)
            else:
                return function(request, *args, **kwargs)
        messages.error(request, 'Unauthorized access. Hospital privileges required.')
        return redirect('common_login')
    return wrap

def is_doctor(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        print(f"User is_authenticated: {request.user.is_authenticated}")
        if request.user.is_authenticated and request.user.user_type == 'DOCTOR':
            print(f"User is a doctor: {request.user.userID}")
            if 'doctorID' in kwargs:
                print(f"DoctorID in kwargs: {kwargs['doctorID']}")
                if request.user.userID == int(kwargs['doctorID']):
                    print("User id and doctor id match")
                    return function(request, *args, **kwargs)
                else:
                    print("User id and doctor id do not match")
            else:
                return function(request, *args, **kwargs)
        else:
            print("User is not authenticated or not a doctor")
        messages.error(request, 'Unauthorized access. Doctor privileges required.')
        return redirect('common_login')
    return wrap


# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////

def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def home(request):
    return render(request, 'others/home.html')

def common_login(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not email:
            messages.error(request, "Please enter an email address")
            return render(request, "others/common_login.html")

        user = CustomUser.objects.filter(email=email).first()
        if user and user.check_password(password):
            login(request, user)

            if user.is_superuser:
                return redirect('admin_dashboard')
            elif user.user_type == 'HOSPITAL':
                return redirect('hospital_dashboard', hospitalID=user.userID)
            elif user.user_type == 'DOCTOR':
                return redirect('doctor_dashboard', doctorID=user.userID)
            elif user.user_type == 'PATIENT':
                return redirect('patient_dashboard', patientID=user.userID)
        else:
            messages.error(request, "Invalid email or password")

    return render(request, "others/common_login.html")

# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////

@login_required
@is_admin
def admin_dashboard(request):
    search_query = request.GET.get('search', '')
    page_number = request.GET.get('page', 1)

    if (search_query):
        hospitals = Hospital.objects.filter(user__name__icontains=search_query).select_related('user', 'added_by_admin')
    else:
        hospitals = Hospital.objects.all().select_related('user', 'added_by_admin')

    for hospital in hospitals:
        hospital.number_of_patients = 0
        doctors = hospital.hospital_doctors.all()
        for doctor in doctors:
            hospital.number_of_patients += doctor.doctor_patients.count()

    # Paginate results
    paginator = Paginator(hospitals, 5)  # Show 5 hospitals per page
    paginated_hospitals = paginator.get_page(page_number)

    return render(request, "admin/admin_dashboard.html", {
        'search_query': search_query,
        'search_results': paginated_hospitals if search_query else None,
        'hospitals': paginated_hospitals if not search_query else None})

# hospitals = Hospital.objects.all().select_related('user', 'added_by_admin')
    # # print(f"Found {hospitals.count()} hospitals")  # Debug line
    # # for hospital in hospitals:
    # #     print(f"Hospital: {hospital.user.name}")  # Debug line
    # paginator = Paginator(hospitals, 3)  # Show 3 hospitals per page
    # page_number = request.GET.get('page')
    # hospitals = paginator.get_page(page_number)
        
    # return render(request, "admin/admin_dashboard.html", {'hospitals': hospitals, 'admin_name': request.user.name})

@login_required
@is_admin
def admin_edit_profile(request):
    if request.method == "POST":
        request.user.name = request.POST.get('name')
        request.user.email = request.POST.get('email')
        if 'profile_photo' in request.FILES:
            request.user.profile_photo = request.FILES['profile_photo']
        if request.POST.get('password'):
            request.user.set_password(request.POST.get('password'))
        request.user.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Profile updated successfully!')
    return redirect('admin_dashboard')

@login_required
@is_admin
def admin_register_hospital(request):
    if request.method == "POST":
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        name = request.POST.get('name')
        address = request.POST.get('address')
        password = request.POST.get('password')

        print(f"Attempting to register hospital - Name: {name}, Email: {email}")
        
        try:
            # Start transaction
            with transaction.atomic():
                # Check if user exists
                if CustomUser.objects.filter(email=email).exists():
                    raise ValueError(f'Email {email} is already registered!')
                if phone_number and CustomUser.objects.filter(phone_number=phone_number).exists():
                    raise ValueError(f'Phone number {phone_number} is already registered!')

                # Create user
                user = CustomUser.objects.create(
                    email=email,
                    name=name,
                    username=email,
                    phone_number=phone_number,
                    user_type='HOSPITAL'
                )
                user.set_password(password)
                user.save()

                # Create hospital
                hospital = Hospital.objects.create(
                    user=user,
                    address=address,
                    added_by_admin=request.user
                )
                
                print(f"Successfully created hospital - ID: {hospital.user.userID}, Name: {hospital.user.name}")
                messages.success(request, f'Hospital {hospital.user.name} registered successfully!')
                return redirect('admin_dashboard')

        except Exception as e:
            print(f"Error creating hospital: {str(e)}")
            messages.error(request, str(e))

    return render(request, 'admin/admin_register_hospital.html', {'admin_name': request.user.name})

# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////

@login_required
@is_hospital
def hospital_dashboard(request, hospitalID):
    hospital = get_object_or_404(Hospital, user__userID=hospitalID)
    doctors = hospital.hospital_doctors.all()
    for doctor in doctors:
        if doctor.user.date_of_birth:
            doctor.user.age = calculate_age(doctor.user.date_of_birth)
        else:
            doctor.user.age = 'N/A'
    return render(request, 'hospital/hospital_dashboard.html', {'hospital': hospital, 'doctors': doctors})

@login_required
@is_hospital
def hospital_edit_profile(request):
    if request.method == "POST":
        try:
            hospital = Hospital.objects.get(user=request.user)
            
            # Update user details
            request.user.name = request.POST.get('name')
            request.user.email = request.POST.get('email')
            request.user.phone_number = request.POST.get('phone_number')
            if 'profile_photo' in request.FILES:
                request.user.profile_photo = request.FILES['profile_photo']
            
            # Update password if provided
            if request.POST.get('password'):
                request.user.set_password(request.POST.get('password'))
            
            request.user.save()
            
            # Update hospital details
            hospital.address = request.POST.get('address')
            hospital.save()
            
            # Keep user logged in after password change
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Profile updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
            
    return redirect('hospital_dashboard', hospitalID=request.user.userID)

@login_required
@is_hospital
def hospital_register_doctor(request, hospitalID):
    hospital = get_object_or_404(Hospital, user__userID=hospitalID)
    
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'hospital/hospital_register_doctor.html', {'hospital': hospital})

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, f'Email {email} is already registered!')
        else:
            try:
                with transaction.atomic():
                    # Create CustomUser with date_of_birth field
                    user = CustomUser.objects.create(
                        email=email,
                        name=request.POST.get('name'),
                        phone_number=request.POST.get('phone_number'),
                        username=email,
                        user_type='DOCTOR',
                        gender=request.POST.get('gender'),
                        date_of_birth=request.POST.get('date_of_birth')  # Changed from age to date_of_birth
                    )
                    user.set_password(password)
                    user.save()

                    # Create Doctor
                    doctor = Doctor.objects.create(
                        user=user,
                        hospital=hospital,
                        specialization=request.POST.get('specialization'),
                        highest_qualification=request.POST.get('highest_qualification'),
                        experience=0  # Set default value
                    )
                    
                    # Increment number_of_doctors
                    hospital.number_of_doctors += 1
                    hospital.save()

                    messages.success(request, f'Doctor {doctor.user.name} added successfully!')
                    return redirect('hospital_dashboard', hospitalID=hospitalID)

            except Exception as e:
                messages.error(request, f'Error creating doctor: {str(e)}')

    return render(request, 'hospital/hospital_register_doctor.html', {'hospital': hospital})



# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////

@login_required
@is_doctor
def doctor_dashboard(request, doctorID):
    doctor = get_object_or_404(Doctor, user__userID=doctorID)
    patients = doctor.doctor_patients.all()
    
    # Calculate registration dates if needed
    for patient in patients:
        if not hasattr(patient, 'dateofregistration'):
            patient.dateofregistration = patient.user.date_of_registration

    return render(request, 'doctor/doctor_dashboard.html', {
        'doctor': doctor, 
        'patients': patients
    })

@login_required
@is_doctor
def doctor_edit_profile(request, doctorID):
    doctor = get_object_or_404(Doctor, user__userID=doctorID)

    if request.method == "POST":
        doctor.user.name = request.POST.get('name')
        doctor.user.email = request.POST.get('email')
        doctor.user.date_of_birth = request.POST.get('date_of_birth')
        doctor.user.gender = request.POST.get('gender')

        if 'profile_photo' in request.FILES:
            doctor.user.profile_photo = request.FILES['profile_photo']
        
        doctor.user.save()

        doctor.specialization = request.POST.get('specialization')
        doctor.highest_qualification = request.POST.get('highest_qualification')
        doctor.experience = request.POST.get('experience')
        doctor.save()

        messages.success(request, 'Profile updated successfully!')
        return redirect('doctor_dashboard', doctorID=doctor.user.userID)

    return render(request, 'doctor/doctor_edit_profile.html', {'doctor': doctor})

@login_required
@is_doctor
def doctor_register_patient(request, doctorID):
    doctor = get_object_or_404(Doctor, user__userID=doctorID)

    if request.method == "POST":
        email = request.POST.get('email')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, f'Email {email} is already registered!')
        else:
            try:
                with transaction.atomic():
                    # Create CustomUser
                    user = CustomUser.objects.create(
                        email=email,
                        name=request.POST.get('name'),
                        username=email,
                        user_type='PATIENT',
                        gender=request.POST.get('gender'),
                        phone_number=request.POST.get('phone_number'),
                        date_of_birth=request.POST.get('date_of_birth') or None
                    )
                    user.set_password(request.POST.get('password'))
                    user.save()

                    # Create Patient with primary_doctor instead of doctor
                    patient = Patient.objects.create(
                        user=user,
                        primary_doctor=doctor,  # Changed from doctor to primary_doctor
                        illness_name=request.POST.get('illness_name'),
                        illness_description=request.POST.get('illness_description'),
                        additional_remarks=request.POST.get('additional_remarks')
                    )

                    messages.success(request, f'Patient {patient.user.name} added successfully!')
                    return redirect('doctor_dashboard', doctorID=doctorID)
            except Exception as e:
                messages.error(request, f'Error creating patient: {str(e)}')

    return render(request, 'doctor/doctor_register_patient.html', {'doctor': doctor})

@login_required
@is_doctor
def doctor_view_other_patients(request, doctorID):
    doctor = get_object_or_404(Doctor, user__userID=doctorID)

    # Get all patients where the doctor is neither primary nor secondary
    other_patients = Patient.objects.exclude(
        Q(primary_doctor=doctor) |
        Q(secondary_doctors=doctor)
    )

    return render(request, 'doctor/doctor_view_other_patients.html', {
        'doctor': doctor,
        'other_patients': other_patients,
        'view_only': True
    })

@login_required
@is_doctor
def doctor_patient_make_visit(request, doctorID, patientID):
    doctor = get_object_or_404(Doctor, user__userID=doctorID)
    patient = get_object_or_404(Patient, user__userID=patientID)
    
    # Check if the doctor is either the primary or a secondary doctor of the patient
    if not (patient.is_primary_doctor(doctor) or patient.is_secondary_doctor(doctor)):
        messages.error(request, 'You do not have permission to schedule visits for this patient.')
        return redirect('doctor_dashboard', doctorID=doctorID)
    
    if request.method == "POST":
        try:
            # Get visit_date and visit_time from POST, default to now if not provided
            visit_date_str = request.POST.get('visit_date')
            visit_time_str = request.POST.get('visit_time')
            if visit_date_str:
                visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d").date()
            else:
                visit_date = date.today()
            if visit_time_str:
                visit_time = datetime.strptime(visit_time_str, "%H:%M").time()
            else:
                visit_time = datetime.now().time()

            # Create new visit
            visit = Visit.objects.create(
                doctor=doctor,
                patient=patient,
                visit_date=visit_date,
                visit_time=visit_time,
                status='Pending',
                remarks=request.POST.get('remarks', '')
            )
            
            # Increment visit count
            patient.number_of_visits += 1
            patient.save()
            
            # numpy file upload handling
            numpy_file = request.FILES.get('numpy_file')
            print(f"Uploaded files: {request.FILES}") #debugging line.

            if numpy_file:
                # Save in 'visits' subfolder inside media
                file_name = f'visits/patient_{patient.user.userID}_visit_{visit.visitID}.numpy'
                file_path = default_storage.save(file_name, numpy_file)
                print(f"Saved file path: {file_path}") #debug
                visit.file_path = file_path
                visit.save()
            
            messages.success(request, f'Visit scheduled successfully for {visit_date} at {visit_time.strftime("%H:%M")}')
            return redirect('patient_dashboard', doctorID=doctorID, patientID=patientID)
        
        except Exception as e:
            print(f"Error scheduling visit: {str(e)}") #debugging line.
            messages.error(request, f'Error scheduling visit: {str(e)}')
    
    return render(request, 'doctor/patient/doctor_patient_make_visit.html', {
        'doctor': doctor,
        'patient': patient
    })

@login_required
@is_doctor
def doctor_request_edit_access(request, doctorID, patientID):
    if request.method == "POST":
        doctor = get_object_or_404(Doctor, user__userID=doctorID)
        patient = get_object_or_404(Patient, user__userID=patientID)
        
        # Check if doctor is already a secondary doctor
        if patient.is_secondary_doctor(doctor):
            messages.error(request, 'You are already a secondary doctor for this patient.')
            return redirect('doctor_view_other_patients', doctorID=doctorID)

        reason = request.POST.get('reason')
        print(f"Requesting doctor: {doctor.user.name}, Patient: {patient.user.name}, Reason: {reason}")

        # Check if there's already a pending request
        existing_request = DoctorEditRequest.objects.filter(
            requesting_doctor=doctor,
            patient=patient,
            status='PENDING'
        ).first()

        if existing_request:
            messages.error(request, 'You already have a pending request for this patient.')
            return redirect('doctor_view_other_patients', doctorID=doctorID)

        # Check the latest entry for the combination of primary doctor, secondary doctor, and patient
        latest_request = DoctorEditRequest.objects.filter(
            requesting_doctor=doctor,
            patient=patient
        ).order_by('-request_date').first()

        if (latest_request):
            if latest_request.retrieved_access_date is None and latest_request.status == 'APPROVED':
                messages.error(request, 'You still have access to this patient.')
                return redirect('doctor_view_other_patients', doctorID=doctorID)
            elif latest_request.status == 'REJECTED':
                latest_request.response_date = latest_request.retrieved_access_date = timezone.now()
                latest_request.save()

        # Create new request
        DoctorEditRequest.objects.create(
            requesting_doctor=doctor,
            patient=patient,
            reason=reason,
            request_date=timezone.now()
        )

        print(f"Edit access request created for doctor: {doctor.user.name}, Patient: {patient.user.name}")
        messages.success(request, 'Edit access request sent successfully.')
        return redirect('doctor_view_other_patients', doctorID=doctorID)

    return HttpResponseBadRequest("Invalid request method")

@login_required
@is_doctor
def doctor_secondary_management(request, doctorID):
    doctor = get_object_or_404(Doctor, user__userID=doctorID)
    patients = doctor.doctor_patients.all()
    edit_requests = DoctorEditRequest.objects.filter(patient__primary_doctor=doctor, status='PENDING')
    own_requests = DoctorEditRequest.objects.filter(requesting_doctor=doctor).exclude(status='PENDING')
    secondary_patients = Patient.objects.filter(secondary_doctors=doctor)

    print(f"Doctor: {doctor.user.name}, Pending edit requests: {edit_requests.count()}, Own requests: {own_requests.count()}, Secondary patients: {secondary_patients.count()}")

    return render(request, 'doctor/doctor_secondary_management.html', {
        'doctor': doctor,
        'patients': patients,
        'edit_requests': edit_requests,
        'own_requests': own_requests,
        'secondary_patients': secondary_patients,
        'doctorID': doctorID  # Add doctorID to the context
    })

@login_required
@is_doctor
def approve_edit_request(request, doctorID, requestID):
    edit_request = get_object_or_404(DoctorEditRequest, requestID=requestID, patient__primary_doctor__user__userID=doctorID)
    if request.method == "POST":
        edit_request.status = 'APPROVED'
        edit_request.response_date = timezone.now()
        edit_request.save()
        edit_request.patient.secondary_doctors.add(edit_request.requesting_doctor)
        messages.success(request, 'Edit request approved successfully.')
    return redirect('doctor_secondary_management', doctorID=doctorID)

@login_required
@is_doctor
def reject_edit_request(request, doctorID, requestID):
    edit_request = get_object_or_404(DoctorEditRequest, requestID=requestID, patient__primary_doctor__user__userID=doctorID)
    if request.method == "POST":
        edit_request.status = 'REJECTED'
        edit_request.response_date = timezone.now()
        edit_request.save()
        messages.success(request, 'Edit request rejected successfully.')
    return redirect('doctor_secondary_management', doctorID=doctorID)

@login_required
@is_doctor
def remove_secondary_doctor(request, doctorID, patientID, secondaryDoctorID):
    doctor = get_object_or_404(Doctor, user__userID=doctorID)
    patient = get_object_or_404(Patient, user__userID=patientID)
    secondary_doctor = get_object_or_404(Doctor, user__userID=secondaryDoctorID)

    # Ensure the requesting doctor is the primary doctor of the patient
    if patient.primary_doctor != doctor:
        messages.error(request, 'You do not have permission to remove secondary doctors from this patient.')
        return redirect('doctor_secondary_management', doctorID=doctorID)

    # Check if the secondary doctor is actually assigned to the patient
    if secondary_doctor in patient.secondary_doctors.all():
        patient.secondary_doctors.remove(secondary_doctor)

        # Update the removal timestamp in DoctorEditRequest if it exists
        edit_request = DoctorEditRequest.objects.filter(requesting_doctor=secondary_doctor, patient=patient, status='APPROVED').first()
        if edit_request:
            edit_request.retrieved_access_date = now()
            edit_request.save()

        messages.success(request, f'Successfully removed {secondary_doctor.user.name} as a secondary doctor for {patient.user.name}.')
    else:
        messages.error(request, 'The selected doctor is not a secondary doctor for this patient.')

    return redirect('doctor_secondary_management', doctorID=doctorID)

# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////

@login_required
def patient_dashboard(request, doctorID, patientID):
    doctor = get_object_or_404(Doctor, user__userID=doctorID)
    patient = get_object_or_404(Patient, user__userID=patientID)

    # Ensure only doctors can access
    if request.user.user_type != 'DOCTOR':
        messages.error(request, 'Access denied.')
        return redirect('home')  # Or another appropriate redirect

    # All doctors can view
    visits = Visit.objects.filter(
        patient=patient,
        visit_date__gte=date.today(),
        status__in=['Pending', 'Rescheduled']
    ).order_by('visit_date')

    context = {
        "doctor": doctor,
        "patient": patient,
        "visits": visits,
        "can_edit": patient.can_edit(doctor) #Use the can_edit method from the model.
    }
    return render(request, "doctor/patient/patient_dashboard.html", context)

@login_required
def patient_edit_profile(request, patientID):
    patient = get_object_or_404(Patient, user__userID=patientID)

    if request.method == "POST":
        patient.user.name = request.POST.get('name')
        patient.user.email = request.POST.get('email')
        patient.user.phone_number = request.POST.get('phone_number')
        patient.illness_name = request.POST.get('illness_name')
        patient.illness_description = request.POST.get('illness_description')

        if 'profile_photo' in request.FILES:
            patient.user.profile_photo = request.FILES['profile_photo']

        if request.POST.get('password'):
            patient.user.set_password(request.POST.get('password'))

        patient.user.save()
        patient.save()

        messages.success(request, 'Profile updated successfully!')
        return redirect('patient_dashboard', doctorID=patient.primary_doctor.user.userID, patientID=patient.user.userID)

    return render(request, 'doctor/patient/patient_edit_profile.html', {'patient': patient})

@login_required
def doctor_patient_all_visits(request, doctorID, patientID):
    doctor = get_object_or_404(Doctor, user__userID=doctorID)
    patient = get_object_or_404(Patient, user__userID=patientID)

    # Ensure only doctors can access
    if request.user.user_type != 'DOCTOR':
        messages.error(request, 'Access denied.')
        return redirect('home')  # Or another appropriate redirect

    visits = Visit.objects.filter(
        patient=patient
    ).order_by('-visit_date')

    # Add numpy file retrieval logic
    for visit in visits:
        if visit.file_path:
            try:
                visit.numpy_file_url = default_storage.url(visit.file_path) # add this.
            except ValueError:
                visit.numpy_file_url = None #if the file does not exist.

    context = {
        "doctor": doctor,
        "patient": patient,
        "visits": visits,
        "can_edit": patient.can_edit(doctor) #Use the can_edit method from the model.
    }
    return render(request, "doctor/patient/doctor_patient_all_visits.html", context)


@login_required
def update_visit_status(request, visitID):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            visit = get_object_or_404(Visit, visitID=visitID)
            new_status = request.POST.get('status')
            
            # Verify the status is valid
            valid_statuses = [choice[0] for choice in Visit._meta.get_field('status').choices]
            if new_status in valid_statuses:
                visit.status = new_status
                visit.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Status updated successfully',
                    'new_status': new_status
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid status value'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
            
    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    }, status=400)



# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////

import json
def demographics(request):
    hospitals = Hospital.objects.all()
    selected_hospital_id = request.GET.get('hospital_id')
    selected_doctor_id = request.GET.get('doctor_id')
    show_secondary = request.GET.get('show_secondary') == 'true'

    selected_hospital = None
    doctors = None
    primary_patients = None
    secondary_patients = None
    selected_doctor = None
    gender_distribution = {}
    patient_gender_distribution = {}

    if selected_hospital_id:
        selected_hospital = get_object_or_404(Hospital, user__userID=selected_hospital_id)
        doctors = Doctor.objects.filter(hospital=selected_hospital)
        
        for doctor in doctors:
            primary_count = Patient.objects.filter(primary_doctor=doctor).count()
            secondary_count = Patient.objects.filter(secondary_doctors=doctor).count()
            doctor.primary_count = primary_count
            doctor.secondary_count = secondary_count

        # Calculate gender distribution
        for gender, _ in CustomUser._meta.get_field('gender').choices:
            gender_distribution[gender] = doctors.filter(user__gender=gender).count()

        # Calculate patient gender distribution for the selected hospital or doctor
        if selected_doctor_id:
            selected_doctor = get_object_or_404(Doctor, user__userID=selected_doctor_id)
            if request.session.get('last_selected_doctor_id') == selected_doctor_id:
                selected_doctor = None
                request.session['last_selected_doctor_id'] = None
            else:
                request.session['last_selected_doctor_id'] = selected_doctor_id
            primary_patients = Patient.objects.filter(primary_doctor=selected_doctor)
            secondary_patients = Patient.objects.filter(secondary_doctors=selected_doctor)
            if show_secondary:
                patients = Patient.objects.filter(Q(primary_doctor=selected_doctor) | Q(secondary_doctors=selected_doctor))
            else:
                patients = Patient.objects.filter(primary_doctor=selected_doctor)

            for gender, _ in CustomUser._meta.get_field('gender').choices:
                if patients:
                    patient_gender_distribution[gender] = patients.filter(user__gender=gender).count()
                else:
                    patient_gender_distribution[gender] = 0
        else:
            request.session['last_selected_doctor_id'] = None
            patients_in_hospital = Patient.objects.filter(primary_doctor__hospital=selected_hospital)
            patients = patients_in_hospital

            for gender, _ in CustomUser._meta.get_field('gender').choices:
                if patients:
                    patient_gender_distribution[gender] = patients.filter(user__gender=gender).count()
                else:
                    patient_gender_distribution[gender] = 0

    context = {
        'hospitals': hospitals,
        'selected_hospital': selected_hospital,
        'doctors': doctors,
        'selected_doctor': selected_doctor,
        'primary_patients': primary_patients,
        'secondary_patients': secondary_patients,
        'gender_distribution_json': json.dumps(gender_distribution),
        'patient_gender_distribution_json': json.dumps(patient_gender_distribution),
        'show_secondary': show_secondary,
    }
    request.session['selected_hospital_id'] = selected_hospital_id
    return render(request, 'others/demographics.html', context)

@login_required
def doctor_patient_view_numpy_data(request, doctorID, patientID, visitID):
    visit = get_object_or_404(Visit, visitID=visitID)
    numbers = None
    error = None

    if not visit.file_path:
        error = "No numpy file uploaded for this visit."
    else:
        try:
            file_path = visit.file_path.path
            with open(file_path, 'rb') as f:
                data = numpy.load(f)
                # Convert numpy array to string for display
                numbers = str(data)
        except Exception as e:
            error = f"Could not read numpy file: {e}"

    context = {
        "visit": visit,
        "numbers": numbers,
        "error": error,
        "patient": visit.patient,
        "doctor": visit.doctor,
    }
    return render(request, "doctor/patient/doctor_patient_view_numpy_data.html", context)

