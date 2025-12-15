# backend/bekola/settings.py

from pathlib import Path
from datetime import timedelta
import os


import ssl
ssl._create_default_https_context = ssl._create_unverified_context


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-bekola-dev-key-change-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    # Your app
    'api',
]

# -----------------------------
#  MIDDLEWARE (VERY IMPORTANT)
# -----------------------------
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # MUST BE FIRST
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bekola.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'bekola.wsgi.application'

# -----------------------------
#  DATABASE
# -----------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# -----------------------------
#  PASSWORD VALIDATORS
# -----------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -----------------------------
#  CUSTOM USER MODEL
# -----------------------------
AUTH_USER_MODEL = 'api.User'

# -----------------------------
#  EMAIL LOGIN BACKEND
# -----------------------------
AUTHENTICATION_BACKENDS = [
    'api.backends.EmailBackend',  # Use email to authenticate
    'django.contrib.auth.backends.ModelBackend',
]

# -----------------------------
#  REST FRAMEWORK
# -----------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'api.authentication.UserTokenAuthentication'
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}


VIDEO_PROGRESS_TEST_MODE = True   # 🔧 set False in production

# -----------------------------
#  JWT SETTINGS
# -----------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# -----------------------------
#  CORS CONFIG (THE FIX)
# -----------------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['Content-Range', 'Accept-Ranges']


CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
    "accept",
    "origin",
    "user-agent",
    "x-csrftoken",
    "accept-encoding",
    "content-type",
    "range"
]

CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]

# -----------------------------
#  RAZORPAY (OPTIONAL)
# -----------------------------
RAZORPAY_KEY_ID = "rzp_test_RrATUAvT1J4mmj"
RAZORPAY_KEY_SECRET = "CCLrGpxQ5GIy8agGbfd0Yae5"


STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

CORS_ALLOW_ALL_ORIGINS = True
AUTH_USER_MODEL = "api.CustomUser"



EMAIL_BACKEND = "api.custom_email_backend.UnverifiedSSLBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "dairiesofbadhran@gmail.com"
EMAIL_HOST_PASSWORD = "dnjijwwhtxukdecz"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
