# PLAMYA

Платформа автономных AI-агентов. Монорепо: outreach, фриланс-сканер, task orchestrator, дашборд.

"From ashes, autonomy." | Маскот: механический феникс

## Стек
- Python 3.11+, FastAPI, React + Vite
- Claude API (через CLI subprocess)
- SQLite (CRM, tasks, memory)
- Playwright (browser automation)

## Структура
```
shared/           — Ядро: AI клиент, security (4 слоя), memory, heartbeat
agents/           — АРХИТЕКТОР (Opus) + КОДЕР (Sonnet)
nexus/            — Orchestrator, task queue, think loop
mission_control/  — FastAPI + React дашборд (порт 8006)
biz_scanner/      — B2B outreach: сбор лидов, аудит, КП, отправка
freelance_engine/ — Фриланс сканер: FL.ru, Reddit, GitHub, HackerNews
```

## Запуск
```bash
pip install -r requirements.txt

python -m biz_scanner run       # Автономный outreach
python -m biz_scanner scan      # Массовый сбор лидов
python -m biz_scanner stats     # Статистика
python -m nexus.run             # Оркестратор агентов
python -m freelance_engine scan # Фриланс сканирование

# Дашборд
cd mission_control/backend && uvicorn main:app --port 8006
cd mission_control/frontend && npm run dev
```

## Статус
Active
