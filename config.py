import os
from dotenv import load_dotenv

load_dotenv("C://PycharmProjects//personal_diary//.env.data")

bot_token = os.getenv("BOT_TOKEN")

admins = os.getenv("admins_ids")

if admins:
    admins = list(map(int, admins.split()))