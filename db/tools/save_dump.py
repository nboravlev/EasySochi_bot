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

def reset_sequence(conn, schema_name, table_name, start_from=None):
    """
    Сбрасывает sequence для таблицы после копирования данных.
    Если start_from не задан, устанавливает MAX(id)+1.
   """
    seq_name = f"{table_name}_id_seq"

    with conn.cursor() as cur:
         #Проверяем, существует ли sequence
        cur.execute(sql.SQL("""
        SELECT 1 FROM information_schema.sequences
        WHERE sequence_schema = %s AND sequence_name = %s
    """), (schema_name, seq_name))

        if not cur.fetchone():
            print(f"⚠️ Sequence {schema_name}.{seq_name} не найдена, пропускаем.")
            return

        # Определяем значение для старта
        if start_from is None:
            cur.execute(sql.SQL("SELECT COALESCE(MAX(id), 0) + 1 FROM {}.{}")
                        .format(sql.Identifier(schema_name),
                                sql.Identifier(table_name)))
            start_from = cur.fetchone()[0]

        cur.execute(sql.SQL("ALTER SEQUENCE {}.{} RESTART WITH %s")
                    .format(sql.Identifier(schema_name),
                            sql.Identifier(seq_name)),
                    (start_from,))
        conn.commit()

        print(f"🔁 Sequence {schema_name}.{seq_name} сброшен, новое значение: {start_from}")

def copy_tables(schema_name, table_names):
    # Подключения
    prod_conn = psycopg2.connect(
        host="192.168.1.109",
        port = 5432,
        database="tg_app_bd",
        user="tg_app_bd_admin",
        password="fgt4567Qh780"
    )
    test_conn = psycopg2.connect(
        host="192.168.1.109",
        port = 5433,
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
                        # Сбрасываем sequence
            reset_sequence(test_conn, schema_name, table_name)

    print("🎯 Копирование завершено.")

    print("Копирование завершено.")

def main():
    schema_name = "apartments"
    table_names = ["apartment_types","apartments"]  # список таблиц
    
    copy_tables(schema_name, table_names)

def main():
    schema_name = "media"
    table_names = ["images"]  # список таблиц
    
    copy_tables(schema_name, table_names)

"""
def main():
    schema_name = "public"
    table_names = ["roles","booking_types","sources","users","sessions","search_sessions","bookings"]  # список таблиц
    
    copy_tables(schema_name, table_names)
"""
if __name__ == "__main__":
    main()
