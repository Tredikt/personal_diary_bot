from sqlite3 import connect

connection = connect("personal_diary.db")
cursor = connection.cursor()

sql_query = """ALTER TABLE days ADD COLUMN image BLOB;"""
cursor.execute(sql_query)
connection.commit()

cursor.close()
connection.close()