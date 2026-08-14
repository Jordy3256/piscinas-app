import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create or reset an admin user from env vars."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_ADMIN_USER")
        email = os.environ.get("DJANGO_ADMIN_EMAIL", "")
        password = os.environ.get("DJANGO_ADMIN_PASSWORD")

        if not username or not password:
            self.stdout.write("Missing DJANGO_ADMIN_USER or DJANGO_ADMIN_PASSWORD. Skipping.")
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})

        user.is_staff = True
        user.is_superuser = True
        if email:
            user.email = email
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(f"Created superuser: {username}")
        else:
            self.stdout.write(f"Reset password for superuser: {username}")
