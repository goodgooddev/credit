# API для фронтенда (Олег)

Базовый адрес: `http://localhost:8000`. Интерактивная версия со всеми полями: `/docs`.
CORS открыт для `http://localhost:3000` и `http://localhost:5173` (список — переменная `CORS_ORIGINS`).

## Главное, что нужно знать

1. **Токен.** После `POST /auth/login` в каждый запрос добавлять заголовок `Authorization: Bearer <access_token>`.
   Токен живёт 12 часов. Нет/плохой токен → `401`.
2. **Деньги — строки**: `"500000.00"`. И в запросах, и в ответах. Не превращать в `float`; для показа форматировать.
3. **Права.** Чужая заявка → `403`. Клиентские методы под сотрудником → `403`.
4. **Формат ошибок.**
   - `401/403/404/409`: `{"detail": "Текст ошибки"}`
   - `422` (ошибка в данных): `{"detail": "...", "errors": [{"field": "amount", "message": "Значение должно быть больше 0"}]}` — `field` совпадает с именем поля формы, `message` можно показывать пользователю.
5. **Статус и решение меняет только сервер.** Если передать `status`, `risk_level`, `decision` и любые другие лишние поля → `422`.
6. **Двойное нажатие «Отправить».** Повторный `POST .../submit` вернёт `409`. Блокируйте кнопку на время запроса; `409` после успешной отправки можно считать «уже отправлено».

## Статусы заявки (`status`)

| Значение | Что показать | Клиент может редактировать |
|---|---|---|
| `draft` | Черновик | да |
| `submitted` | Отправлена, на рассмотрении | нет |
| `needs_info` | Нужны уточнения | да, затем отправить снова |
| `approved` | Одобрена | нет |
| `rejected` | Отказ | нет |
| `counter_offer` | Предложены другие условия | нет (принять/отклонить — этап 4) |
| `accepted` | Условия приняты | нет |

`POST /applications/{id}/submit` сразу выносит решение, отдельного «ожидания» нет: в ответе уже итоговый статус
(`approved`, `rejected` или `needs_info`) и `latest_assessment` с объяснением. Статус `submitted` после отправки
остаётся, только если проверки были недоступны (см. «Решение по заявке» ниже). `counter_offer` и `accepted` — этап 4.

## Сценарий «создать → заполнить → отправить»

```
POST /auth/login            {"email":"client1@demo.local","password":"demo12345"}
GET  /companies             → выбрать company_id
GET  /products              → выбрать product_id (там же min/max суммы и сроки, список целей)
POST /applications          {"company_id":1,"product_id":1,"amount":"500000.00"}   → 201, черновик
PATCH /applications/1       {"term_months":12,"purpose":"Закупка товара",
                             "annual_revenue":"12000000.00","monthly_expenses":"600000.00","existing_debt":"0"}
POST /applications/1/submit → 200, status = "approved" | "rejected" | "needs_info" (+ latest_assessment)
GET  /applications/1/events → история
```

Черновик можно сохранять **частично** — обязателен только `company_id`. Полнота проверяется при `submit`.
Поля, которые клиент заполняет: `product_id`, `amount`, `term_months`, `purpose`, `annual_revenue`, `monthly_expenses`, `existing_debt` (`existing_debt: "0"`, если долгов нет), `monthly_debt_payment` (ежемесячные платежи по текущим кредитам).
`monthly_expenses` указывается без этих платежей. Если долг больше нуля, неизвестный платёж приводит к `needs_info`; нулевой платёж можно указать явно.

## Примеры ответов

### POST /auth/login → 200
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {"id": 1, "email": "client1@demo.local", "full_name": "Иван Петров", "role": "client"}
}
```
`role`: `client` или `staff` — по нему выбирать, какой интерфейс показывать.

### GET /products → 200
```json
[{
  "id": 1, "code": "working_capital", "name": "Оборотный кредит",
  "description": "На пополнение оборотных средств: закупка товара, сырья, текущие расходы.",
  "purposes": ["Закупка товара", "Пополнение оборотных средств", "Выплата зарплат"],
  "min_amount": "100000.00", "max_amount": "5000000.00",
  "min_term_months": 3, "max_term_months": 36, "annual_rate": "18.50"
}]
```

### GET /companies → 200
```json
[{"id": 1, "name": "ООО «Ромашка-Торг»", "inn": "7700000001", "industry": "Розничная торговля",
  "region": "Москва", "registration_date": "2019-03-12", "employees_count": 14}]
```

### GET /applications/{id}, POST /applications, PATCH, submit → 200/201 (одна и та же форма)
```json
{
  "id": 1, "company_id": 1, "product_id": 1,
  "amount": "500000.00", "term_months": 12, "purpose": "Закупка товара",
  "annual_revenue": "12000000.00", "monthly_expenses": "600000.00", "existing_debt": "0.00",
  "status": "approved", "risk_level": "low", "decision": "approved",
  "submitted_at": "2026-10-20T14:47:20.589356+03:00",
  "created_at": "2026-10-20T14:47:20.482965+03:00",
  "updated_at": "2026-10-20T14:47:20.587070+03:00",
  "company": { "id": 1, "name": "ООО «Ромашка-Торг»", "inn": "7700000001", "...": "..." },
  "product": { "id": 1, "name": "Оборотный кредит", "...": "..." },
  "latest_assessment": {
    "id": 1, "risk_score": 0, "risk_level": "low", "decision": "approved",
    "reasons": ["Заявка одобрена на условиях выбранного продукта"],
    "offered_conditions": {"amount": "500000.00", "term_months": 12, "annual_rate": "18.50", "monthly_payment": "45959.06"},
    "rules_version": "2026-10-v2", "created_at": "2026-10-20T14:47:20.600000+03:00"
  }
}
```
Для черновика `status = "draft"`, а `risk_level`, `decision`, `latest_assessment` равны `null`.

### Решение по заявке

После `submit` (и после `reprocess`) в `latest_assessment` лежит последнее решение. Что показывать:

| `decision` | `status` заявки | Что показать клиенту |
|---|---|---|
| `approved` | `approved` | Одобрено. Условия — в `offered_conditions` (сумма, срок, ставка, ежемесячный платёж). `reasons` — пояснение (ставка выбранного продукта сохраняется) |
| `rejected` | `rejected` | Отказ. Причины — **список строк в `latest_assessment.reasons`** (в `decision` лежит только код `"rejected"`) |
| `needs_info` | `needs_info` | Нужны уточнения: что именно сделать — в `reasons`. Клиент правит заявку (`PATCH`) и снова вызывает `submit` |
| `check_unavailable` | `submitted` | Проверки не удалось выполнить. **Это не отказ.** Показать `reasons[0]` и кнопку «Повторить» → `POST /applications/{id}/reprocess` |

`risk_level` — `low` / `medium` / `high` (при недоступной проверке или недостающих данных для оценки — `null`). `offered_conditions` заполнено только при `approved`.
Одинаковые данные всегда дают одинаковое решение. Каждое рассмотрение — новая запись оценки, прежние не удаляются.

Пример `needs_info`: в заявке есть задолженность, но неизвестен ежемесячный платёж по ней.
```json
{"decision": "needs_info", "risk_level": null, "offered_conditions": null,
 "requested_fields": ["monthly_debt_payment"],
 "reasons": ["Укажите ежемесячный платёж по действующим кредитам (0, если платежей сейчас нет). Ежемесячные расходы указывайте без этих платежей."]}
```

Клиент передаёт `PATCH /applications/{id}` с `{"monthly_debt_payment":"10000.00"}`, затем вызывает `submit`.
Новый платёж вычитается из свободного потока и может привести как к одобрению, так и к отказу.
При остальных исходах `requested_fields` — пустой список. Поле входит в `latest_assessment`.
Цель кредита очищается от пробелов по краям и при отправке проверяется по `product.purposes`.

### POST /applications/{id}/reprocess → 200
Повторить обработку, если последнее решение — `check_unavailable`. Доступно владельцу и сотруднику. Возвращает ту же форму,
что и `submit`. Если решение уже вынесено или заявка ещё черновик → `409`.
`GET /applications` (список) отдаёт те же поля **без** `company`, `product`, `latest_assessment`. Фильтр: `?status=draft`.

### Ошибки
```json
// PATCH {"amount": "-100"} → 422
{"detail": "Проверьте поля запроса", "errors": [{"field": "amount", "message": "Значение должно быть больше 0"}]}

// POST .../submit с неполной заявкой → 422
{"detail": "Заявка заполнена не полностью",
 "errors": [{"field": "term_months", "message": "Укажите срок"}, {"field": "purpose", "message": "Укажите цель кредита"}]}

// сумма вне лимитов продукта → 422
{"detail": "Заявка заполнена не полностью",
 "errors": [{"field": "amount", "message": "Сумма по продукту: от 100000.00 до 5000000.00"}]}

// повторная отправка / правка после отправки → 409
{"detail": "Заявка в статусе «submitted» не может быть изменена или отправлена повторно"}

// чужая заявка → 403
{"detail": "Доступ запрещён"}
```

### GET /applications/{id}/events → 200
```json
[
  {"id": 1, "event_type": "created", "from_status": null, "to_status": "draft", "actor_id": 1,
   "payload": {"company_id": 1}, "created_at": "2026-10-20T14:47:20.482965+03:00"},
  {"id": 2, "event_type": "updated", "from_status": null, "to_status": null, "actor_id": 1,
   "payload": {"fields": ["purpose", "term_months"]}, "created_at": "..."},
  {"id": 3, "event_type": "submitted", "from_status": "draft", "to_status": "submitted", "actor_id": 1,
   "payload": {}, "created_at": "..."},
  {"id": 4, "event_type": "assessed", "from_status": "submitted", "to_status": "approved", "actor_id": null,
   "payload": {"assessment_id": 1, "decision": "approved", "risk_level": "low", "risk_score": 0,
               "rules_version": "2026-10-v2"}, "created_at": "..."}
]
```
`actor_id: null` — действие выполнила система. Типы событий: `created`, `updated`, `submitted`, `assessed` (решение системы),
`reprocessed` (повторный запуск после недоступных проверок).

### GET /staff/applications → 200 (только `staff`)
Параметры: `status` (по умолчанию все, кроме `draft`), `limit` (1–200, по умолчанию 50), `offset`.
Элемент — те же поля заявки плюс `company_name` и `owner_email`. Детали заявки сотрудник открывает через `GET /applications/{id}`.
