from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
import os
from django.utils.timezone import now

class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email must be set')
        email = self.normalize_email(email)
        extra_fields.setdefault('username', email)  # Setting username to email (Django requires username)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'ADMIN')
        extra_fields.setdefault('name', email)
        return self._create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('HOSPITAL', 'Hospital'),
        ('DOCTOR', 'Doctor'),
        ('PATIENT', 'Patient'),
    )
    
    userID = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, null=True)
    profile_photo = models.ImageField(upload_to='images/profile_photos/', null=True, blank=True, default='images/default.png')
    date_of_registration = models.DateField(auto_now_add=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], null=True, blank=True)
    is_hidden = models.BooleanField(default=False)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = CustomUserManager()

class Hospital(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, primary_key=True, limit_choices_to={'user_type': 'HOSPITAL'})
    address = models.TextField()
    number_of_doctors = models.IntegerField(default=0)
    number_of_patients = models.IntegerField(default=0)
    added_by_admin = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='admin_hospitals', limit_choices_to={'user_type': 'ADMIN'})

class Doctor(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, primary_key=True, limit_choices_to={'user_type': 'DOCTOR'})
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='hospital_doctors')
    highest_qualification = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)
    experience = models.IntegerField(help_text="Years of experience")
    number_of_patients = models.IntegerField(default=0)

class Patient(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, primary_key=True, limit_choices_to={'user_type': 'PATIENT'})
    primary_doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='doctor_patients')
    secondary_doctors = models.ManyToManyField(Doctor, blank=True, related_name='secondary_patients')
    illness_name = models.CharField(max_length=100)
    illness_description = models.TextField(null=True, blank=True)
    date_of_first_visit = models.DateField(auto_now_add=True)
    additional_remarks = models.TextField(null=True, blank=True)
    number_of_visits = models.IntegerField(default=0)

    def is_primary_doctor(self, doctor):
        return self.primary_doctor == doctor

    def is_secondary_doctor(self, doctor):
        return doctor in self.secondary_doctors.all()

    def can_edit(self, doctor):
        return self.is_primary_doctor(doctor) or self.is_secondary_doctor(doctor)  # Both primary and secondary doctors can edit

class Visit(models.Model):
    visitID = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_visits')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='doctor_visits')
    visit_date = models.DateField()
    visit_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=[
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Rescheduled', 'Rescheduled'),
        ('Other', 'Other')
    ], default="Completed")
    remarks = models.TextField(null=True, blank=True)
    file_path = models.FileField(upload_to='media/visits/', blank=True, null=True) #######################################################################################

    class Meta:
        ordering = ['-visitID']

class DoctorEditRequest(models.Model):
    requestID = models.AutoField(primary_key=True)
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ]
    requesting_doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='sent_requests')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='edit_requests')
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reason = models.TextField()
    response_date = models.DateTimeField(null=True, blank=True)
    response_note = models.TextField(null=True, blank=True)
    retrieved_access_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-request_date']