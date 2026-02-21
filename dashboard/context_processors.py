# dashboard/context_processors.py
from django.conf import settings

def vapid_public_key(request):
    key = getattr(settings, "VAPID_PUBLIC_KEY", "") or ""
    key = key.replace("\n", "").replace("\r", "").strip()
    return {"VAPID_PUBLIC_KEY": key}