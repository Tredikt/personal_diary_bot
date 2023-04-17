from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


back_to_quotes_markup = InlineKeyboardMarkup()
back_to_quotes_markup.add(InlineKeyboardButton("Назад", callback_data="quotes"))