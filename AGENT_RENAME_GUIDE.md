# AGENT RENAME GUIDE (Django Template)

Этот файл — инструкция для ИИ-агентов, как **безошибочно** переименовывать Django project package (сейчас `config`) в новое имя (например, `myproj`).

## Цель

Переименовать только Django project package и связанные ссылки, не ломая Docker, Celery, settings и запуск.

---

## Входные данные

- `OLD_NAME` — текущее имя пакета (по умолчанию: `config`)
- `NEW_NAME` — новое имя пакета (задаёт пользователь)

Пример:
- `OLD_NAME=config`
- `NEW_NAME=myproj`

---

## Обязательные правила

1. Делай переименование **только если `NEW_NAME` явно задан пользователем**.
2. Используй аккуратные замены по шаблонам, не меняй случайный текст без префикса.
3. Не меняй сетевые и env-правила инфраструктуры (`expose` в production, `ports` в override).
4. После правок обязательно проверь запуск и health endpoint.

---

## Шаг 1. Переименуй директорию пакета

- Было: `app/config/`
- Стало: `app/<NEW_NAME>/`

Предпочтительно через git rename:

```bash
git mv app/config app/<NEW_NAME>
```

Если git недоступен — файловое переименование допустимо.

---

## Шаг 2. Обнови Python/Django ссылки

### 2.1 `DJANGO_SETTINGS_MODULE`

Заменить:
- `config.settings.dev` -> `<NEW_NAME>.settings.dev`
- `config.settings.prod` -> `<NEW_NAME>.settings.prod`

Где обычно встречается:
- `app/manage.py`
- `app/<NEW_NAME>/wsgi.py`
- `app/<NEW_NAME>/asgi.py`
- `docker-compose.yml`
- `docker-compose.override.yml`
- `app/pytest.ini`

### 2.2 Root URL + WSGI references

В `app/<NEW_NAME>/settings/base.py`:
- `ROOT_URLCONF = "config.urls"` -> `"<NEW_NAME>.urls"`
- `WSGI_APPLICATION = "config.wsgi.application"` -> `"<NEW_NAME>.wsgi.application"`

### 2.3 Celery module name

Заменить:
- `celery -A config ...` -> `celery -A <NEW_NAME> ...`
- `Celery("config")` -> `Celery("<NEW_NAME>")`

Где проверять:
- `docker-compose.yml`
- `docker-compose.override.yml`
- `app/<NEW_NAME>/celery.py`

### 2.4 Gunicorn target

В `Dockerfile`:
- `config.wsgi:application` -> `<NEW_NAME>.wsgi:application`

### 2.5 Package init

В `app/<NEW_NAME>/__init__.py` должно остаться:

```python
from .celery import app as celery_app

__all__ = ("celery_app",)
```

---

## Шаг 3. Обнови документацию и agent-инструкции

Проверь и обнови ссылки:
- `README.md`
- `.copilot-instructions.md`

Минимум: все упоминания `config.settings.*` и `celery -A config`.

---

## Шаг 4. Поиск-контроль (не пропустить хвосты)

Перед финалом найди остатки `OLD_NAME`:

```bash
# Примеры поиска
grep -R "config\.settings\|celery -A config\|config\.wsgi\|config\.urls" -n .
```

На Windows/PowerShell аналогично через поиск по рабочей области.

Критерий готовности: **нет технических ссылок на `OLD_NAME`**, кроме исторических текстов/примеров, если они явно помечены как пример.

---

## Шаг 5. Валидация запуска

```bash
docker compose up --build
```

Проверить:
- Web стартует без ImportError
- Worker/Beat стартуют
- `http://localhost:8000/health/` отвечает `{"status":"ok"}`

Опционально:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py migrate --plan
```

---

## Anti-patterns (запрещено)

- Менять production `expose` на `ports` в `docker-compose.yml`.
- Хардкодить `ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS` вместо env.
- Менять `DATABASE_URL` host с `db` на `localhost` внутри контейнеров.
- Переименовывать папку `app/` (это отдельная задача, не часть текущего rename).

---

## Краткий checklist для агента

- [ ] Получил `NEW_NAME` от пользователя
- [ ] Переименовал `app/config` -> `app/<NEW_NAME>`
- [ ] Обновил `DJANGO_SETTINGS_MODULE` везде
- [ ] Обновил `ROOT_URLCONF` и `WSGI_APPLICATION`
- [ ] Обновил `celery -A ...` и `Celery("...")`
- [ ] Обновил `Dockerfile` gunicorn target
- [ ] Обновил `README.md` и `.copilot-instructions.md`
- [ ] Проверил, что не осталось технических ссылок на `config`
- [ ] Проверил старт через `docker compose up --build`
