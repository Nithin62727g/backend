import os
from dotenv import load_dotenv
import smtplib
import traceback

load_dotenv(override=True)

host = os.getenv("SMTP_HOST", "smtp.gmail.com")
port = int(os.getenv("SMTP_PORT", 587))
user = os.getenv("SMTP_USER", "")
pwd = os.getenv("SMTP_PASSWORD", "")
use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

print(f"Testing SMTP login for {user} at {host}:{port} (TLS={use_tls})")
print(f"Password length: {len(pwd)}")

try:
    if use_tls:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.set_debuglevel(1)
            server.ehlo()
            server.starttls()
            server.login(user, pwd)
            print("Login SUCCESS!")
    else:
        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            server.set_debuglevel(1)
            server.login(user, pwd)
            print("Login SUCCESS!")
except Exception as e:
    print(f"Login FAILED: {type(e).__name__} - {e}")
    traceback.print_exc()
