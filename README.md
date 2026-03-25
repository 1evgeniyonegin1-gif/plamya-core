# PLAMYA — B2B Lead Generation & AI Outreach Platform

Автоматизированная система поиска бизнес-клиентов и AI-генерации коммерческих предложений.

**1800+ бизнесов обработано. 5 источников парсинга. 4 канала рассылки.**

## Что делает

1. **Сканирует** бизнесы из 5 источников (2GIS, Google Maps, DuckDuckGo, VK, каталоги)
2. **Анализирует** каждый бизнес через AI — определяет потребности, слабые места
3. **Генерирует** персонализированные коммерческие предложения
4. **Рассылает** КП через Email, WhatsApp, Telegram, VK

## Стек

| Компонент | Технология |
|-----------|-----------|
| Backend | Python 3.11+, asyncio |
| Парсинг | Playwright, BeautifulSoup4, DuckDuckGo Search |
| AI | Claude (через CLI subprocess — без API ключей) |
| БД | SQLite (MCP-сервер для CRM) |
| Рассылка | Telethon (Telegram), VK API, SMTP |
| Security | 4-layer prompt injection defense |

## Архитектура

```
shared/           — Ядро: AI клиент, 4-слойная защита, memory
biz_scanner/      — B2B pipeline: scan → analyze → propose → send
  ├── channels/   — Каналы парсинга (2GIS, Google, VK, каталоги)
  ├── ai/         — AI-анализ и генерация КП
  ├── senders/    — 4 канала рассылки
  └── db.py       — SQLite CRM
freelance_engine/ — Фриланс-сканер (FL.ru, Reddit, GitHub)
demos/            — Telegram боты (unit-калькулятор, анализатор отзывов)
```

## Security: 4-Layer Defense

Собственный фреймворк защиты от prompt injection:

1. **Input Guard** — изоляция untrusted данных
2. **Output Guard** — предотвращение утечки секретов
3. **Action Guard** — whitelist действий per-agent
4. **Canary Token** — обнаружение prompt injection

## Запуск

```bash
pip install -r requirements.txt

python -m biz_scanner scan      # Сбор лидов
python -m biz_scanner stats     # Статистика
python scripts/human_send.py    # Отправка КП
```

## Результаты

- 1800+ бизнесов в CRM
- Парсинг 5 источников за ~30 минут
- AI-генерация КП: ~15 секунд на бизнес
- 4-слойная security без единого инцидента

## Автор

Данил Лысенко — [@Daniel_Lysenko33](https://t.me/Daniel_Lysenko33)
