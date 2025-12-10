import smtplib
from django.core.mail.backends.smtp import EmailBackend
import ssl

class UnverifiedSSLBackend(EmailBackend):
    def open(self):
        if self.connection:
            return False

        try:
            # override SSL context ONLY for email
            self.connection = smtplib.SMTP(self.host, self.port)
            self.connection.ehlo()
            self.connection.starttls(context=ssl._create_unverified_context())
            self.connection.ehlo()

            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise
            return False
