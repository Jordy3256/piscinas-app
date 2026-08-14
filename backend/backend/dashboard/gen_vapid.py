from pywebpush import WebPush

vapid_keys = WebPush.generate_vapid_keys()

print("\n====== VAPID KEYS ======\n")
print("PUBLIC_KEY:")
print(vapid_keys["publicKey"])
print("\nPRIVATE_KEY:")
print(vapid_keys["privateKey"])
print("\n========================\n")
