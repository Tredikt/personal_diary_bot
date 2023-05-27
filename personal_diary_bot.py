"""
Файл с кодом бота.

Класс с различными функциями, позволяющими работать боту.
"""

import logging
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types.inline_keyboard import (
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from aiogram.types import Message, CallbackQuery, User, ContentType
from aiogram.types import BotCommand

from inline_keyboard.back_to_goals_markup import back_to_goals_markup
from inline_keyboard.back_to_quotes_markup import back_to_quotes_markup
from inline_keyboard.back_to_mainmenu_markup import back_to_mainmenu_markup
from inline_keyboard.back_to_admin_actions_markup import back_to_admin_actions_markup

from inline_keyboard.admin_actions_markup import admin_actions_markup
from inline_keyboard.quotes_actions_markup import quotes_actions_markup
from inline_keyboard.goals_actions_markup import (
    goals_actions_markup,
    goals_mark_markup
)
from inline_keyboard.main_menu_markup import main_menu_markup

from tables import (
    sql_query_reached_goals,
    sql_query_users,
    sql_query_days,
    sql_query_quotes,
    sql_query_goals
)

from xlsxwriter import Workbook
from datetime import datetime, date
from sqlite3 import connect
from sqlite3 import Cursor, Connection
from typing import Dict, List

from config import bot_token, admins
from config import categories_lists, categories, additions, deletings_dict


class PersonalDiaryBot:
    """
    Телеграм-бот Персональный дневник.

    Как обычный дневник, но с большим функционалом.
    """

    def __init__(self, token: str) -> None:
        """
        Функция __init__ определяет основные параметры для класса.

        Функция принимает токен бота в
        параметре token и на основе этого
        запускает его.
        """
        self.bot: Bot = Bot(token)
        self.dp: Dispatcher = Dispatcher(self.bot)

        self.add_goal_flag: bool = False
        self.add_quote_flag: bool = False

        self.write_day_flag: bool = False
        self.remind_day_flag: bool = False

        self.del_message: bool = False
        self.send_message_flag: bool = False

        self.commands: List = [
            BotCommand(command="/menu", description="Открыть меню")
        ]

        if admins:
            self.admins: List = list(map(int, admins.split()))
        else:
            self.admins: List = []

        self.users_list: List = self.write_or_get_user(action="get")

        logging.basicConfig(level=logging.INFO)

    async def start_handler(self, message: Message) -> None:
        """
        Команды /start и /menu.

        Хэндлер, отслеживающий команду '/start' и '/menu'
        и отправляющий приветствие с inline-menu
        """
        chat = tg_id = message.from_user.id

        if (tg_id not in self.users_list) or \
                (await self.is_admin(tg_id) is False):
            self.write_or_get_user(user=message.from_user, action="write")

        await message.reply(
            "Привет, я бот - личный дневник"
        )
        await self.bot.send_message(
            chat,
            "Главное меню:",
            reply_markup=main_menu_markup
        )

    async def text_handler(self, message: types.Message) -> None:
        """
        Хэндлер, реагирующий на текст.

        При нажатии определённых кнопок некоторые
        флаги из значение False переходят в True,
        после чего пользователь пишет сообщение,
        которое заносится в базу данных или
        отправляется всех пользователям, если
        админ делает рассылку.
        """
        chat: int = message.chat.id
        text: str = message.text
        tg_id: int = message.from_user.id

        if self.write_day_flag:
            await self.add(base="days", message=message)

        elif self.remind_day_flag:
            day, month, year = list(map(int, text.split(".")))

            try:
                made_date = str(date(year, month, day))
                await self.select_all_bases(user_id=tg_id, day=made_date)

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=message.message_id - 1
                )

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=message.message_id
                )
            except SyntaxError:
                await self.bot.send_message(
                    chat_id=chat,
                    text="Некорректный ввод, попробуйте снова"
                )

        elif self.add_goal_flag:
            await self.add(base="goals", message=message)

        elif self.add_quote_flag:
            await self.add(base="quotes", message=message)

        elif self.send_message_flag:
            for chat_id in self.users_list:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=text

                )
                self.send_message_flag: bool = False

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=message.message_id - 1
                )

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=message.message_id
                )

                await self.bot.send_message(
                    chat_id=chat,
                    text="Выберите опцию",
                    reply_markup=admin_actions_markup
                )

    async def photo_handler(self, message: Message) -> None:
        """
        Хэндер, реагирующий на фото.

        В зависимости от того, какие флаги
        переведены на True, бот либо сохраняет
        фото в базу данных, либо выводит.
        """
        chat = message["chat"]["id"]
        caption = message["caption"]

        if self.write_day_flag:
            await message.photo[-1].download(f"photos/photo_days_{chat}.jpg")
            await self.add(base="days", message=message, photo_name=f"photos/photo_days_{chat}.jpg")

        elif self.send_message_flag:
            await message.photo[-1].download(f"photos/photo_message_{chat}.jpg")
            with open(f"photos/photo_message_{chat}.jpg", "rb") as photo:
                for chat_id in self.users_list:
                    await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=caption
                    )
                    self.send_message_flag: bool = False

                    await self.bot.send_message(
                        chat_id=chat,
                        text="Выберите опцию",
                        reply_markup=admin_actions_markup
                    )

    @staticmethod
    async def error_handler(error: Message, *args) -> None:
        """
        Хэндлер, отвечающий за ошибки

        Если во время работы бота произойдёт
        ошибка, мы сможем отследить её в логах
        """
        logging.error(error)

    async def callback_handler(self, call: CallbackQuery) -> None:
        """
        Хэндлер, отвечающий за поведение Inline кнопок.

        Хэндлер реагирует на все Inline кнопки,
        которые есть в меню бота,
        каждый callback-запрос отвечает за
        определённый функционал.
        """
        chat = call.message.chat.id
        req = call.data.split("_")
        callback = req[0]
        user_id = call["from"]["id"]
        mess_id = call.message.message_id

        goals_dict = await self.dicts(user_id=user_id, base="goals")
        goals_dict_mark = {
            key + "mark": value
            for key, value in goals_dict.items()
            if len(key) > 0
        }
        quotes_dict = await self.dicts(user_id=user_id, base="quotes")

        if callback in categories:
            if self.del_message:
                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=mess_id - 1
                )

            self.del_message: bool = False
            await self.turn_off_flags()

            await self.bot.delete_message(
                chat_id=chat,
                message_id=mess_id
            )
            await self.keyboards(
                message=call.message, keyboard=f"{callback}"
            )

        elif callback == "write-day":
            await self.bot.delete_message(
                chat_id=chat,
                message_id=mess_id
            )

            await self.bot.send_message(
                chat_id=chat,
                text="Напиши то, что хотел бы запомнить",
                reply_markup=back_to_mainmenu_markup
            )
            self.write_day_flag: bool = True

        elif callback == "remind-day":
            await self.bot.delete_message(
                chat_id=chat,
                message_id=mess_id
            )

            dates = await self.select_dates(tg_id=chat)

            text = "Напиши день, который хотите вспомнить. " \
                   "\n\nПример: \n1) 24.09.2023\n"

            text = text if dates is None else text + dates

            await self.bot.send_message(
                chat_id=chat,
                text=text,
                reply_markup=back_to_mainmenu_markup
            )
            self.remind_day_flag: bool = True

        elif callback in categories_lists:
            await self.elements_list(
                message=call.message,
                elem=categories_lists[callback]
            )

        elif callback == "goalmark":
            mark_goals: InlineKeyboardMarkup = InlineKeyboardMarkup()
            if goals_dict_mark:
                for key, value in goals_dict_mark.items():
                    mark_goals.add(
                        InlineKeyboardButton(
                            text=f"{value}",
                            callback_data=f"{key}"
                        )
                    )

                mark_goals.add(
                    InlineKeyboardButton(
                        text="Назад",
                        callback_data="goals")
                )

            await self.bot.delete_message(
                chat_id=chat,
                message_id=call.message.message_id
            )

            await self.bot.send_message(
                chat_id=chat,
                text="Выберите выполненную цель",
                reply_markup=mark_goals
            )

        elif callback in additions:
            if callback == "addgoal":
                self.add_goal_flag: bool = True

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=call.message.message_id
                )

                await self.bot.send_message(
                    chat_id=chat,
                    text="Введите цель:",
                    reply_markup=back_to_goals_markup
                )

            elif callback == "addquote":
                self.add_quote_flag: bool = True

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=call.message.message_id
                )

                await self.bot.send_message(
                    chat_id=chat,
                    text="Введите цитату:",
                    reply_markup=back_to_quotes_markup
                )

        elif callback in deletings_dict:
            del_goals: InlineKeyboardMarkup = InlineKeyboardMarkup()

            if callback == "deletequote":
                if quotes_dict:
                    for key, value in quotes_dict.items():
                        del_goals.add(
                            InlineKeyboardButton(
                                text=value,
                                callback_data=str(key)
                            )
                        )

                else:
                    await self.bot.delete_message(chat, mess_id)
                    await self.bot.send_message(
                        chat_id=chat,
                        text="Список цитат пуст, удалять нечего",
                        reply_markup=back_to_quotes_markup
                    )

            elif callback == "deletegoal":
                if goals_dict:
                    for key, value in goals_dict.items():
                        del_goals.add(
                            InlineKeyboardButton(
                                text=f"{value}",
                                callback_data=str(key)
                            )
                        )

                else:
                    await self.bot.delete_message(
                        chat_id=chat,
                        message_id=mess_id
                    )

                    await self.bot.send_message(
                        chat_id=chat,
                        text="Список целей пуст, удалять нечего",
                        reply_markup=back_to_goals_markup
                    )

            del_goals.add(
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=deletings_dict[callback][0]
                )
            )

            await self.bot.delete_message(
                chat_id=chat,
                message_id=call.message.message_id
            )

            await self.bot.send_message(
                chat_id=chat,
                text=f"Выберите {deletings_dict[callback][1]}, "
                f"которую хотите удалить",
                reply_markup=del_goals
            )

        elif callback in quotes_dict:
            """Код используется для удаления цитат"""
            sql_connection: Connection = connect("personal_diary.db")
            try:
                cursor: Cursor = sql_connection.cursor()
                sql_query: str = f"""DELETE from quotes
                                     WHERE tg_id={user_id}
                                     AND quote="{quotes_dict[callback]}";"""
                cursor.execute(sql_query)
                sql_connection.commit()

            finally:
                if sql_connection:
                    sql_connection.close()

            quotes_dict: Dict = await self.dicts(
                user_id=user_id,
                base="quotes"
            )
            del_goals: InlineKeyboardMarkup = InlineKeyboardMarkup()

            for key, value in quotes_dict.items():
                del_goals.add(
                    InlineKeyboardButton(
                        text=value,
                        callback_data=str(key)
                    )
                )

            del_goals.add(
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="quotes"
                )
            )

            if len(quotes_dict) != 0:
                await self.bot.answer_callback_query(
                    callback_query_id=call.id,
                    show_alert=True,
                    text="Цитата успешно удалена\U0001F5D1"
                )

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=call.message.message_id
                )

                await self.bot.send_message(
                    chat_id=chat,
                    text="Выберите цитату, которую хотите удалить",
                    reply_markup=del_goals
                )

            else:
                await self.bot.answer_callback_query(
                    callback_query_id=call.id,
                    show_alert=True,
                    text="Вы очистили весь список цитат"
                )

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=call.message.message_id
                )

                await self.keyboards(
                    message=call.message,
                    keyboard="quotes"
                )

        elif callback in goals_dict:
            """Код используется для удаления целей"""
            sql_connection: Connection = connect("personal_diary.db")
            try:
                cursor: Cursor = sql_connection.cursor()
                sql_query: str = f"""DELETE from goals
                                     WHERE goal="{goals_dict[callback]}"
                                     AND tg_id={user_id};"""
                cursor.execute(sql_query)
                sql_connection.commit()

            finally:
                if sql_connection:
                    sql_connection.close()

                mark_goals: InlineKeyboardMarkup = InlineKeyboardMarkup()
                goals_dict: Dict = await self.dicts(
                    user_id=user_id,
                    base="goals"
                )

                if (goals_dict is not None) and (len(goals_dict) > 0):
                    for key, value in goals_dict.items():
                        mark_goals.add(
                            InlineKeyboardButton(
                                text=f"{value}",
                                callback_data=f"{key}"
                            )
                        )

                    mark_goals.add(
                        InlineKeyboardButton(
                            text="Назад",
                            callback_data="goals"
                        )
                    )

                    await self.bot.answer_callback_query(
                        callback_query_id=call.id,
                        show_alert=True,
                        text="Цель успешно удалена\U0001F5D1"
                    )
                    await self.bot.delete_message(
                        chat_id=chat,
                        message_id=call.message.message_id
                    )

                    await self.bot.send_message(
                        chat_id=chat,
                        text="Выберите цель, которую хотите удалить",
                        reply_markup=mark_goals
                    )

                else:
                    await self.bot.answer_callback_query(
                        callback_query_id=call.id,
                        show_alert=True,
                        text="Вы очистили весь список целей"
                    )
                    await self.bot.delete_message(
                        chat_id=chat,
                        message_id=call.message.message_id
                    )

                    await self.keyboards(
                        message=call.message,
                        keyboard="goals"
                    )

        elif callback in goals_dict_mark:
            """
            Код ниже удаляет выполненные цели
             из запланированных и переносит их в выполненные
            """
            data: List = await self.select_one_base(
                user_id=user_id,
                base="goals"
            )

            tg_id: int = int()
            goal: str = str()

            for elem in data:
                tg_id, goal, activation_date = elem
                break
            sql_connection: Connection = connect("personal_diary.db")


            try:
                date_of_completion: str = str(
                    date(datetime.now().year,
                         datetime.now().month,
                         datetime.now().day)
                )
                cursor: Cursor = sql_connection.cursor()
                sql_delete_query: str = f"""DELETE from goals
                                            WHERE tg_id={tg_id}
                                            AND goal="{goal}";"""

                sql_insert_query: str = f"""INSERT INTO reached_goals
                                        (goal, date_of_completion, tg_id)
                                        VALUES
                                        (
                                        "{goal}",
                                        "{date_of_completion}",
                                        {tg_id}
                                        );"""

                cursor.execute(sql_delete_query)
                sql_connection.commit()
                cursor.execute(sql_insert_query)
                sql_connection.commit()
            finally:
                if sql_connection:
                    sql_connection.close()

            mark_goals: InlineKeyboardMarkup = InlineKeyboardMarkup()
            goals_dict = await self.dicts(user_id=user_id, base="goals")
            goals_dict_mark: Dict = {
                key + "mark": value
                for key, value in goals_dict.items()
                if len(key) > 0
            }

            if len(goals_dict_mark) > 0:
                for key, value in goals_dict_mark.items():
                    mark_goals.add(
                        InlineKeyboardButton(
                            text=f"{value}",
                            callback_data=f"{key}"
                        )
                    )

                mark_goals.add(
                    InlineKeyboardButton(
                        text="Назад",
                        callback_data="goals"
                    )
                )

                await self.bot.answer_callback_query(
                    callback_query_id=call.id,
                    show_alert=True,
                    text="Цель выполнена, поздравляю!"
                )

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=call.message.message_id
                )

                await self.bot.send_message(
                    chat_id=chat,
                    text="Выберите выполненную цель",
                    reply_markup=mark_goals
                )

            else:
                await self.bot.answer_callback_query(
                    callback_query_id=call.id,
                    show_alert=True,
                    text="Поздравляем! Вы выполнили все цели"
                )

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=call.message.message_id
                )

                await self.keyboards(message=call.message, keyboard="goals")

        elif callback == "unload-users":
            """
            Выгрузка информации о пользователях.

            Код ниже выгружает информацию о пользователях из базы данных
             и отправляет файлом с расширением .xlsx админу.
            """
            wb: Workbook = Workbook("users-list.xlsx")
            worksheet = wb.add_worksheet()

            # сюда нужно вставить путь до файла с расширением xlsx
            # если файл с таким названием существует,
            # то он удаляется, чтобы не было конфликтов
            if os.path.isfile("users-list.xlsx"):
                os.remove("users-list.xlsx")

            database: Connection = connect("personal_diary.db")
            cursor: Cursor = database.cursor()

            query = """SELECT * FROM users"""

            data: Cursor = cursor.execute(query)
            database.commit()
            data: List = data.fetchall()

            row: int = 0  # номер строки

            worksheet.write(row, 0, "id")
            worksheet.write(row, 1, "tg_id")
            worksheet.write(row, 2, "username")
            worksheet.write(row, 3, "first_name")
            worksheet.write(row, 4, "last_name")
            worksheet.write(row, 5, "activation_date")

            for i_elem in data:
                id, tg_id, username, first_name, last_name, activation_date = i_elem

                row += 1
                worksheet.write(row, 0, id)
                worksheet.write(row, 1, tg_id)
                worksheet.write(row, 2, username)
                worksheet.write(row, 3, first_name)
                worksheet.write(row, 4, last_name)
                worksheet.write(row, 5, activation_date)

            wb.close()

            await self.bot.delete_message(
                chat_id=chat,
                message_id=mess_id
            )

            with open("users-list.xlsx", "rb") as document:
                await self.bot.send_message(
                    chat_id=chat,
                    text="Файл с данными о всех пользователях:"
                )

                await self.bot.send_document(
                    chat_id=chat,
                    document=document
                )
                os.remove("users-list.xlsx")

            await self.bot.send_message(
                chat_id=chat,
                text="Выберите опцию",
                reply_markup=admin_actions_markup
            )

        elif callback == "message-to-users":
            self.send_message_flag: bool = True

            await self.bot.delete_message(
                chat_id=chat,
                message_id=mess_id
            )

            await self.bot.send_message(
                chat_id=chat,
                text="Введите сообщение, "
                     "которое хотите отправить пользователям:",
                reply_markup=back_to_admin_actions_markup
            )

        elif callback == "back-to-admin-actions":
            self.send_message_flag: bool = False

            await self.bot.delete_message(
                chat_id=chat,
                message_id=mess_id
            )

            await self.bot.send_message(
                chat_id=chat,
                text="Выберите опцию",
                reply_markup=admin_actions_markup
            )

    async def admin_handler(self, message: Message) -> None:
        """
        Админ-панель.

        Данная функция открывает проверяет
        наличие админки с помощью функии
        is_admin и предлоставляет открывает
        admin-клавиатуру, если пользователь админ.
        """
        tg_id: int = message.from_user.id
        chat: int = message.chat.id

        accept: bool = await self.is_admin(tg_id=tg_id)

        if accept:
            await self.bot.send_message(
                chat_id=chat,
                text="Выберите опцию",
                reply_markup=admin_actions_markup
            )

    async def is_admin(self, tg_id: int) -> bool:
        """
        Проверка админки.

        Данная функия возвращает True,
        если пользователь админ и False иначе.
        """
        if tg_id in self.admins:
            return True
        return False

    @staticmethod
    def write_or_get_user(action: str, user: User = None) -> List[int] or None:
        """
        Функция ведения учёта пользователей.

        Данная функция позволяет записать информацию
        о пользователе в базу данных,
        при вводе им команды /start.
        Так же функция возвращает список id пользователей,
        если в аргумент action передать 'get'.
        """
        database: Connection = connect("personal_diary.db")
        cursor: Cursor = database.cursor()

        if action.lower() == "write":
            tg_id = user.id
            first_name: str = user.first_name
            last_name: str = user.last_name
            username: str = user.username
            activation_date: str = str(
                date(datetime.now().year,
                     datetime.now().month,
                     datetime.now().day)
            )

            query: str = f"""INSERT INTO users
                            (
                            tg_id,
                            username,
                            first_name,
                            last_name,
                            activation_date
                            )
                            VALUES
                            (
                            {tg_id},
                            "{username}",
                            "{first_name}",
                            "{last_name}",
                            "{activation_date}"
                            );
                        """

            cursor.execute(query)
            database.commit()

        elif action.lower() == "get":
            query: str = """SELECT tg_id FROM users"""
            data: Cursor = cursor.execute(query)
            database.commit()

            data: List = data.fetchall()

            users_list: List = list()
            for user in data:
                users_list.append(user[0])

            return users_list

    async def elements_list(self, message: Message, elem: str) -> None:
        """
        Формирование списка цитат/целей.

        Функция формирует списки целей/цитат пользователя,
        взаимодействует с такими кнопками, как:
        'Список цитат' и 'Список целей'
        """
        chat = user_id = message.chat.id  # int
        await self.bot.delete_message(
            chat_id=chat,
            message_id=message.message_id
        )

        if elem == "goals":
            data: List = await self.select_one_base(
                user_id=user_id,
                base="goals"
            )

            if data:
                row: str = "Твой список целей \U0001F4CB:\n"
                for num, elem in enumerate(data):
                    row += f"{num + 1}. {elem[1]}\n"

                await self.bot.send_message(
                    chat_id=chat,
                    text=row,
                    reply_markup=goals_mark_markup
                )

            else:
                await self.bot.send_message(
                    chat_id=chat,
                    text="Ты пока не записал ни одной цели",
                    reply_markup=back_to_goals_markup
                )

        elif elem == "quotes":
            data: List = await self.select_one_base(
                user_id=user_id,
                base="quotes"
            )

            if data:
                row: str = "Твой список цитат \U0001F4CB:\n"
                for num, i_elem in enumerate(data):
                    row += f"{num + 1}) {i_elem[1]}\n"

                await self.bot.send_message(
                    chat_id=chat,
                    text=row,
                    reply_markup=back_to_quotes_markup
                )

            else:
                await self.bot.send_message(
                    chat_id=chat,
                    text="Ты пока не записал ни одной цитаты",
                    reply_markup=back_to_quotes_markup
                )

    async def dicts(self, user_id: int, base: str) -> Dict:
        """
        Формирование информации из базы данных в списки.

        Функция достаёт информацию из баз данных с помощью 'select_one_base'
        и структурирует её в списки, это необходимо для того,
        чтобы пользователь мог удалять записи и цитаты.
        """
        if base.lower() == "goals":
            goals: List = await self.select_one_base(
                user_id=user_id,
                base=base
            )

            goals_dict: Dict = dict()

            for num, elem in enumerate(goals):
                goals_dict[f"goal{num + 1}"] = elem[1]

            return goals_dict

        elif base.lower() == "quotes":
            quotes: List = await self.select_one_base(
                user_id=user_id,
                base="quotes"
            )

            quotes_dict: Dict = dict()

            for num, elem in enumerate(quotes):
                quotes_dict[f"quote{num + 1}"] = elem[1]

            return quotes_dict

    async def add(self, base: str, message: Message, photo_name=None) -> None:
        """
        Функция записывает данные в выбранную базу данных.

        В функцию передаётся параметр base - название
        таблицы и параметр message, объект типа
        Message, из которого мы берём информацию о
        пользователе и записываем её в таблицу
        с название base.
        """
        sql_connection: Connection = connect("personal_diary.db")
        chat: int = message.chat.id
        text: str = message.text
        tg_id: int = message.from_user.id

        try:
            activation_date: str = str(
                date(datetime.now().year,
                     datetime.now().month,
                     datetime.now().day)
            )

            cursor: Cursor = sql_connection.cursor()

            sql_goal_query: str = f"""
                                   INSERT INTO goals
                                   (goal, activation_date, tg_id)
                                   VALUES
                                   ("{text}", "{activation_date}", {tg_id});
                                   """

            sql_quote_query: str = f"""
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
                image = None
                if photo_name is not None:
                    image = open(photo_name, "rb")


                sql_day_query: str = f"""
                                      INSERT INTO days
                                      (tg_id, activation_date, writing, image)
                                      VALUES
                                      (?, ?, ?, ?);
                                      """

                if text is None:
                    text = message["caption"]

                photo = image.read()
                params = (tg_id, activation_date, text, photo)
                cursor.execute(sql_day_query, params)
                if image:
                    image.close()

            sql_connection.commit()

        finally:
            if sql_connection:
                sql_connection.close()

            if base.lower() == "goals":
                await self.bot.send_message(
                    chat_id=chat,
                    text="Цель успешно добавлена!\U0001F3AF"
                )

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=message.message_id - 1
                )

                self.del_message: bool = True
                self.add_goal_flag: bool = False

                await self.elements_list(message=message, elem="goals")

            elif base.lower() == "quotes":
                await self.bot.send_message(
                    chat_id=chat,
                    text="Цитата успешно добавлена!\U0001F4DA"
                )

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=message.message_id - 1
                )

                self.del_message: bool = True
                self.add_quote_flag: bool = False

                await self.elements_list(message=message, elem="quotes")

            elif base.lower() == "days":
                await self.bot.send_message(
                    chat_id=chat,
                    text="Запись успешно добавлена!\U0001F3AF",
                    reply_markup=back_to_mainmenu_markup
                )

                await self.bot.delete_message(
                    chat_id=chat,
                    message_id=message.message_id - 1

                )
                self.del_message: bool = True
                self.write_day_flag: bool = False

    async def select_all_bases(self, user_id: int, day: str) -> None:
        """
        Данная функция достаёт информацию о пользователе за определённый день.

        В параметре day передаётся дата,
        информацию о которой пользователь хочет узнать,
        если есть какие-либо записи за этот день,
        то пользователю выводит сообщение со список действие,
        иначе сообщение об отсуствии действий.
        """
        chat: int = user_id
        connection: Connection = connect("personal_diary.db")

        try:
            cursor: Cursor = connection.cursor()

            goals_query: str = f"""SELECT goal FROM goals
                                   WHERE tg_id={user_id}
                                   AND activation_date="{day}";"""

            goals_data: Cursor = cursor.execute(goals_query)
            connection.commit()
            goals_data: List = goals_data.fetchall()

            reached_query: str = f"""SELECT goal FROM reached_goals
                                     WHERE tg_id={user_id}
                                     AND date_of_completion="{day}";"""

            reached_goals_data: Cursor = cursor.execute(reached_query)
            connection.commit()
            reached_goals_data: List = reached_goals_data.fetchall()

            quotes_query: str = f"""SELECT quote FROM quotes
                                    WHERE tg_id={user_id}
                                    AND activation_date="{day}";"""

            quotes_data: Cursor = cursor.execute(quotes_query)
            connection.commit()
            quotes_data: List = quotes_data.fetchall()

            days_query: str = f"""SELECT writing, image FROM days
                                  WHERE tg_id={user_id}
                                  AND activation_date="{day}";"""

            days_data: Cursor = cursor.execute(days_query)
            connection.commit()
            days_data: List = days_data.fetchall()

            row = "В этот день ты:"
            if days_data:
                row += "\nДобавил записи:\n"
                if days_data[0][1]:
                    await self.bot.send_message(
                        chat_id=chat,
                        text="Добавил картинок с текстом:"
                    )
                for num, elem in enumerate(days_data):
                    if elem[1]:
                        photo = elem[1]
                        await self.bot.send_photo(
                            chat_id=chat,
                            photo=photo,
                            caption=elem[0]
                        )
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
                    chat_id=chat,
                    text=row,
                    reply_markup=back_to_mainmenu_markup
                )

            else:
                await self.bot.send_message(
                    chat_id=chat,
                    text="В этот день ты ничего не делал",
                    reply_markup=back_to_mainmenu_markup
                )

        finally:
            if connection:
                connection.close()

    @staticmethod
    async def select_dates(tg_id: int) -> str or None:
        """
        Функция сбора дат.

        В данной функции мы подключаемся к базе
        данных и берём все даты, в которые пользователь
        совершал действия, чтобы облегчить поиск по дате.
        """
        connection: Connection = connect("personal_diary.db")

        try:
            cursor: Cursor = connection.cursor()

            goals_query: str = f"""SELECT activation_date FROM goals
                                           WHERE tg_id={tg_id};"""

            goals_data: Cursor = cursor.execute(goals_query)
            connection.commit()
            goals_data: List = goals_data.fetchall()

            reached_query: str = f"""SELECT date_of_completion FROM reached_goals
                                             WHERE tg_id={tg_id};"""

            reached_goals_data: Cursor = cursor.execute(reached_query)
            connection.commit()
            reached_goals_data: List = reached_goals_data.fetchall()

            quotes_query: str = f"""SELECT activation_date FROM quotes
                                            WHERE tg_id={tg_id};"""

            quotes_data: Cursor = cursor.execute(quotes_query)
            connection.commit()
            quotes_data: List = quotes_data.fetchall()

            days_query: str = f"""SELECT activation_date FROM days
                                          WHERE tg_id={tg_id};"""

            days_data: Cursor = cursor.execute(days_query)
            connection.commit()
            days_data: List = days_data.fetchall()

            data_list = [goals_data, reached_goals_data, quotes_data, days_data]
            dates_set: set = {elem[0] for dates_list in data_list for elem in dates_list}
            end_list: List = sorted([".".join(elem.split("-")[::-1]) for elem in dates_set])

            row: str = "Доступные даты:\n"

            for num, date in enumerate(end_list):
                row += f"{num + 1}) {date}\n"

            if len(end_list) > 0:
                return row
            return None

        finally:
            if connection:
                connection.close()

    @staticmethod
    async def select_one_base(user_id: int, base: str) -> List:
        """
        Функция достаёт информацию о пользователе и выбранной базы данных.

        В параметре user_id передаётся ID пользователя,
        а в параметре base передаётся название базы данных.
        По этим параметрам из базы достаётся информация.
        """
        sql_connection: Connection = connect("personal_diary.db")

        try:
            cursor: Cursor = sql_connection.cursor()
            sqlite_query: str = f"""SELECT * FROM {base}
                                    WHERE tg_id={user_id};"""
            sql: Cursor = cursor.execute(sqlite_query)
            sql_connection.commit()

            data: List = sql.fetchall()
            return data

        finally:
            if sql_connection:
                sql_connection.close()



    async def turn_off_flags(self) -> None:
        """
        Перевод всех флагов из True в False.

        Функция переводит все флаги в False, чтобы избежать лишний записей.
        """
        self.write_day_flag: bool = False
        self.remind_day_flag: bool = False
        self.send_message_flag: bool = False
        self.add_goal_flag: bool = False
        self.add_quote_flag: bool = False

    async def keyboards(self, message: Message, keyboard: str):
        """
        Клавиатуры.

        В данной функции при передаче аргумента
        keyboard бот выбирает, какую клавиатуру необходимимо
        отправить пользователю.
        """
        chat: int = message.chat.id

        if keyboard.lower() == "mainmenu":
            await self.bot.send_message(
                chat_id=chat,
                text="Главное меню:",
                reply_markup=main_menu_markup
            )

        elif keyboard.lower() == "goals":
            await self.bot.send_message(
                chat_id=chat,
                text="Здесь ты можешь управлять своими целями \U0001F4DD",
                reply_markup=goals_actions_markup
            )

        elif keyboard.lower() == "quotes":
            await self.bot.send_message(
                chat_id=chat,
                text="Здесь ты можешь управлять своими цитатами \U0001F4D7",
                reply_markup=quotes_actions_markup
            )

    def add_handlers(self) -> None:
        """
        Функция регистрирует все хэндлеры.

        Здесь происходит регистрация хэндлеров, реагирующих
        на команды /start, /menu и /admin, а так же хэндеров,
        реагирующих на ошибки, текст, фото и callback запросы.
        """
        self.dp.register_message_handler(
            callback=self.start_handler,
            commands=["start", "menu"]
        )
        self.dp.register_message_handler(
            callback=self.admin_handler,
            commands=["admin"]
        )

        self.dp.register_message_handler(
            callback=self.text_handler,
            content_types=ContentType.TEXT
        )

        self.dp.register_message_handler(
            callback=self.photo_handler,
            content_types=ContentType.PHOTO
        )

        self.dp.register_callback_query_handler(
            callback=self.callback_handler,
        )

        self.dp.register_errors_handler(
            callback=self.error_handler
        )

    def run(self) -> None:
        """
        Фукнция запуска бота.

        Вызывает функцию add_handlers, которая регистрирует хэндлеры и
        запускает бота с помощью executor.start_polling()
        """
        self.add_handlers()

        executor.start_polling(dispatcher=self.dp, skip_updates=True)


connection: Connection = connect("personal_diary.db")

cursor: Cursor = connection.cursor()

cursor.execute(sql_query_users)
connection.commit()

cursor.execute(sql_query_days)
connection.commit()

cursor.execute(sql_query_quotes)
connection.commit()

cursor.execute(sql_query_goals)
connection.commit()

cursor.execute(sql_query_reached_goals)
connection.commit()

cursor.close()
connection.close()

if __name__ == "__main__":
    bot = PersonalDiaryBot(token=bot_token)
    bot.run()
