"""
WSGI config for bekola project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bekola.settings')

application = get_wsgi_application()

