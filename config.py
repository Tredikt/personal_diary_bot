import os
from dotenv import load_dotenv

load_dotenv(".env.example")


bot_token = os.getenv("BOT_TOKEN")

admins = os.getenv("admins_ids")

if admins:
    admins = list(map(int, admins.split()))


categories_lists = {
    "goalslist": "goals",
    "quoteslist": "quotes"
}

categories = [
    "mainmenu",
    "goals",
    "quotes"
]

additions = [
    "addgoal",
    "addquote"
]

deletings_dict = {
    "deletegoal": ("goals", "цель"),
    "deletequote": ("quotes", "цитату")
}