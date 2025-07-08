import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = int(os.getenv("MONGODB_PORT", "27017"))
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "0"))

# Добавьте другие параметры по мере необходимости 