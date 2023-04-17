from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


back_to_mainmenu_markup = InlineKeyboardMarkup()
back_to_mainmenu_markup.add(InlineKeyboardButton("В главное меню", callback_data="mainmenu"))