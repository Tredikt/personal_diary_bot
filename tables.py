sql_query_users: str = f"""CREATE TABLE IF NOT EXISTS users
            (   
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                activation_date TEXT
            );
            """

sql_query_days: str = f"""CREATE TABLE IF NOT EXISTS days
                    (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tg_id INTEGER,
                        activation_date TEXT,
                        writing TEXT
                    );"""

sql_query_goals: str = f"""CREATE TABLE IF NOT EXISTS goals
                    (
                        tg_id INTEGER,
                        goal TEXT,
                        activation_date TEXT
                    );"""

sql_query_quotes: str = f"""CREATE TABLE IF NOT EXISTS quotes
                    (
                        tg_id INTEGER,
                        quote TEXT,
                        activation_date TEXT
                    );"""

sql_query_reached_goals: str = f"""CREATE TABLE IF NOT EXISTS reached_goals
                            (
                                tg_id INTEGER,
                                goal TEXT,
                                date_of_completion TEXT
                            );"""