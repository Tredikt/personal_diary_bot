import os
from dotenv import load_dotenv

# load_dotenv(".env.data")


bot_token = ""  # BOT TOKEN from @BotFather
admins = ""  # Admins ids. Write your ID here and your will get access to admin_panel


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