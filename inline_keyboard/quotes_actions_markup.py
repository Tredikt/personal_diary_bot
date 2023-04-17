from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

quotes_actions_markup = InlineKeyboardMarkup()

quotes_actions_markup.add(InlineKeyboardButton("Список цитат", callback_data="quoteslist"))
quotes_actions_markup.add(InlineKeyboardButton("Добавить цитату", callback_data="addquote"))
quotes_actions_markup.add(InlineKeyboardButton("Удалить цитату", callback_data="deletequote"))
quotes_actions_markup.add(InlineKeyboardButton("В главное меню", callback_data="mainmenu"))
