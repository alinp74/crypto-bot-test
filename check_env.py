import os
from dotenv import load_dotenv

load_dotenv()

print("API KEY =", os.getenv("API_KEY_MAINNET"))
print("API SECRET =", os.getenv("API_SECRET_MAINNET"))
