from pathlib import Path
from cryptography.hazmat.primitives import serialization

inp = Path("vapid_private.pem").read_bytes()

key = serialization.load_pem_private_key(inp, password=None)

out = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,  # -> EC PRIVATE KEY
    encryption_algorithm=serialization.NoEncryption(),
)

Path("vapid_private_ec.pem").write_bytes(out)
print("OK -> vapid_private_ec.pem generado")