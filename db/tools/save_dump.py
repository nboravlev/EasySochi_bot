import psycopg2
from psycopg2.extras import execute_values
from psycopg2 import sql
import json

def get_column_types(cursor, schema_name, table_name):
    """Возвращает dict {colname: udt_name} для таблицы"""
    cursor.execute("""
        SELECT column_name, udt_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
    """, (schema_name, table_name))
    return {row[0]: row[1] for row in cursor.fetchall()}


def normalize_row(row, colnames, coltypes):
    """Преобразуем только json/jsonb"""
    new_row = []
    for value, colname in zip(row, colnames):
        coltype = coltypes.get(colname)
        if coltype in ("json", "jsonb") and value is not None:
            new_row.append(json.dumps(value))
        else:
            new_row.append(value)
    return tuple(new_row)

def copy_tables(schema_name, table_names):
    # Подключения
    prod_conn = psycopg2.connect(
        host="89.169.187.49",
        database="tg_app_bd",
        user="tg_app_bd_admin",
        password="fgt4567Qh780"
    )
    test_conn = psycopg2.connect(
        host="89.169.181.200",
        port = "5433",
        database="tg_app_test",
        user="tg_app_bd_test",
        password="1234qazwsx_cvbn"
    )

    with prod_conn, prod_conn.cursor() as prod_cur, test_conn, test_conn.cursor() as test_cur:
        for table_name in table_names:
            print(f"Копируем таблицу: {schema_name}.{table_name}")

                        # Получаем список колонок и их типы
            coltypes = get_column_types(prod_cur, schema_name, table_name)

            # Получаем данные
            select_query = sql.SQL("SELECT * FROM {}.{};").format(
                sql.Identifier(schema_name),
                sql.Identifier(table_name)
            )
            prod_cur.execute(select_query)
            rows = prod_cur.fetchall()

            if not rows:
                print(f"Таблица {table_name}: нет данных для копирования.")
                continue

            # Имена колонок
            colnames = [desc[0] for desc in prod_cur.description]

            # Нормализация только json/jsonb
            rows = [normalize_row(row, colnames, coltypes) for row in rows]

            columns = sql.SQL(', ').join(map(sql.Identifier, colnames))

            # Запрос с ON CONFLICT DO NOTHING
            insert_query = sql.SQL("""
                INSERT INTO {}.{} ({}) VALUES %s
                ON CONFLICT DO NOTHING
            """).format(
                sql.Identifier(schema_name),
                sql.Identifier(table_name),
                columns
            )

            execute_values(test_cur, insert_query, rows)
            test_conn.commit()

            print(f"Таблица {table_name}: скопировано {len(rows)} строк.")

    print("Копирование завершено.")

def main():
    schema_name = "public"
    table_names = ["sessions","search_sessions"]  # список таблиц
    
    copy_tables(schema_name, table_names)

if __name__ == "__main__":
    main()
