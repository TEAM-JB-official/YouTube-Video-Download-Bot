from cryptography.fernet import Fernet

key = Fernet.generate_key().decode()
print(f"COOKIE_ENCRYPTION_KEY={key}")
print("\nAdd this to your .env file")
