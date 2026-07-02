import smtplib
import ssl
from django.core.mail.backends.smtp import EmailBackend


class CertifiEmailBackend(EmailBackend):
    def open(self):
        if self.connection:
            return False
        try:
            ctx = ssl.create_default_context()
            self.connection = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            self.connection.ehlo()
            if self.use_tls:
                self.connection.starttls(context=ctx)
                self.connection.ehlo()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except Exception:
            if not self.fail_silently:
                raise