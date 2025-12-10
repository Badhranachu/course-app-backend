#backend/api/urls.py


from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Auth endpoints
    path('auth/signup/', views.signup, name='signup'),
    path('auth/login/', views.login, name='login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.get_user, name='get_user'),
    
    # Course endpoints
    path('courses/', views.CourseListCreateView.as_view(), name='course-list-create'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course-detail'),
    path('courses/<int:course_id>/videos/', views.course_videos, name='course-videos'),
    
    # Payment endpoints
    path('payment/create-order/', views.create_payment_order, name='create-order'),
    path('payment/verify/', views.verify_payment, name='verify-payment'),
    
    # Video streaming
    path('videos/<int:video_id>/stream/', views.stream_video, name='stream-video'),

    path("courses/<int:course_id>/modules/", views.course_modules),

    path("test/<int:test_id>/", views.get_test, name="get-test"),

    path("test/<int:test_id>/submit/", views.submit_test),

    path("courses/<int:course_id>/test-history/", views.course_test_history),



path("videos/<int:video_id>/attachment-preview/", views.attachment_preview),
path("videos/<int:video_id>/attachment-tree/", views.attachment_tree),
path("videos/<int:video_id>/attachment-content/<path:file_path>/", views.attachment_content),

path("certificate/generate/", views.generate_user_certificate),


path("certificate/github-link/", views.save_github_link),

path("certificate/github-link/<int:course_id>/", views.get_github_link),

path("certificate/send/<int:course_id>/", views.send_course_certificate, name="send-course-certificate"),
















]

