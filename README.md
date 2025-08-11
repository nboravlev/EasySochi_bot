#  EasySochi_bot

Telegram-бот для посуточной аренды жилья в Сочи. MVP-версия предназначена для посуточной аренды жилья в Сочи и туристических услуг.


---

##  Функциональность
В приложении есть возможность искать по различным параметрам квартиру или услугу,
бронировать. Оплата в приложении будет реализована позднее.
###  Роли пользователей

- **Админ**  
   добавляет и редактирует карточки квартир или услуг: описание, цены, доступные даты, контакт владельца  
   управляет базой данных через административный интерфейс (в разработке)

- **Арендатор**  
   ищет свободные квартиры по дате  
   отправляет запрос на бронирование  
   переходит в личный чат с владельцем для согласования оплаты

- **Владелец** ( роль появится позднее)
   будет возможность самостоятельно добавлять и редактировать свои карточки, управлять бронированием, смотреть аналитику.

---

##  Технологии

- `Python 3.11+`
- `python-telegram-bot` (Telegram Bot API)
- `PostgreSQL`
- `Docker`, `Docker Compose`
- `FastAPI` (в планах, для админ-панели)
- `SQLAlchemy`, `Alembic` для работы с БД


---

##  Быстрый запуск

> Убедитесь, что установлены Docker и Docker Compose

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/EasySochi_bot.git
cd EasySochi_bot
```
2. Создайте директорию secrets и добавьте в нее файлы
```
mkdir -p secrets
echo "your_db_user" > secrets/postgres_user.txt
echo "your_db_pass" > secrets/postgres_password.txt
echo "your_db_name" > secrets/postgres_db.txt
```
3. Запустите приложение

```
docker compose up -d --build
```

## Структура проекта


EasySochi_bot/
│
├── Dockerfile
├── README.md
├── alembic
│   ├── README
│   ├── env.py
│   ├── script.py.mako
│   └── versions
├── alembic.ini
├── api
│   ├── main.py
│   └── routes
├── bot
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── handlers
│   ├── main.py
│   └── utils
├── db
│   ├── __init.py__
│   ├── db.py
│   ├── db_async.py
│   └── models
├── docker-compose.yml
├── init-pg.sql
├── postgresql.conf
├── requirements.txt
├── reset_db.py
├── schemas
│   ├── __init.py__
│   └── apartment_types.py
├── secrets
│   ├── bot_token.txt
│   ├── postgres_db.txt
│   ├── postgres_password.txt
│   └── postgres_user.txt
├── test_connection.py
├── test_geocode.py
├── utils
│   └── geocoding.py
└── venv
    ├── bin
    ├── include
    ├── lib
    ├── lib64 -> lib
    └── pyvenv.cfg


## Безопасность
 * Конфиденциальные данные (пользователи БД, токены) хранятся через Docker secrets или .env
 * Доступ в Telegram бот регулируется ролями
 * В будущем планируется интеграция с платежной системой с соблюдением PCI-DSS рекомендаций

## Развитие

 * Веб-интерфейс админа (на FastAPI + React)
 * Интеграция с платежной системой (ЮKassa / Stripe) 
 * Роль Владелец с правами создавать и редактировать карточки услуг
 * Создание экосистемы бронирований услуг, квартир, экскурсий в Сочи
 * Вывод аналитики в веб-интерфейс, с доступом по ролям
