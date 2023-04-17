import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.inline_keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import Message, CallbackQuery, User, ContentType

from inline_keyboard.back_to_goals_markup import back_to_goals_markup
from inline_keyboard.back_to_quotes_markup import back_to_quotes_markup
from inline_keyboard.back_to_mainmenu_markup import back_to_mainmenu_markup

from inline_keyboard.admin_actions_markup import admin_actions_markup
from inline_keyboard.quotes_actions_markup import quotes_actions_markup
from inline_keyboard.goals_actions_markup import goals_actions_markup, goals_mark_markup
from inline_keyboard.main_menu_markup import main_menu_markup

from xlsxwriter import Workbook
from datetime import datetime, date
from sqlite3 import connect
from typing import Dict

from config import bot_token, admins
from config import categories_lists, categories, additions, deletings_dict


class PersonalDiaryBot:
    def __init__(self, token: str) -> None:
        self.bot = Bot(token)
        self.dp = Dispatcher(self.bot)

        self.add_goal_flag = False
        self.add_quote_flag = False

        self.write_day_flag = False
        self.remind_day_flag = False

        self.del_message = False
        self.send_message_flag = False

        if admins:
            self.admins = admins
        else:
            self.admins = []

        self.users_list = self.write_or_get_user(action="get")

        logging.basicConfig(level=logging.INFO)

    async def start_handler(self, message: Message):
        """Хэндлер, отслеживающий команду '/start'"""
        chat = tg_id = message.from_user.id

        if (tg_id not in self.users_list) or (await self.is_admin(tg_id) is False):
            self.write_or_get_user(user=message.from_user, action="write")

        await message.reply(
            "Привет, я бот - личный дневник"
        )
        await self.bot.send_message(
            chat,
            "Главное меню:",
            reply_markup=main_menu_markup
        )


    async def text_handler(self, message: types.Message):
        """Хэндлер, реагирующий на текст"""
        chat = message.chat.id
        text = message.text
        tg_id = message.from_user.id

        if self.write_day_flag:
            await self.add(base="days", message=message)

        elif self.remind_day_flag:
            day, month = list(map(int, text.split(".")))
            year = 2023
            try:
                made_date = str(date(year, month, day))
                await self.select_all_bases(user_id=tg_id, day=made_date)
                await self.bot.delete_message(chat, message.message_id - 1)
                await self.bot.delete_message(chat, message.message_id)
            except SyntaxError:
                await self.bot.send_message(chat, "Некорректный ввод, попробуйте снова")

        elif self.add_goal_flag:
            await self.add(base="goals", message=message)

        elif self.add_quote_flag:
            await self.add(base="quotes", message=message)

        elif self.send_message_flag:
            for chat_id in self.users_list:
                await self.bot.send_message(chat_id, text)
                self.send_message_flag = False
                await self.bot.send_message(chat, "Выберите опцию", reply_markup=admin_actions_markup)

    async def callback_handler(self, call: CallbackQuery):
        """Хэндлер, отвечающий за поведение Inline кнопок"""
        chat = call.message.chat.id
        req = call.data.split("_")
        callback = req[0]
        user_id = call["from"]["id"]
        mess_id = call.message.message_id

        goals_dict = await self.dicts(user_id=user_id, base="goals")
        quotes_dict = await self.dicts(user_id=user_id, base="quotes")

        if callback in categories:
            if self.del_message:
                await self.bot.delete_message(chat, call.message.message_id - 1)
            self.del_message = False
            await self.turn_off_flags()
            await self.bot.delete_message(chat, call.message.message_id)
            await self.keyboards(call.message, keyboard=f"{callback}")

        elif callback == "write-day":
            await self.bot.delete_message(chat, call.message.message_id)
            await self.bot.send_message(
                chat,
                "Напиши то, что хотел бы запомнить",
                reply_markup=back_to_mainmenu_markup
            )
            self.write_day_flag = True

        elif callback == "remind-day":
            await self.bot.delete_message(chat, call.message.message_id)
            await self.bot.send_message(
                chat,
                "Напиши день, который хотите вспомнить. "
                "\n\nПримеры: "
                "\n1) 24.09"
                "\n2) 01.03",
                reply_markup=back_to_mainmenu_markup
            )
            self.remind_day_flag = True


        elif callback in categories_lists:
            await self.elements_list(message=call.message, elem=categories_lists[callback])

        elif callback == "goalmark":
            mark_goals = InlineKeyboardMarkup()
            if goals_dict:
                for key, value in goals_dict.items():
                    mark_goals.add(InlineKeyboardButton(f"{key}", callback_data=f"{value}"))

                mark_goals.add(InlineKeyboardButton("Назад", callback_data="goals"))

            await self.bot.delete_message(chat, call.message.message_id)
            await self.bot.send_message(chat, "Выберите выполненную цель", reply_markup=mark_goals)

        elif callback in additions:
            if callback == "addgoal":
                self.add_goal_flag = True

                await self.bot.delete_message(chat, call.message.message_id)
                await self.bot.send_message(chat, "Введите цель:", reply_markup=back_to_goals_markup)

            elif callback == "addquote":
                self.add_quote_flag = True

                await self.bot.delete_message(chat, call.message.message_id)
                await self.bot.send_message(chat, "Введите цитату:", reply_markup=back_to_quotes_markup)

        elif callback in deletings_dict:
            del_goals = InlineKeyboardMarkup()

            if callback == "deletequote":
                if quotes_dict:
                    for i_elem in quotes_dict.keys():
                        del_goals.add(InlineKeyboardButton(i_elem, callback_data=i_elem))
                else:
                    await self.bot.delete_message(chat, mess_id)
                    await self.bot.send_message(
                        chat, "Список цитат пуст, удалять нечего",
                        reply_markup=back_to_quotes_markup
                    )

            elif callback == "deletegoal":
                if goals_dict:
                    for i_elem in goals_dict.keys():
                        del_goals.add(InlineKeyboardButton(f"{i_elem}", callback_data=f"{i_elem}"))
                else:
                    await self.bot.delete_message(chat, mess_id)
                    await self.bot.send_message(
                        chat, "Список целей пуст, удалять нечего",
                        reply_markup=back_to_goals_markup
                    )

            del_goals.add(InlineKeyboardButton("Назад", callback_data=deletings_dict[req[0]][0]))
            await self.bot.delete_message(chat, call.message.message_id)
            await self.bot.send_message(
                chat,
                f"Выберите {deletings_dict[callback][1]}, которую хотите удалить",
                reply_markup=del_goals
            )

        elif callback in quotes_dict:
            """Код используется для удаления цитат"""
            sql_connection = connect("databases/personal_diary.db")
            try:
                cursor = sql_connection.cursor()
                sql_query = f"""DELETE from quotes WHERE tg_id={user_id} AND quote="{quotes_dict[callback]}";"""
                cursor.execute(sql_query)
                sql_connection.commit()

            finally:
                if sql_connection:
                    sql_connection.close()

            quotes = await self.select_one_base(user_id, base="quotes")
            quotes_dict = dict()
            del_goals = InlineKeyboardMarkup()

            for elem in quotes:
                quotes_dict[elem[1]] = elem[1]

            for i_elem in quotes_dict.keys():
                del_goals.add(InlineKeyboardButton(i_elem, callback_data=i_elem))
            del_goals.add(InlineKeyboardButton("Назад", callback_data="quotes"))

            if len(quotes) != 0:
                await self.bot.answer_callback_query(call.id, show_alert=True, text="Цитата успешно удалена\U0001F5D1")
                await self.bot.delete_message(chat, call.message.message_id)
                await self.bot.send_message(chat, "Выберите цитату, которую хотите удалить", reply_markup=del_goals)

            else:
                await self.bot.answer_callback_query(call.id, show_alert=True, text="Вы очистили весь список цитат")
                await self.bot.delete_message(chat, call.message.message_id)
                await self.keyboards(call.message, keyboard="quotes")

        elif callback in goals_dict:
            """Код используется для удаления целей"""
            sql_connection = connect("databases/personal_diary.db")
            try:
                cursor = sql_connection.cursor()
                sql_query = f"""DELETE from goals WHERE goal="{req[0]}" AND tg_id={user_id};"""
                cursor.execute(sql_query)
                sql_connection.commit()

            finally:
                if sql_connection:
                    sql_connection.close()

                mark_goals = InlineKeyboardMarkup()
                goals_dict = await self.dicts(user_id=user_id, base="goals")

                if (goals_dict is not None) and (len(goals_dict) > 0):
                    for key in goals_dict:
                        mark_goals.add(InlineKeyboardButton(f"{key}", callback_data=f"{key}"))

                    mark_goals.add(InlineKeyboardButton("Назад", callback_data="goals"))

                    await self.bot.answer_callback_query(
                        call.id, show_alert=True, text="Цель успешно удалена\U0001F5D1"
                    )
                    await self.bot.delete_message(chat, call.message.message_id)
                    await self.bot.send_message(chat, "Выберите цель, которую хотите удалить", reply_markup=mark_goals)

                else:
                    await self.bot.answer_callback_query(call.id, show_alert=True, text="Вы очистили весь список целей")
                    await self.bot.delete_message(chat, call.message.message_id)
                    await self.keyboards(call.message, keyboard="goals")

        elif callback in goals_dict.values():
            """
            Код ниже удаляет выполненные цели из запланированных целей и переносит их в выполненные
            """
            data = await self.select_one_base(user_id=user_id, base="goals")
            for elem in data:
                tg_id, goal, activation_date = elem
                break
            sql_connection = connect("databases/personal_diary.db")

            try:
                date_of_completion = str(date(datetime.now().year, datetime.now().month, datetime.now().day))
                cursor = sql_connection.cursor()
                sql_delete_query = f"""DELETE from goals WHERE tg_id={tg_id} AND goal="{goal}";"""
                sql_insert_query = f"""INSERT INTO reached_goals 
                                        (goal, date_of_completion, tg_id)
                                        VALUES
                                        ("{goal}", "{date_of_completion}", {tg_id});"""
                cursor.execute(sql_delete_query)
                sql_connection.commit()
                cursor.execute(sql_insert_query)
                sql_connection.commit()
            finally:
                if sql_connection:
                    sql_connection.close()

            mark_goals = InlineKeyboardMarkup()
            goals_dict = await self.dicts(user_id=user_id, base="goals")

            if len(goals_dict) > 0:
                for key, value in goals_dict.items():
                    mark_goals.add(InlineKeyboardButton(f"{key}", callback_data=f"{value}"))

                mark_goals.add(InlineKeyboardButton("Назад", callback_data="goals"))

                await self.bot.answer_callback_query(call.id, show_alert=True, text="Цель выполнена, поздравляю!")
                await self.bot.delete_message(chat, call.message.message_id)
                await self.bot.send_message(chat, "Выберите выполненную цель", reply_markup=mark_goals)

            else:
                await self.bot.answer_callback_query(
                    call.id, show_alert=True, text="Поздравляем! Вы выполнили все цели"
                )
                await self.bot.delete_message(chat, call.message.message_id)
                await self.keyboards(call.message, keyboard="goals")

        elif callback == "unload-users":
            """
            Код ниже выгружает информацию о пользователях из базы данных и отправляет файлом с расширением .xlsx админу 
            """
            wb = Workbook("users-list.xlsx")
            worksheet = wb.add_worksheet()

            # сюда нужно вставить путь до файла с расширением xlsx
            # если файл с таким названием существует, то он удаляется, чтобы не было конфликтов
            if os.path.isfile("users-list.xlsx"):
                os.remove("users-list.xlsx")

            database = connect("databases/personal_diary.db")
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
                os.remove("users-list.xlsx")

            await self.bot.send_message(chat, "Выберите опцию", reply_markup=admin_actions_markup)

        elif callback == "message-to-users":
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
            await self.bot.send_message(chat, "Выберите опцию", reply_markup=admin_actions_markup)

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
        database = connect("databases/personal_diary.db")
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

    async def elements_list(self, message: Message, elem: str) -> None:
        """
        Функция формирует списки целей/цитат пользователя, взаимодействует с такими кнопками, как:
        'Список цитат' и 'Список целей'
        """
        chat = user_id = message.chat.id
        await self.bot.delete_message(chat, message_id=message.message_id)

        if elem == "goals":
            data = await self.select_one_base(user_id=user_id, base="goals")

            if data:
                row = f"Твой список целей \U0001F4CB:\n"
                for num, elem in enumerate(data):
                    row += f"{num + 1}. {elem[1]}\n"

                await self.bot.send_message(chat, row, reply_markup=goals_mark_markup)

            else:
                await self.bot.send_message(
                    chat,
                    "Ты пока не записал ни одной цели",
                    reply_markup=back_to_goals_markup
                )

        elif elem == "quotes":
            data = await self.select_one_base(user_id=user_id, base="quotes")

            if data:
                row = f"Твой список цитат \U0001F4CB:\n"
                for num, i_elem in enumerate(data):
                    row += f"{num + 1}) {i_elem[1]}.\n"

                await self.bot.send_message(chat, row, reply_markup=back_to_quotes_markup)

            else:
                await self.bot.send_message(
                    chat,
                    "Ты пока не записал ни одной цитаты",
                    reply_markup=back_to_quotes_markup
                )

    async def dicts(self, user_id: int, base: str) -> Dict:
        """
        Функция достаёт информацию из баз данных с помощью 'select_one_base' и структурирует её в списки, это
        необходимо для того, чтобы пользователь мог удалять записи и цитаты
        """
        if base.lower() == "goals":
            goals = await self.select_one_base(user_id=user_id, base=base)
            goals_dict = dict()

            for num, elem in enumerate(goals):
                goals_dict[elem[1]] = f"goal{num + 1}"

            return goals_dict

        elif base.lower() == "quotes":
            quotes = await self.select_one_base(user_id=user_id, base="quotes")
            quotes_dict = dict()

            for elem in quotes:
                quotes_dict[elem[1]] = elem[1]

            return quotes_dict


    async def add(self, base: str, message: Message) -> None:
        """
        Функция записывает данные в выбранную базу данных
        """

        sql_connection = connect("databases/personal_diary.db")
        chat = message.chat.id
        text = message.text
        tg_id = message.from_user.id

        try:
            activation_date = str(date(datetime.now().year, datetime.now().month, datetime.now().day))
            cursor = sql_connection.cursor()

            sql_day_query = f"""
                                INSERT INTO days
                                (tg_id, activation_date, writing)
                                VALUES
                                ({tg_id}, "{activation_date}", "{text}");
                            """

            sql_goal_query = f"""
                                INSERT INTO goals
                                (goal, activation_date, tg_id)
                                VALUES 
                                ("{text}", "{activation_date}", {tg_id});
                            """

            sql_quote_query = f"""
                                INSERT INTO quotes
                                (quote, activation_date, tg_id)
                                VALUES 
                                ("{text}", "{activation_date}", {tg_id});
                            """

            if base.lower() == "goals":
                cursor.execute(sql_goal_query)

            elif base.lower() == "quotes":
                cursor.execute(sql_quote_query)

            elif base.lower() == "days":
                cursor.execute(sql_day_query)

            sql_connection.commit()

        finally:
            if sql_connection:
                sql_connection.close()

            if base.lower() == "goals":
                await self.bot.send_message(chat, "Цель успешно добавлена!\U0001F3AF")
                await self.bot.delete_message(chat, message_id=message.message_id - 1)

                self.del_message = True
                self.add_goal_flag = False

                await self.elements_list(message, elem="goals")

            elif base.lower() == "quotes":
                await self.bot.send_message(chat, "Цитата успешно добавлена!\U0001F4DA")
                await self.bot.delete_message(chat, message_id=message.message_id - 1)

                self.del_message = True
                self.add_quote_flag = False

                await self.elements_list(message, elem="quotes")

            elif base.lower() == "days":
                await self.bot.send_message(
                    chat,
                    "Запись успешно добавлена!\U0001F3AF",
                    reply_markup=back_to_mainmenu_markup
                )
                await self.bot.delete_message(chat, message_id=message.message_id - 1)
                self.del_message = True
                self.write_day_flag = False

    async def select_all_bases(self, user_id: int, day: str) -> None:
        """
        Данная функция достаёт информацию о действиях пользователя за определённый день
        """
        chat = user_id
        connection = connect("databases/personal_diary.db")

        try:
            cursor = connection.cursor()
            goals_query = f"""SELECT goal FROM goals WHERE tg_id={user_id} AND activation_date="{day}";"""
            reached_query = f"""SELECT goal FROM reached_goals WHERE tg_id={user_id} AND date_of_completion="{day}";"""
            quotes_query = f"""SELECT quote FROM quotes WHERE tg_id={user_id} AND activation_date="{day}";"""
            days_query = f"""SELECT writing FROM days WHERE tg_id={user_id} AND activation_date="{day}";"""

            goals_data = cursor.execute(goals_query)
            connection.commit()
            reached_goals_data = cursor.execute(reached_query)
            connection.commit()
            quotes_data = cursor.execute(quotes_query)
            connection.commit()
            days_data = cursor.execute(days_query)
            connection.commit()


            goals_data = goals_data.fetchall()
            reached_goals_data = reached_goals_data.fetchall()
            quotes_data = quotes_data.fetchall()
            days_data = days_data.fetchall()

            row = "В этот день ты:"
            if days_data:
                row += "\nДобавил записи:\n"
                for num, elem in enumerate(days_data):
                    row += f"{num + 1}) {elem[0]}\n"

            if reached_goals_data:
                row += "\nДостиг целей:\n"
                for num, elem in enumerate(reached_goals_data):
                    row += f"{num + 1}) {elem[0]}\n"

            if goals_data:
                row += "\nДобавил цели:\n"
                for num, elem in enumerate(goals_data):
                    row += f"{num + 1}) {elem[0]}\n"

            if quotes_data:
                row += "\nДобавил цитаты:\n"
                for num, elem in enumerate(quotes_data):
                    row += f"{num + 1}) {elem[0]}\n"

            if len(row) > 15:
                await self.bot.send_message(
                    chat, row, reply_markup=back_to_mainmenu_markup
                )

            else:
                await self.bot.send_message(
                    chat,
                    "В этот день ты ничего не делал",
                    reply_markup=back_to_mainmenu_markup
                )

        finally:
            if connection:
                connection.close()

    @staticmethod
    async def select_one_base(user_id: int, base: str):
        """Функция достаёт информацию о пользователе и выбранной базы данных"""
        sql_connection = connect("databases/personal_diary.db")

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

    async def turn_off_flags(self) -> None:
        """
        Функция переводит все флаги в False, чтобы избежать лишний записей
        """
        self.write_day_flag = False
        self.remind_day_flag = False
        self.send_message_flag = False
        self.add_goal_flag = False
        self.add_quote_flag = False

    async def keyboards(self, message, keyboard):
        """Клавиатуры"""
        chat = message.chat.id

        if keyboard.lower() == "mainmenu":
            await self.bot.send_message(
                chat,
                "Главное меню:",
                reply_markup=main_menu_markup
            )

        elif keyboard.lower() == "goals":
            await self.bot.send_message(
                chat, "Здесь ты можешь управлять своими целями \U0001F4DD",
                reply_markup=goals_actions_markup
            )

        elif keyboard.lower() == "quotes":
            await self.bot.send_message(
                chat,
                "Здесь ты можешь управлять своими цитатами \U0001F4D7",
                reply_markup=quotes_actions_markup
            )

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
