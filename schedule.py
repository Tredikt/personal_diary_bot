import asyncio
import aioschedule
from sqlite3 import connect
from aiogram import Bot
from config import bot_token
from random import choice

shedule_flag = False
bot = Bot(token=bot_token)


async def main_schedule():
    await asyncio.create_task(scheduler())


async def turn_on_flag():
    global shedule_flag
    shedule_flag = True


async def scheduler():
    global shedule_flag
    if shedule_flag:
        aioschedule.every().day.at("09:00").do(reminder)
        shedule_flag = False
    aioschedule.every().day.at("8:55").do(turn_on_flag)

    # aioschedule.every(3).seconds.do(reminder)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def reminder():
    connection = connect("personal_diary.db")
    cursor = connection.cursor()

    sql_query_users = f"""SELECT tg_id FROM users"""
    users_data = cursor.execute(sql_query_users)
    users_data = users_data.fetchall()
    connection.commit()
    #print(users_data)
    for tg_id_tuple in users_data:
        tg_id = tg_id_tuple[0]

        sql_query_goals = f"""SELECT goal FROM goals WHERE tg_id={tg_id};"""
        goals_data = cursor.execute(sql_query_goals)
        connection.commit()
        goals_data = goals_data.fetchall()

        sql_query_quotes = f"""SELECT quote FROM quotes WHERE tg_id={tg_id};"""
        quotes_data = cursor.execute(sql_query_quotes)
        connection.commit()
        quotes_data = quotes_data.fetchall()
        connection.commit()

        # print(goals_data, quotes_data)
        goals_row = "<strong>Твой список целей:</strong>\n"
        quote_row = "<strong>Рандомная цитата:</strong>\n"
        if len(goals_data) > 0:
            for num, goals_tuple in enumerate(goals_data):
                goal = goals_tuple[0]
                goals_row += f"{num + 1}) {goal}\n"
        else:
            goals_row = "<b>У тебя пока нет целей, добавь одну и следуй ей!</b>\n"

        if len(quotes_data) > 0:
            quotes = [quotes_tuple[0] for quotes_tuple in quotes_data]
            quote_row += choice(quotes)
        else:
            quote_row = "<b>Ты пока не добавил ни одной цитаты</b>"

        await bot.send_message(
            chat_id=tg_id,
            text=f"<strong>Просыпайся, друг мой, ведь у тебя есть цели, к которым нужно стремиться!</strong>\n"
                 f"{goals_row} {quote_row}",
            parse_mode="html"
        )

    connection.close()


if __name__ == '__main__':
    asyncio.run(main_schedule())