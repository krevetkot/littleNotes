# littleNotes — защищённое REST API для заметок

Реализованы меры безопасности:
- аутентификация по JWT
- защита от SQLi: : все запросы к БД через ORM SQLAlchemy, которая параметризует запросы
- защита от XSS: экранирование пользовательских данных с помощью html.escape
- хэширование паролей и требования к паролю для его усиления

Backend на **Python / Flask**, есть CI/CD-пайплайн с SAST- и SCA-сканерами.

**Последний успешный запуск pipeline:** https://github.com/krevetkot/littleNotes/actions/runs/36264980310

---

## Содержание
1. [Стек](#стек)
2. [Запуск](#запуск)
3. [API](#api)
4. [Меры защиты](#меры-защиты)
5. [CI/CD и security-сканеры](#cicd-и-security-сканеры)
6. [Тестирование API](#тестирование-api)

---

## Стек

| Компонент           | Технология |
|---------------------|---|
| Язык, фреймворк     | Python 3.12, Flask 3 |
| База данных         | PostgreSQL 16 (Docker) |
| ORM                 | Flask-SQLAlchemy |
| Хэширование паролей | bcrypt |
| Токены              | PyJWT (HS256) |
| SAST                | Bandit |
| SCA                 | pip-audit, OWASP Dependency-Check |
| CI/CD               | GitHub Actions |

---

## Запуск

Требуется Python 3.12+ и Docker.

```bash
git clone https://github.com/krevetkot/littleNotes.git
cd littleNotes

python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux / macOS
pip install -r requirements.txt

cp .env.example .env             # затем заменить SECRET_KEY на случайный (см. ниже)
docker compose up -d             # поднять PostgreSQL
python main.py                   # http://127.0.0.1:5000
```

Сгенерировать `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

| Адрес | Что там |
|---|---|
| `http://127.0.0.1:5000/` | веб-интерфейс (вход, регистрация, заметки) |

---

## API

Все запросы и ответы — JSON. Ошибки возвращаются в формате `{"error": "описание"}`.

| Метод | Путь | Авторизация | Описание |
|---|---|---|---|
| `POST` | `/auth/register` | — | Регистрация пользователя |
| `POST` | `/auth/login` | — | Вход, выдача JWT |
| `GET` | `/api/data` | JWT | Список заметок текущего пользователя |
| `POST` | `/api/notes` | JWT | Создание заметки |

Защищённые эндпоинты требуют заголовок:
```
Authorization: Bearer <token>
```

### `POST /auth/register`
Тело: `{"username": "alice", "password": "Str0ng#Pass"}`

| Код | Когда | Ответ |
|---|---|---|
| 201 | пользователь создан | `{"id": 1, "username": "alice"}` |
| 400 | нет логина/пароля или пароль слабый | `{"error": "..."}` |
| 409 | логин занят | `{"error": "Username already exists"}` |

Требования к паролю: не меньше 8 символов, строчная и заглавная латинская буква, цифра и спецсимвол.

### `POST /auth/login`
Тело: `{"username": "alice", "password": "Str0ng#Pass"}`

| Код | Когда | Ответ |
|---|---|---|
| 200 | успешный вход | `{"token": "eyJhbGciOi..."}` |
| 400 | нет логина или пароля | `{"error": "..."}` |
| 401 | неверный логин или пароль | `{"error": "Invalid credentials"}` |

### `GET /api/data`
Возвращает заметки **только текущего пользователя**, новые первыми.

| Код | Когда | Ответ |
|---|---|---|
| 200 | успех | `[{"id": 1, "title": "...", "text": "...", "created_at": "26.09.2026 11:50"}]` |
| 401 | нет токена / токен невалиден / истёк | `{"error": "Unauthorized" \| "Invalid token" \| "Token expired"}` |

### `POST /api/notes`
Тело: `{"title": "Заголовок", "text": "Текст"}`

| Код | Когда | Ответ |
|---|---|---|
| 201 | заметка создана | объект заметки |
| 400 | нет JSON, заголовка или текста | `{"error": "..."}` |
| 401 | нет токена / токен невалиден / истёк | `{"error": "..."}` |

---

## Меры защиты

### 1. SQL-инъекции (OWASP A03:2021 — Injection)

Все обращения к базе выполняются через **ORM SQLAlchemy**; SQL-запросы нигде не собираются конкатенацией строк.

```python
db.select(User).filter_by(username=username)
```

SQLAlchemy превращает это в **параметризованный запрос**: значение `username` передаётся драйверу PostgreSQL отдельно от текста SQL и никогда не интерпретируется как код. Ввод вида `' OR 1=1 --` будет просто искаться как логин.

### 2. XSS (OWASP A03:2021 — Injection)

**Серверная сторона.** Все данные, пришедшие от пользователя, экранируются в момент формирования ответа функцией `html.escape` — спецсимволы `< > & " '` заменяются на HTML-сущности:

- `title` и `text` заметки — в `Note.to_dict()` (`models.py`);
- `username` — в ответе `/auth/register` (`routes/auth.py`).

Экранирование выполняется **при выводе, а не при сохранении**: в базе хранятся исходные данные, а экранирование применяется под конкретный контекст вывода (рекомендация OWASP XSS Prevention Cheat Sheet).

**Клиентская сторона (второй слой).** Веб-интерфейс вставляет пользовательский текст в страницу только через `textContent`, никогда через `innerHTML`, поэтому браузер не интерпретирует его как разметку.

### 3. Аутентификация (OWASP A07:2021 — Identification and Authentication Failures)

**Хэширование паролей — bcrypt.**
- При регистрации пароль хэшируется со случайной солью; соль хранится внутри хэша.
- В базе хранится только хэш; пароль в открытом виде нигде не сохраняется и не возвращается в ответах.
- При входе пароль проверяется.

**Политика паролей.** При регистрации пароль проверяется регулярным выражением на сервере (минимум 8 символов, строчная и заглавная буквы, цифра, спецсимвол). В интерфейсе те же правила подсвечиваются при вводе, но решающей является проверка на сервере.

**Единое сообщение об ошибке входа.** И при несуществующем логине, и при неверном пароле возвращается одинаковый ответ `401 Invalid credentials`, чтобы нельзя было выяснить, какие логины зарегистрированы.

**JWT.**
- После успешного входа выдаётся токен, подписанный HMAC-SHA256 (`HS256`) секретным ключом `SECRET_KEY`.
- Payload: `sub` (id пользователя), `iat` (время выдачи), `exp` (истекает через 12 часов). Пароль и другие секреты в токен не кладутся — payload только подписан, но не зашифрован.
- `SECRET_KEY` — случайная строка из 64 hex-символов, хранится в `.env`.

**Middleware проверки токена** — декоратор `token_required` (`security.py`), навешен на все эндпоинты `/api/*`:
1. требует заголовок `Authorization: Bearer <token>`, иначе — `401`;
2. проверяет подпись и срок действия через `jwt.decode(..., algorithms=["HS256"])`. Явный список алгоритмов защищает от подмены алгоритма (в т.ч. атаки `alg: none`);
3. требует наличия полей `exp` и `sub` (`options={"require": [...]}`);
4. при любой ошибке возвращает `401` и не пускает запрос в обработчик;
5. при успехе кладёт id пользователя в `flask.g.user_id`.

### 4. Контроль доступа (OWASP A01:2021 — Broken Access Control)

Id пользователя берётся **только из проверенного токена**, а не из параметров запроса:
- `GET /api/data` фильтрует заметки по `user_id = g.user_id` — пользователь не видит чужие заметки;
- `POST /api/notes` сохраняет заметку с `user_id` из токена — нельзя создать заметку от имени другого пользователя.

### 5. Прочее

- **Секреты вне кода**: ключ JWT и параметры БД — в `.env` (в `.gitignore`); в репозитории только `.env.example`. Ключ NVD для CI — в GitHub Secrets.
- **Debug-режим отключён по умолчанию**: `debug` включается только при `FLASK_DEBUG=1` (исправление находки Bandit B201, см. ниже).

---

## CI/CD и security-сканеры

Pipeline: [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Запускается автоматически **при каждом push и pull request** в `master`. Два параллельных job:

| Job | Инструмент | Что проверяет |
|---|---|---|
| **SAST** | Bandit | исходный код на небезопасные конструкции |
| **SCA** | pip-audit | зависимости из `requirements.txt` по базе уязвимостей PyPI |
| **SCA** | OWASP Dependency-Check | зависимости по базе NVD (CVE); HTML-отчёт сохраняется как артефакт запуска |

Dependency-Check использует API-ключ NVD, который хранится в GitHub Secrets (`NVD_API_KEY`) и не попадает в код и логи.

### Найденные и исправленные проблемы

Первый запуск Bandit завершился с ошибкой и нашёл две проблемы:

![Найденные уязвимости](screenshots/1.png)

Я убрала debug=True и переименовала переменную, которую bandit ошибочно посчитал захардкоженным паролем.

Больше уязвимостей нет:

![Успешное завершение Bandit](screenshots/2.png)

### Отчёты SCA

![Успешное завершение SCA](screenshots/3.png)

---

## Тестирование API

### Регистрация

```powershell
curl.exe -i -X POST http://127.0.0.1:5000/auth/register -H "Content-Type: application/json" -d '{\"username\":\"alice\",\"password\":\"Str0ng#Pass\"}'
```
![Сильный пароль](screenshots/4.png)

Слабый пароль отклоняется:
```powershell
curl.exe -i -X POST http://127.0.0.1:5000/auth/register -H "Content-Type: application/json" -d '{\"username\":\"bob\",\"password\":\"12345\"}'
```
![Слабый пароль](screenshots/5.png)

### Пароль хранится в виде bcrypt-хэша

```powershell
docker compose exec db psql -U notes -d notes -c "select id, username, password_hash from users;"
```
![Хэшированный пароль](screenshots/6.png)

### Вход

```powershell
curl.exe -i -X POST http://127.0.0.1:5000/auth/login -H "Content-Type: application/json" -d '{\"username\":\"alice\",\"password\":\"Str0ng#Pass\"}'
```
![Токен](screenshots/7.png)

eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwiaWF0IjoxNzkwNDUyODY4LCJleHAiOjE3OTA0OTYwNjh9.Q3qJpOqXraEQ5xn_yWQj7THICV7GWC3tHIx2oP0KkUs

Неверный пароль:
```powershell
curl.exe -i -X POST http://127.0.0.1:5000/auth/login -H "Content-Type: application/json" -d '{\"username\":\"alice\",\"password\":\"Wrong#Pass1\"}'
```
![Неверный пароль](screenshots/8.png)

### Доступ без токена запрещён

```powershell
curl.exe -i http://127.0.0.1:5000/api/data
```
![Неавторизованный пользователь](screenshots/4.png)

С поддельным токеном:
```powershell
curl.exe -i http://127.0.0.1:5000/api/data -H "Authorization: Bearer abc.def.ghi"
```
![Поддельный токен](screenshots/a.png)

### Доступ с токеном

Создать заметку с попыткой XSS:
```powershell
curl.exe -i -X POST http://127.0.0.1:5000/api/notes -H "Authorization: Bearer $t" -H "Content-Type: application/json" -d '{\"title\":\"<script>alert(1)</script>\",\"text\":\"<b>bold</b>&more\"}'
```
![XSS](screenshots/c.png)

Получить свои заметки:
```powershell
curl.exe -i http://127.0.0.1:5000/api/data -H "Authorization: Bearer $t"
```
![Создание заметки](screenshots/b.png)
