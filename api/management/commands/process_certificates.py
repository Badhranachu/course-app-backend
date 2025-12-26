# api/management/commands/process_certificates.py
from django.core.management.base import BaseCommand
from api.models import PreCertificate
from api.utils import delayed_transfer_and_email


class Command(BaseCommand):
    help = "Process pending certificates"

    def handle(self, *args, **kwargs):
        for precert in PreCertificate.objects.all():
            delayed_transfer_and_email(precert.id)

        self.stdout.write("Certificate check completed")