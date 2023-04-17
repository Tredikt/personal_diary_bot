from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

admin_actions_markup = InlineKeyboardMarkup()
admin_actions_markup.add(InlineKeyboardButton("Выгрузить пользователей", callback_data="unload-users"))
admin_actions_markup.add(InlineKeyboardButton("Отправить сообщение пользователем", callback_data="message-to-users"))
admin_actions_markup.add(InlineKeyboardButton("В главное меню", callback_data="mainmenu"))