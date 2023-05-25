from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

back_to_admin_actions_markup = InlineKeyboardMarkup()
back_to_admin_actions_markup.add(
    InlineKeyboardButton(text="Назад", callback_data="back-to-admin-actions")
)