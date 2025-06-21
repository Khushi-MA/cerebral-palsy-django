from django.urls import path
from . import views

urlpatterns = [
     path('', views.common_login, name='common_login'),
     path('login/', views.common_login, name='common_login'),
     
     # Admin routes
     path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
     path('admin_edit_profile/', views.admin_edit_profile, name='admin_edit_profile'),

     # Hospital routes
     path('admin_register_hospital/', views.admin_register_hospital, name='admin_register_hospital'),
     path('hospital/<int:hospitalID>/dashboard/', views.hospital_dashboard, name='hospital_dashboard'),
     path('hospital/<int:hospitalID>/hospital_register_doctor/', views.hospital_register_doctor, name='hospital_register_doctor'),
     path('hospital_edit_profile/', views.hospital_edit_profile, name='hospital_edit_profile'),

     # Doctor routes
     path('doctor/<int:doctorID>/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
     path('doctor/<int:doctorID>/doctor_register_patient/', views.doctor_register_patient, name='doctor_register_patient'),
     path('doctor/<int:doctorID>/edit_profile/', views.doctor_edit_profile, name='doctor_edit_profile'),
     path('patient/<int:patientID>/edit/', views.patient_edit_profile, name='patient_edit_profile'),
     path('doctor/<int:doctorID>/other-patients/', views.doctor_view_other_patients, name='doctor_view_other_patients'), 
     path('doctor/<int:doctorID>/request-edit-access/<int:patientID>/', views.doctor_request_edit_access, name='doctor_request_edit_access'),
     path('doctor/<int:doctorID>/secondary-management/', views.doctor_secondary_management, name='doctor_secondary_management'),
     path('doctor/<int:doctorID>/approve-edit-request/<int:requestID>/', views.approve_edit_request, name='approve_edit_request'),
     path('doctor/<int:doctorID>/reject-edit-request/<int:requestID>/', views.reject_edit_request, name='reject_edit_request'),
     path('doctor/<int:doctorID>/patient/<int:patientID>/remove_secondary/<int:secondaryDoctorID>/', views.remove_secondary_doctor, name='remove_secondary_doctor'),

     # patient routes
     path('doctor/<int:doctorID>/patient/<int:patientID>/dashboard', views.patient_dashboard, name='patient_dashboard'),
     path('doctor/<int:doctorID>/patient/<int:patientID>/make_visit/', views.doctor_patient_make_visit, name='doctor_patient_make_visit'),
     path('doctor/<int:doctorID>/patient/<int:patientID>/all-visits/', views.doctor_patient_all_visits, name='doctor_patient_all_visits'),
     path('users/update-visit-status/<int:visitID>/', views.update_visit_status, name='update_visit_status'),
     path('doctor/<int:doctorID>/patient/<int:patientID>/doctor_patient_view_numpy_data/<int:visitID>/', views.doctor_patient_view_numpy_data, name='doctor_patient_view_numpy_data'),


     path('others/demographics', views.demographics, name='demographics'),
]