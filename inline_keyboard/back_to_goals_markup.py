from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

back_to_goals_markup = InlineKeyboardMarkup()
back_to_goals_markup .add(InlineKeyboardButton("Назад", callback_data="goals"))