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
├── bot/                   # Telegram-бот: логика, хендлеры, состояния
│   ├── handlers/
│   ├── states/
│   └── main.py
│
├── db/                    # Модели и миграции базы данных
│   ├── models/
│   ├── migrations/
│   └── db.py
│   └── postgresql.conf
│   └── init-pg.sql
│
├── secrets/               # Секретные данные (не пушить в git)
│   ├── postgres_user.txt
│   ├── postgres_password.txt
│   └── postgres_db.txt
│
├── Dockerfile
├── docker-compose.yml
└── README.md


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
