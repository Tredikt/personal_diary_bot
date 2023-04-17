from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu_markup = InlineKeyboardMarkup()

main_menu_markup.add(InlineKeyboardButton("Цели", callback_data="goals"))
main_menu_markup.add(InlineKeyboardButton("Цитаты", callback_data="quotes"))
main_menu_markup.add(InlineKeyboardButton("Записать день", callback_data="write-day"))
main_menu_markup.add(InlineKeyboardButton("Вспомнить день", callback_data="remind-day"))