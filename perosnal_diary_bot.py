import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import Message, CallbackQuery, User, ContentType

from inline_keyboard.admin_markup import admin_markup


from xlsxwriter import Workbook
from datetime import datetime, date
from sqlite3 import connect
import os

from config import bot_token, admins


class PersonalDiaryBot:
    def __init__(self, token: str) -> None:
        self.bot = Bot(token)
        self.dp = Dispatcher(self.bot)

        self.last_request = None
        self.add_target = False
        self.del_message = False
        self.del_target = False
        self.list_targets = False
        self.list_quotes = False
        self.add_quote = False
        self.del_message = False
        self.send_message_flag = False

        if admins:
            self.admins = admins
        else:
            self.admins = []

        self.users_list = self.write_or_get_user(action="get")

        logging.basicConfig(level=logging.INFO)

    async def start_handler(self, message: Message):
        tg_id = message.from_user.id

        if (tg_id not in self.users_list) or (await self.is_admin(tg_id) is False):
            self.write_or_get_user(user=message.from_user, action="write")

        await message.reply(
            "Привет, я бот - личный дневник"
        )
        await self.main_menu(message=message)


    async def text_handler(self, message: types.Message):
        chat = message.chat.id
        text = message.text

        if self.add_target:
            await self.add(base="purposes", message=message)

        elif self.add_quote:
            await self.add(base="quotes", message=message)

        elif self.send_message_flag:
            for chat_id in self.users_list:
                await self.bot.send_message(chat_id, message.text)
                self.send_message_flag = False
                await self.bot.send_message(chat, "Выберите опцию", reply_markup=admin_markup)

    async def callback_handler(self, call):
        categories = ["goals", "quotes"]
        chat = call.message.chat.id
        req = call.data.split("_")
        user_id = call["from"]["id"]
        mess_id = call.message.message_id
        goals, undone_goals_dict = await self.goals_list(user_id)
        done_goals, done_goals_dict = await self.goals_list(user_id, done=True)

        # для возврата назад
        goals_markup = InlineKeyboardMarkup()
        goals_markup.add(InlineKeyboardButton("Назад", callback_data="goals"))

        self.quotes_markup = InlineKeyboardMarkup()
        self.quotes_markup.add(InlineKeyboardButton("Назад", callback_data="quotes"))

        # для выполнения целей
        goals_mark = InlineKeyboardMarkup()

        goals_mark.add(InlineKeyboardButton("Отметить выполненные", callback_data="goalMark"))
        goals_mark.add(InlineKeyboardButton("Назад", callback_data="goals"))

        # для выполненных целей
        mark_goals = InlineKeyboardMarkup()
        if undone_goals_dict:
            for key, value in undone_goals_dict.items():
                mark_goals.add(InlineKeyboardButton(f"{value}", callback_data=f"{value}"))

            mark_goals.add(InlineKeyboardButton("Назад", callback_data="goals"))

        quotes = await self.selection(user_id, base="quotes")
        quotes_dict = dict()

        for elem in quotes:
            quotes_dict[elem[0]] = elem[0]

        if req[0] == "mainmenu":
            await self.main_menu(message=call.message, prev=True)

        elif req[0] in categories:
            if self.del_message:
                await self.bot.delete_message(chat, call.message.message_id - 2)
                await self.bot.delete_message(chat, call.message.message_id - 1)
                self.del_message = False
            self.last_request = None
            await self.bot.delete_message(chat, call.message.message_id)
            await self.keyboards(call.message, keyboard=f"{req[0]}")

        elif req[0] == "targetslist" or req[0] == "quoteslist":
            lists = {"targetslist": "goals", "quoteslist": "quotes"}
            await self.elements_list(message=call.message, elem=lists[req[0]])

        elif req[0] == "goalMark":
            if self.del_message:
                await self.bot.delete_message(chat, call.message.message_id - 1)
                self.del_message = False
            await self.bot.delete_message(chat, call.message.message_id)
            await self.bot.send_message(chat, "Выберите выполненную цель", reply_markup=mark_goals)

        elif req[0] == "addtarget" or req[0] == "addquote":
            if req[0] == "addtarget":
                self.add_target = True

                await self.bot.delete_message(chat, call.message.message_id)
                await self.bot.send_message(chat, "Введите цель:", reply_markup=goals_markup)

            elif req[0] == "addquote":
                self.add_quote = True

                await self.bot.delete_message(chat, call.message.message_id)
                await self.bot.send_message(chat, "Введите цитату:", reply_markup=self.quotes_markup)

        elif req[0] == "deletetarget" or req[0] == "deletequote":
            del_dict = {"deletetarget": ("goals", "цель"), "deletequote": ("quotes", "цитату")}
            del_goals = InlineKeyboardMarkup()

            if req[0] == "deletequote":
                if quotes_dict:
                    for i_elem in quotes_dict.keys():
                        del_goals.add(InlineKeyboardButton(i_elem, callback_data=i_elem))
                else:
                    quote_back = InlineKeyboardMarkup()
                    quote_back.add(InlineKeyboardButton("Назад", callback_data="quotes"))
                    await self.bot.delete_message(chat, mess_id)
                    await self.bot.send_message(chat, "Список цитат пуст, удалять нечего", reply_markup=quote_back)

            elif self.last_request == "delete":
                if done_goals_dict:
                    for key, value in done_goals_dict.items():
                        del_goals.add(InlineKeyboardButton(f"{value}", callback_data=f"{key}"))
                else:
                    await self.bot.delete_message(chat, mess_id)
                    await self.bot.send_message(chat, "Список целей пуст, удалять нечего", reply_markup=goals_markup)

            else:
                if undone_goals_dict:
                    for key, value in undone_goals_dict.items():
                        del_goals.add(InlineKeyboardButton(f"{value}", callback_data=f"{key}"))
                else:
                    await self.bot.delete_message(chat, mess_id)
                    await self.bot.send_message(chat, "Список целей пуст, удалять нечего", reply_markup=goals_markup)

            del_goals.add(InlineKeyboardButton("Назад", callback_data=del_dict[req[0]][0]))
            await self.bot.delete_message(chat, call.message.message_id)
            await self.bot.send_message(chat, f"Выберите {del_dict[req[0]][1]}, которую хотите удалить",
                                   reply_markup=del_goals)

        elif req[0] == "deleteallgoals":
            sql_connection = connect("databases/personal_diary.db")
            try:
                cursor = sql_connection.cursor()
                sql_query = f"""DELETE from purposes WHERE Выполнение=1 AND tg_id={user_id};"""
                cursor.execute(sql_query)
                sql_connection.commit()
            finally:
                if sql_connection:
                    sql_connection.close()

                await self.bot.answer_callback_query(call.id, show_alert=True, text="Все записи удалены")
                await self.bot.delete_message(chat, mess_id)
                await self.keyboards(call.message, keyboard="goals")

        elif req[0] == "targertsdone":
            data = await self.selection(user_id=user_id, base="purposes")

            if len(data) != 0:
                goals = []
                for elem in data:
                    if elem[1] == 1:
                        goals.append(elem[0])

                row = f"Выполненные цели \N{White Heavy Check Mark}:\n"
                for num, elem in enumerate(goals):
                    row += f"{num + 1}. {elem}\n"

                self.last_request = "delete"
                goals_markup.add(InlineKeyboardButton("Удалить выборочно", callback_data="deletetarget"))
                goals_markup.add(InlineKeyboardButton("Удалить все", callback_data="deleteallgoals"))
                await self.bot.delete_message(chat, mess_id)
                await self.bot.send_message(chat, row, reply_markup=goals_markup)

            else:
                await self.bot.delete_message(chat, mess_id)
                await self.bot.send_message(chat, "Ты пока не выполнил ни одной цели", reply_markup=goals_markup)

        elif req[0] in quotes_dict:
            sql_connection = connect("databases/personal_diary.db")
            try:
                cursor = sql_connection.cursor()
                sql_query = f"""DELETE from quotes WHERE Цитата="{quotes_dict[req[0]]}" AND tg_id={user_id};"""
                cursor.execute(sql_query)
                sql_connection.commit()

            finally:
                if sql_connection:
                    sql_connection.close()

            quotes = await self.selection(user_id, base="quotes")
            quotes_dict = dict()
            del_goals = InlineKeyboardMarkup()

            for elem in quotes:
                quotes_dict[elem[0]] = elem[0]

            for i_elem in quotes_dict.keys():
                del_goals.add(InlineKeyboardButton(i_elem, callback_data=i_elem))
                del_goals.add(InlineKeyboardButton("Назад", callback_data="quotes"))

            if len(quotes) != 0:
                await self.bot.answer_callback_query(call.id, show_alert=True, text="Цитата успешно удалена\U0001F5D1")
                await self.bot.delete_message(chat, call.message.message_id)
                await self.bot.send_message(chat, "Выберите цель, которую хотите удалить", reply_markup=del_goals)

            else:
                await self.bot.answer_callback_query(call.id, show_alert=True, text="Вы очистили весь список целей")
                await self.bot.delete_message(chat, call.message.message_id)
                await self.keyboards(call.message, keyboard="quotes")

        elif req[0] in undone_goals_dict.keys() or req[0] in done_goals_dict.keys():
            sql_connection = connect("databases/personal_diary.db")
            try:
                cursor = sql_connection.cursor()
                if self.last_request == "delete":
                    sql_query_done = f"""DELETE from purposes WHERE Цель="{done_goals_dict[req[0]]}" AND tg_id={user_id};"""
                    cursor.execute(sql_query_done)
                else:
                    sql_query = f"""DELETE from purposes WHERE Цель="{undone_goals_dict[req[0]]}" AND tg_id={user_id};"""
                    cursor.execute(sql_query)
                sql_connection.commit()

            finally:
                if sql_connection:
                    sql_connection.close()

                mark_goals = InlineKeyboardMarkup()
                goals, done_goals_dict = await self.goals_list(user_id, done=True)
                undone_goals, undone_goals_dict = await self.goals_list(user_id)

                if (done_goals_dict is not None) and (len(done_goals_dict) > 0) and self.last_request:
                    for key, value in done_goals_dict.items():
                        mark_goals.add(InlineKeyboardButton(f"{value}", callback_data=f"{key}"))

                    mark_goals.add(InlineKeyboardButton("Назад", callback_data="goals"))

                    await self.bot.answer_callback_query(call.id, show_alert=True, text="Цель успешно удалена\U0001F5D1")
                    await self.bot.delete_message(chat, call.message.message_id)
                    await self.bot.send_message(chat, "Выберите цель, которую хотите удалить", reply_markup=mark_goals)

                elif (undone_goals_dict is not None) and (len(undone_goals_dict) > 0) and (self.last_request is None):
                    for key, value in undone_goals_dict.items():
                        mark_goals.add(InlineKeyboardButton(f"{value}", callback_data=f"{key}"))

                    mark_goals.add(InlineKeyboardButton("Назад", callback_data="goals"))

                    await self.bot.answer_callback_query(call.id, show_alert=True, text="Цель успешно удалена\U0001F5D1")
                    await self.bot.delete_message(chat, call.message.message_id)
                    await self.bot.send_message(chat, "Выберите цель, которую хотите удалить", reply_markup=mark_goals)

                else:
                    self.last_request = None
                    await self.bot.answer_callback_query(call.id, show_alert=True, text="Вы очистили весь список целей")
                    await self.bot.delete_message(chat, call.message.message_id)
                    await self.keyboards(call.message, keyboard="goals")

        elif req[0] in undone_goals_dict.values():
            self.del_message = False
            data = await self.selection(user_id=user_id, base="purposes")
            for elem in data:
                if elem[0] == req[0]:
                    goal, done, date_created, date_done, tg_id = elem
                    break
            sql_connection = connect("databases/personal_diary.db")

            try:
                cursor = sql_connection.cursor()
                sql_delete_query = f"""DELETE from purposes WHERE tg_id={tg_id} AND Цель="{goal}";"""
                sql_insert_query = f"""INSERT INTO purposes 
                                        (Цель, Выполнение, Дата_создания, Дата_выполнения, tg_id)
                                        VALUES
                                        ("{goal}", 1, "{date_created}", "{date_done}", {tg_id});"""
                cursor.execute(sql_delete_query)
                sql_connection.commit()
                cursor.execute(sql_insert_query)
                sql_connection.commit()
            finally:
                if sql_connection:
                    sql_connection.close()

            mark_goals = InlineKeyboardMarkup()
            goals, goals_dict = await self.goals_list(user_id)

            if len(goals_dict) > 0:
                for key, value in goals_dict.items():
                    mark_goals.add(InlineKeyboardButton(f"{value}", callback_data=f"{value}"))

                mark_goals.add(InlineKeyboardButton("Назад", callback_data="goals"))

                await self.bot.answer_callback_query(call.id, show_alert=True, text="Цель успешно перенесена в выполненные")
                await self.bot.delete_message(chat, call.message.message_id)
                await self.bot.send_message(chat, "Выберите выполненную цель", reply_markup=mark_goals)

            else:
                await self.bot.answer_callback_query(call.id, show_alert=True, text="Поздравляем! Вы выполнили все цели")
                await self.bot.delete_message(chat, call.message.message_id)
                await self.keyboards(call.message, keyboard="goals")

        elif req[0] == "unload-users":
            """
            Код ниже выгружает информацию о пользователях из базы данных и отправляет файлом с расширением .xlsx админу 
            """
            wb = Workbook("users-list.xlsx")
            worksheet = wb.add_worksheet()

            # сюда нужно вставить путь до файла с расширением xlsx
            # если файл с таким названием существует, то он удаляется, чтобы не было конфликтов
            if os.path.isfile("C://PycharmProjects/personal_diary//users-list.xlsx"):
                os.remove("users-list.xlsx")

            database = connect("personal_diary.db")
            cursor = database.cursor()

            query = f"""SELECT * FROM users"""

            data = cursor.execute(query)
            database.commit()
            data = data.fetchall()

            row = 0

            worksheet.write(row, 0, "tg_id")
            worksheet.write(row, 1, "username")
            worksheet.write(row, 2, "first_name")
            worksheet.write(row, 3, "last_name")
            worksheet.write(row, 4, "activation_date")

            for i_elem in data:
                tg_id, username, first_name, last_name, activation_date = i_elem
                row += 1
                worksheet.write(row, 0, tg_id)
                worksheet.write(row, 1, username)
                worksheet.write(row, 2, first_name)
                worksheet.write(row, 3, last_name)
                worksheet.write(row, 4, activation_date)

            wb.close()

            await self.bot.delete_message(chat, mess_id)
            with open("users-list.xlsx", "rb") as document:
                await self.bot.send_message(chat, "Файл с данными о всех пользователях:")
                await self.bot.send_document(chat, document)

            await self.bot.send_message(chat, "Выберите опцию", reply_markup=admin_markup)

        elif req[0] == "message-to-users":
            self.send_message_flag = True
            await self.bot.send_message(chat, "Введите сообщение, которое хотите отправить пользователям:")

    async def admin_handler(self, message):
        """
        Данная функция открывает админ-панель
        """
        tg_id = message.from_user.id
        chat = message.chat.id

        accept = await self.is_admin(tg_id=tg_id)

        if accept:
            await self.bot.send_message(chat, "Выберите опцию", reply_markup=admin_markup)

    async def is_admin(self, tg_id) -> bool:
        """
        Данная функия возвращает True, если пользователь админ и False иначе
        """
        if tg_id in self.admins:
            return True
        return False

    @staticmethod
    def write_or_get_user(action: str, user: User = None) -> list or None:
        """
        Данная функция позвонляет записать информацию о пользователе в базу данных, при вводе им команды /start.
        Так же функция возвращает список id пользователей, если в аргумент action передать 'get'
        """
        database = connect("personal_diary.db")
        cursor = database.cursor()

        if action.lower() == "write":
            tg_id = user.id
            first_name = user.first_name
            last_name = user.last_name
            username = user.username
            activation_date = str(date(datetime.now().year, datetime.now().month, datetime.now().day))

            query = f"""INSERT INTO users
                            (tg_id, username, first_name, last_name, activation_date)
                            VALUES
                            ({tg_id}, "{username}", "{first_name}", "{last_name}", "{activation_date}"); 
                        """

            cursor.execute(query)
            database.commit()

        elif action.lower() == "get":
            query = """SELECT tg_id FROM users"""
            data = cursor.execute(query)
            database.commit()

            data = data.fetchall()

            users_list = list()
            for user in data:
                users_list.append(user[0])

            return users_list

    async def elements_list(self, message, elem):
        chat = user_id = message.chat.id

        if elem == "goals":
            goals, undone_goals_dict = await self.goals_list(user_id)
            # для выполнения целей
            goals_mark = InlineKeyboardMarkup()

            goals_mark.add(InlineKeyboardButton("Отметить выполненные", callback_data="goalMark"))
            goals_mark.add(InlineKeyboardButton("Назад", callback_data="goals"))

            # для возврата назад
            goals_markup = InlineKeyboardMarkup()
            goals_markup.add(InlineKeyboardButton("Назад", callback_data="goals"))

            if goals is None:
                await self.bot.delete_message(chat, message.message_id)
                await self.bot.send_message(chat, "Список целей пуст", reply_markup=goals_markup)

            else:
                row = f"Твой список целей \U0001F4CB:\n"
                for num, elem in enumerate(goals):
                    row += f"{num + 1}. {elem}\n"

                self.list_targets = True
                await self.bot.delete_message(chat, message.message_id)
                await self.bot.send_message(chat, row, reply_markup=goals_mark)

        elif elem == "quotes":
            quoteslist_markup = InlineKeyboardMarkup()
            quoteslist_markup.add(InlineKeyboardButton("Назад", callback_data="quotes"))

            data = await self.selection(user_id=user_id, base="quotes")
            await self.bot.delete_message(chat, message.message_id)

            if data:
                row = str()
                for num, i_elem in enumerate(data):
                    row += f"{num + 1}) {i_elem[0]}.\n"

                await self.bot.send_message(chat, row, reply_markup=quoteslist_markup)

            else:
                await self.bot.send_message(
                    chat,
                    "Ты пока не записал ни одной цитаты",
                    reply_markup=self.quotes_markup
                )

    @staticmethod
    async def selection(user_id: int, base: str):
        sql_connection = connect("personal_diary.db")

        try:
            cursor = sql_connection.cursor()
            sqlite_query = f"""SELECT * FROM {base} WHERE tg_id={user_id};"""
            sql = cursor.execute(sqlite_query)
            sql_connection.commit()

            data = sql.fetchall()
            return data

        finally:
            if sql_connection:
                sql_connection.close()

    async def main_menu(self, message, prev=None):
        if prev:
            await self.bot.delete_message(message.chat.id, message.message_id)

        mainMenu = InlineKeyboardMarkup()

        mainMenu.add(InlineKeyboardButton("Цели", callback_data="goals"))
        mainMenu.add(InlineKeyboardButton("Цитаты", callback_data="quotes"))
        await self.bot.send_message(message.chat.id, "Главное меню:", reply_markup=mainMenu)

    async def goals_list(self, user_id, done=None):
        data = await self.selection(user_id=user_id, base="purposes")
        if data:
            goals = []
            goals_dict = {}

            if done:
                for elem in data:
                    if elem[1] == 1:
                        goals.append(elem[0])

            else:
                for elem in data:
                    if elem[1] != 1:
                        goals.append(elem[0])

            for num, elem in enumerate(goals):
                goals_dict[f"goal{num + 1}"] = elem

            return goals, goals_dict
        return {}, {}

    async def delete_targets(self, call: CallbackQuery):
        chat = call.message.chat.id
        user_id = call["from"]["id"]
        goals, goals_dict = await self.goals_list(user_id)
        mess_id = call.message.message_id

        # для возврата назад
        goals_markup = InlineKeyboardMarkup()
        goals_markup.add(InlineKeyboardButton("Назад", callback_data="goals"))

        if goals:
            del_goals = InlineKeyboardMarkup()
            for key, value in goals_dict.items():
                del_goals.add(InlineKeyboardButton(f"{value}", callback_data=f"{key}"))

            del_goals.add(InlineKeyboardButton("Назад", callback_data="goals"))
            await self.bot.delete_message(chat, call.message.message_id)
            await self.bot.send_message(chat, "Выберите цель, которую хотите удалить", reply_markup=del_goals)

        else:
            await self.bot.delete_message(chat, mess_id)
            await self.bot.send_message(chat, "Список целей пуст, удалять нечего", reply_markup=goals_markup)

    async def add(self, base, message):
        sql_connection = connect("databases/personal_diary.db")
        chat = message.chat.id
        text = message.text

        try:
            activation_date = str(date(datetime.now().year, datetime.now().month, datetime.now().day))
            cursor = sql_connection.cursor()

            sql_goal_query = f"""INSERT INTO {base}
                                   (Цель, Выполнение, Дата_создания, Дата_выполнения, tg_id)
                                   VALUES 
                                   ("{text}", 0, "{activation_date}", NULL, {message.from_user.id});"""

            sql_quote_query = f"""INSERT INTO {base}
                                           (Цитата, Дата_создания, tg_id)
                                           VALUES 
                                           ("{text}", "{activation_date}", {message.from_user.id});"""

            if base.lower() == "purposes":
                cursor.execute(sql_goal_query)

            elif base.lower() == "quotes":
                cursor.execute(sql_quote_query)

            sql_connection.commit()

        finally:
            if sql_connection:
                sql_connection.close()

            if base.lower() == "purposes":
                await self.bot.delete_message(chat, message.message_id - 1)
                await self.bot.send_message(chat, "Цель успешно добавлена!\U0001F3AF")
                self.add_target = False

                user_id = message.from_user.id
                data = await self.selection(user_id=user_id, base="purposes")
                goals = []
                for elem in data:
                    if elem[1] != 1:
                        goals.append(elem[0])

                row = f"Твой список целей \U0001F4CB:\n"
                for num, elem in enumerate(goals):
                    row += f"{num + 1}. {elem}\n"

                goals_markup = InlineKeyboardMarkup()

                goals_markup.add(InlineKeyboardButton("Отметить выполненные", callback_data="goalMark"))
                goals_markup.add(InlineKeyboardButton("Назад", callback_data="goals"))
                self.del_message = True
                await self.bot.send_message(chat, row, reply_markup=goals_markup)

            elif base.lower() == "quotes":
                await self.bot.delete_message(chat, message.message_id - 1)
                await self.bot.send_message(chat, "Цитата успешно добавлена!\U0001F4DA")
                self.add_quote = False

                user_id = message.from_user.id

                self.del_message = True

                quoteslist_markup = InlineKeyboardMarkup()
                quoteslist_markup.add(InlineKeyboardButton("Назад", callback_data="quotes"))

                await self.elements_list(message, elem="quotes")

    async def keyboards(self, message, keyboard):
        chat = message.chat.id
        markup = InlineKeyboardMarkup()

        if keyboard.lower() == "goals":
            item_1 = InlineKeyboardButton("Список целей", callback_data="targetslist")
            item_2 = InlineKeyboardButton("Добавить цель", callback_data="addtarget")
            item_3 = InlineKeyboardButton("Удалить цель", callback_data="deletetarget")
            item_4 = InlineKeyboardButton("Выполненные цели", callback_data="targertsdone")

            markup.add(item_1)
            markup.add(item_2)
            markup.add(item_3)
            markup.add(item_4)
            markup.add(InlineKeyboardButton("В главное меню", callback_data="mainmenu"))

            await self.bot.send_message(chat, "Здесь ты можешь управлять своими целями \U0001F4DD", reply_markup=markup)

        elif keyboard.lower() == "quotes":
            markup.add(InlineKeyboardButton("Список цитат", callback_data="quoteslist"))
            markup.add(InlineKeyboardButton("Добавить цитату", callback_data="addquote"))
            markup.add(InlineKeyboardButton("Удалить цитату", callback_data="deletequote"))

            markup.add(InlineKeyboardButton("В главное меню", callback_data="mainmenu"))

            await self.bot.send_message(chat, "Здесь ты можешь управлять своими цитатами \U0001F4D7", reply_markup=markup)

    def add_handlers(self) -> None:
        """
        Функция регистрирует все хэндлеры
        """
        self.dp.register_message_handler(self.start_handler, commands=["start"])
        self.dp.register_message_handler(self.admin_handler, commands=["admin"])
        self.dp.register_message_handler(self.text_handler, content_types=ContentType.TEXT)
        self.dp.register_callback_query_handler(self.callback_handler, lambda message: True)


    def run(self):
        """
        Фукнция запуска бота
        """
        self.add_handlers()
        executor.start_polling(self.dp, skip_updates=True)


if __name__ == "__main__":
    bot = PersonalDiaryBot(token=bot_token)
    bot.run()

