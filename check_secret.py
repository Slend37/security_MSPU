import os
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("APP_SECRET"):
    print('ERROR: Secret key not found')
    exit(1)

print(f"System started. Secret hash: {os.getenv("APP_SECRET")[0:3]}")
