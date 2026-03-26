"""Запуск SEO Аудитор бота.

python -m demos.seo_auditor_bot
"""

import asyncio

from .bot import main

asyncio.run(main())
