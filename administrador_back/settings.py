from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-&0l=el^o0pf10q%)a3zd9hxs-66!&fwv!cxcq)i+u09gc1a3^9'

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'backend',
    'tempro',
    'django_extensions',
    'rest_framework',
    'knox',
    'django_filters',
    'rest_framework.authtoken',
    'dj_rest_auth',
    'corsheaders',
    'simple_history',
    'django_tables2',
    'django_rest_passwordreset',]


REST_AUTH_SERIALIZERS = {
    'PASSWORD_RESET_SERIALIZER': 
        'backend.serializers.PasswordResetSerializer',}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' 

# These are the default values if none are set
from datetime import timedelta
from rest_framework.settings import api_settings

REST_KNOX = {
  'SECURE_HASH_ALGORITHM': 'cryptography.hazmat.primitives.hashes.SHA512',
  'AUTH_TOKEN_CHARACTER_LENGTH': 64,
  'TOKEN_TTL': timedelta(hours=2),
  'USER_SERIALIZER': 'knox.serializers.UserSerializer',
  'TOKEN_LIMIT_PER_USER': None,
  'AUTO_REFRESH': False,
  'EXPIRY_DATETIME_FORMAT': api_settings.DATETIME_FORMAT,}

REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': (
            # 'rest_framework.authentication.TokenAuthentication',
            # 'rest_framework.authentication.SessionAuthentication',
            'knox.auth.TokenAuthentication'
        ),
    'DATETIME_FORMAT': "%d/%m/%Y %H:%M:%S",
    'DATE_INPUT_FORMATS': ["%d-%m-%Y",'%Y-%m-%d'],
    'DATE_FORMAT':["%d-%m-%Y",'%Y-%m-%d'],

    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend']}

GRAPH_MODELS = {
  'all_applications': True,
  'group_models': True,}

FORMAT_MODULE_PATH = [
    'administrador_back.formats',
    'backend.formats',]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

DATE_INPUT_FORMATS = ('%d-%m-%Y','%Y-%m-%d')
DATE_FORMAT = ('%d-%m-%Y','%Y-%m-%d')
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
RESET_PASSWORD_ROUTE = 'http://localhost:8080/reset-password/'
ROOT_URLCONF = 'administrador_back.urls'

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

WSGI_APPLICATION = 'administrador_back.wsgi.application'

DATABASES = {
    #'default': {
    #    'ENGINE': 'django.db.backends.sqlite3',
    #    'NAME': BASE_DIR / 'db.sqlite3',
     'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
         'NAME': 'badministrador',
         'USER': 'uadministrador',
         'PASSWORD': 'padministrador',
         'HOST': '192.168.0.150',
         'PORT': '5432',
    # 'default': {
    #    'ENGINE': 'django.db.backends.postgresql_psycopg2',
    #    'NAME': 'medicallv1',
    #    'USER': 'gf',
    #    'PASSWORD': 'uPKsp22tBeBC506WRBv21d7kniWiELwg',
    #    'HOST': '157.230.2.213',
    #    'PORT': '5432',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },]

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Caracas'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static_administrador/'
STATIC_ROOT = 'static/'
#MEDIA_URL = 'static/media_administrador/'
#MEDIA_ROOT = BASE_DIR / 'static/media/'
MEDIA_URL = '/media_administrador/'
MEDIA_ROOT = '/django/productivo/administrador/media_root/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 587
