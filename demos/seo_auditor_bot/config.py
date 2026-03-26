"""Конфигурация SEO Аудитор бота."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из папки бота
load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN = os.getenv("SEO_AUDITOR_BOT_TOKEN", "")

# Контакт для CTA
CONTACT_TG = os.getenv("SEO_AUDITOR_CONTACT", "@Daniel_Lysenko33")

# Таймаут на Claude CLI (секунды)
CLAUDE_TIMEOUT = 120

# Макс количество аудитов в день на пользователя (0 = безлимит)
DAILY_LIMIT = 0
