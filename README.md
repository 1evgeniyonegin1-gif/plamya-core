# PLAMYA — Marketplace Automation Toolkit

Инструменты для продавцов Wildberries и Ozon: Telegram-боты, AI-аналитика, парсеры, мониторинг.

**3 Telegram-бота. 45+ тестов. 4-слойная AI-безопасность.**

## Что внутри

### Telegram-боты (`demos/`)

| Бот | Описание | Тесты |
|-----|----------|-------|
| **WB SEO Auditor** | AI-аудит карточек WB: парсит через Playwright, анализирует через Claude AI | 45 |
| **Unit Calculator** | Калькулятор unit-экономики WB/Ozon с учётом комиссий, логистики, возвратов | — |
| **Review Analyst** | AI-анализ отзывов: кластеры проблем, тренды, рекомендации | — |

### Shared-библиотека (`shared/`)

- **AI Client** — вызов Claude через CLI subprocess (без API-ключей)
- **4-Layer Security** — защита от prompt injection (input guard, output guard, action guard, canary token)
- **Browser Sessions** — управление Playwright-сессиями
- **Memory** — персистентная файловая память

### Biz Scanner (`biz_scanner/`)

Парсинг бизнесов из 5 источников (2GIS, Google Maps, DuckDuckGo, VK, каталоги) + AI-квалификация лидов. 1800+ бизнесов в базе.

## Стек

| Компонент | Технология |
|-----------|-----------|
| Backend | Python 3.11+, asyncio |
| Боты | aiogram 3, FSM, Inline Keyboards |
| Парсинг | Playwright, BeautifulSoup4 |
| AI | Claude (CLI subprocess — без API-ключей) |
| БД | SQLite |
| Security | 4-layer prompt injection defense |
| Тесты | pytest (45+ unit-тестов) |

## Запуск

```bash
pip install -r requirements.txt
playwright install chromium

# SEO Auditor бот
python -m demos.seo_auditor_bot

# Biz Scanner
python -m biz_scanner scan
python -m biz_scanner stats

# Тесты
pytest demos/seo_auditor_bot/tests/ -v
```

## Безопасность: 4-Layer Defense

1. **Input Guard** — изоляция untrusted данных через XML-теги
2. **Output Guard** — предотвращение утечки секретов
3. **Action Guard** — whitelist действий per-agent
4. **Canary Token** — обнаружение prompt injection

## Автор

Данил Лысенко — [@Daniel_Lysenko33](https://t.me/Daniel_Lysenko33) · [GitHub](https://github.com/dlysenko-dev)
