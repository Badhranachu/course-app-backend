from django.urls import path
from api import views

urlpatterns = [

    # =========================
    # AUTH
    # =========================
    path("auth/send-otp/", views.SendEmailOTPAPIView.as_view()),
    path("auth/verify-otp/", views.VerifyEmailOTPAPIView.as_view()),
    path("auth/signup/", views.SignupAPIView.as_view(), name="signup"),
    path("auth/login/", views.LoginAPIView.as_view(), name="login"),
    # path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", views.GetUserAPIView.as_view(), name="get-user"),

    # =========================
    # COURSES
    # =========================
    path("courses/", views.CourseListCreateAPIView.as_view(), name="course-list"),
    path("courses/<int:pk>/", views.CourseDetailAPIView.as_view(), name="course-detail"),
    path("courses/<int:course_id>/modules/", views.CourseModulesAPIView.as_view()),
    path("courses/<int:course_id>/videos/", views.CourseVideosAPIView.as_view()),
    path(
    "courses/<int:course_id>/videos/<int:video_id>/",
    views.CourseVideosAPIView.as_view(),
    name="course-video-detail"
    ),





    # =========================
    # PAYMENT
    # =========================
    path("payment/create-order/", views.CreatePaymentOrderAPIView.as_view()),
    path("payment/verify/", views.VerifyPaymentAPIView.as_view()),

    # =========================
    # VIDEO
    # =========================
# path(
#     "courses/<int:course_id>/videos/<int:video_id>/stream/",
#     views.StreamVideoAPIView.as_view(),
#     name="video-stream",
# ),
    path(
    "courses/<int:course_id>/videos/<int:video_id>/duration/",
    views.UpdateVideoDurationAPIView.as_view(),
    name="video-duration"
),

    #update video progress and get video progress
path(
    "courses/<int:course_id>/videos/<int:video_id>/progress/",
    views.UpdateVideoProgressAPIView.as_view(),
    name="video-progress"
),

path(
    "courses/<int:course_id>/all-videos/progress/",
    views.CourseVideoAllProgressAPIView.as_view(),
    name="course-video-progress"
),



    # get module progres
    path(
    "courses/<int:course_id>/module-progress/",
    views.CourseModuleProgressAPIView.as_view(),
    name="course-module-status"
),




    # =========================
    # TESTS
    # =========================
# 1️⃣ List all tests for a course (enrolled students only)
    path(
        "courses/<int:course_id>/tests/",
        views.CourseTestsAPIView.as_view(),
        name="course-tests"
    ),
    path(
        "courses/<int:course_id>/tests/<int:test_id>/",
        views.CourseTestsAPIView.as_view(),
        name="course-test-detail"
    ),

    # 3️⃣ Submit test answers
    path(
    "courses/<int:course_id>/tests/<int:test_id>/submit/",
    views.SubmitTestAPIView.as_view(),
    name="test-submit"
    ),
    

    # 4️⃣ Test history (summary list for course)
path(
    "courses/<int:course_id>/tests/history/",
    views.TestHistoryAPIView.as_view(),
    name="test-history"
),

path(
    "courses/<int:course_id>/tests/history/<int:student_test_id>/",
    views.TestHistoryAPIView.as_view(),
    name="test-history-detail"
),


    # =========================
    # ATTACHMENTS
    # =========================
path(
    "courses/<int:course_id>/videos/<int:video_id>/attachment-preview/",
    views.AttachmentPreviewAPIView.as_view(),
    name="attachment-preview"
),

path(
    "courses/<int:course_id>/videos/<int:video_id>/attachment-tree/",
    views.AttachmentTreeAPIView.as_view(),
    name="attachment-tree"
),

path(
    "courses/<int:course_id>/videos/<int:video_id>/attachment-content/<path:file_path>/",
    views.AttachmentContentAPIView.as_view(),
    name="attachment-content"
),
    # =========================
    # CERTIFICATES
    # =========================
path(
    "certificate/github-link/<int:course_id>/",
    views.SaveGithubLinkAPIView.as_view(),
    name="certificate-github-link"
),
    # path("certificate/generate/", views.GenerateUserCertificateAPIView.as_view()),
    path("certificate/send/<int:course_id>/", views.SendCourseCertificateAPIView.as_view()),
    path("certificate/my/", views.ListUserCertificatesAPIView.as_view()),
    path(
    "my-certificate/download/<path:reference_number>/",
    views.MyCertificateDownloadAPIView.as_view(),
    name="my-certificate-download",
),
    path("certificate/github-link/<int:course_id>/", views.GetGithubLinkAPIView.as_view()),

    # =========================
    # MODULE / PROGRESS
    # =========================
    path("modules/<int:module_id>/complete-video/", views.CompleteVideoAPIView.as_view()),


    path(
        "certificate/check/",
        views.CertificateCheckAPIView.as_view(),
        name="certificate-check",
    ),
    path(
        "certificate/download/<path:reference_number>/",
        views.CertificateDownloadAPIView.as_view(),
        name="certificate-download",
    ),
    path("grow-with-us/", views.GrowWithUsView.as_view()),
    path("announcements/", views.AnnouncementListAPIView.as_view()),
    path("student/profile/", views.StudentProfileAPIView.as_view()),
    path(
    "student/enrollments/",
    views.StudentEnrollmentListAPIView.as_view(),
    
),
    path("support/create/", views.CreateSupportTicketAPIView.as_view()),
    path("support/my-tickets/", views.MySupportTicketsAPIView.as_view()),



    path("chat/", views.ChatWithAIView.as_view(), name="chat-with-ai"),
    # api/urls.py
    # path("me/", views.MeAPIView.as_view()),
    path("admin-videos/upload/", views.VideoUploadAPIView.as_view()),
    path("admin-courses/", views.CourseListAPIView.as_view()),





    
    path("admin-videos/presign/", views.R2PresignedUploadView.as_view()),
    path("admin-videos/create/", views.AdminVideoCreateView.as_view()),
    path("admin-videos/upload-zip/", views.AdminVideoUploadZipAPIView.as_view()),
    path("contactus/",views.ContactUsCreateAPIView.as_view()),

    path("forgot-password/", views.ForgotPasswordAPIView.as_view()),
    path("forgot-password/resend/", views.ResendForgotPasswordOTPAPIView.as_view()),
    path("forgot-password/verify/", views.VerifyForgotPasswordOTPAPIView.as_view()),


    #

#


]
