"""Pruebas de regresión para la pareja VAPID y la renovación en navegador."""
from django.conf import settings
from django.test import SimpleTestCase
from cryptography.hazmat.primitives.serialization import load_der_private_key, Encoding, PublicFormat
import base64


class VapidConfigurationTests(SimpleTestCase):
    def test_public_key_corresponds_to_private_key_when_configured(self):
        if not settings.VAPID_PRIVATE_KEY:
            self.assertFalse(settings.VAPID_PUBLIC_KEY)
            return
        private = load_der_private_key(base64.urlsafe_b64decode(settings.VAPID_PRIVATE_KEY + "=" * (-len(settings.VAPID_PRIVATE_KEY) % 4)), password=None)
        expected = base64.urlsafe_b64encode(
            private.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        ).decode().rstrip('=')
        self.assertEqual(settings.VAPID_PUBLIC_KEY, expected)
