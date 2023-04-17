from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

goals_actions_markup = InlineKeyboardMarkup()
goals_actions_markup.add(InlineKeyboardButton("Список целей", callback_data="goalslist"))
goals_actions_markup.add(InlineKeyboardButton("Добавить цель", callback_data="addgoal"))
goals_actions_markup.add(InlineKeyboardButton("Удалить цель", callback_data="deletegoal"))
goals_actions_markup.add(InlineKeyboardButton("В главное меню", callback_data="mainmenu"))


goals_mark_markup = InlineKeyboardMarkup()
goals_mark_markup.add(InlineKeyboardButton("Отметить выполненные", callback_data="goalmark"))
goals_mark_markup.add(InlineKeyboardButton("Назад", callback_data="goals"))
