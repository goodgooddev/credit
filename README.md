# Умный кредитный кабинет предпринимателя — бэкенд

FastAPI + PostgreSQL + SQLAlchemy + Alembic + Docker Compose.

## Запуск (одна команда)

```bash
cp .env.example .env          # при необходимости поменяйте пароли
docker compose up --build
```

При старте контейнер `api` сам: применяет миграции → заполняет тестовые данные → запускает сервер.

| Что | Адрес |
|---|---|
| Документация и «песочница» API | http://localhost:8000/docs |
| Сервер жив | http://localhost:8000/health |
| Сервер видит БД | http://localhost:8000/ready |

Каждый участник получает **свою локальную БД** с одинаковой структурой и тестовыми данными.

Полезные команды: `docker compose ps`, `docker compose logs api`, `docker compose logs db`,
`docker compose stop` / `start`. Полностью удалить данные БД: `docker compose down -v`.

## Тестовые аккаунты

Пароль у всех: `demo12345` (меняется переменной `SEED_PASSWORD`).

| Email | Роль | Компании |
|---|---|---|
| client1@demo.local | клиент | «Ромашка-Торг» (хорошая история), ИП Петров (нет истории) |
| client2@demo.local | клиент | «СтройРесурс» (просрочки, налоговый долг) |
| staff@demo.local | сотрудник | — |

## API

Подробные примеры — в [docs/API.md](docs/API.md). Кратко:

| Запрос | Кто | Назначение |
|---|---|---|
| POST /auth/login | все | Войти, получить токен |
| GET /auth/me | авторизованный | Кто я |
| GET /products | все | Каталог |
| GET /companies | клиент | Мои компании |
| POST /applications | клиент | Создать черновик |
| GET /applications | клиент | Мои заявки |
| GET /applications/{id} | владелец / сотрудник | Заявка + результат |
| PATCH /applications/{id} | владелец | Изменить поля (draft, needs_info) |
| POST /applications/{id}/submit | владелец | Отправить |
| GET /applications/{id}/events | владелец / сотрудник | История |
| GET /staff/applications | сотрудник | Список для сотрудника |

Статусы заявки: `draft` → `submitted` → (`needs_info` ↔ `submitted`) → `approved` / `rejected` / `counter_offer` → `accepted`.

## Миграции

```bash
cd backend
alembic revision --autogenerate -m "что изменилось"   # затем ПРОЧИТАТЬ созданный файл
alembic upgrade head
```
Файлы из `backend/alembic/versions/` коммитятся вместе с кодом.

## Тесты

Нужен PostgreSQL (в тестах используется отдельная база, имя **обязательно** на `_test`, её схема пересоздаётся):

```bash
docker compose up -d db
docker compose exec db createdb -U credit_app credit_test
cd backend && pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql+psycopg://credit_app:<POSTGRES_PASSWORD>@localhost:5432/credit_test pytest
```
Порт 5432 в compose наружу не открыт; для тестов с хоста добавьте в сервис `db` строку
`ports: ["127.0.0.1:5432:5432"]`, либо запускайте pytest внутри контейнера `api`.

## Структура

```
backend/app/
  main.py          приложение, роутеры, обработчики ошибок
  config.py        настройки из переменных окружения
  database.py      подключение к PostgreSQL
  models.py        таблицы
  schemas.py       поля запросов и ответов (контракт для фронтенда)
  security.py      хеш паролей, JWT
  deps.py          «кто делает запрос», проверка роли
  seed.py          тестовые данные (идемпотентный)
  routers/         health, auth, products, companies, applications, staff
  services/        checks (validate_application — готово), scoring, decisions — этап 3
```
