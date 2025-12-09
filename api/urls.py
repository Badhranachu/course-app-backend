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



]

