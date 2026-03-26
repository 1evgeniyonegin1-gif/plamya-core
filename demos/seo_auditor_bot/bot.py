"""Telegram-бот: AI SEO Аудитор карточек WB.

Пользователь отправляет ссылку на товар WB или артикул.
Бот парсит карточку, прогоняет через Claude AI, выдаёт SEO-отчёт
с оценкой, проблемами и конкретными рекомендациями.

Запуск: SEO_AUDITOR_BOT_TOKEN=xxx python -m demos.seo_auditor_bot
"""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from .config import BOT_TOKEN, CONTACT_TG
from .seo_analyzer import analyze_seo
from .wb_parser import WBCard, extract_wb_article, fetch_wb_card

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

router = Router()


def _main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📝 Заказать SEO-оптимизацию",
            url=f"https://t.me/{CONTACT_TG.lstrip('@')}",
        )],
        [InlineKeyboardButton(text="🔄 Проверить другой товар", callback_data="again")],
    ])


def _again_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить другой товар", callback_data="again")],
    ])


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🔍 <b>AI SEO Аудитор карточек WB</b>\n\n"
        "Отправь ссылку на товар или артикул — "
        "получишь аудит карточки с оценкой и рекомендациями.\n\n"
        "Что проверяю:\n"
        "• Заголовок — длина, ключевые слова\n"
        "• Описание — полнота, SEO\n"
        "• Характеристики — заполненность\n"
        "• Фото и видео\n"
        "• Отзывы и рейтинг\n\n"
        "Пример: <code>173295478</code>\n"
        "Или ссылку: wildberries.ru/catalog/173295478/...",
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Как пользоваться:</b>\n\n"
        "1. Отправь артикул WB (число) или ссылку на товар\n"
        "2. Подожди 20-40 секунд (AI анализирует)\n"
        "3. Получи отчёт с оценкой 1-10 и рекомендациями\n\n"
        "/start — начать\n"
        "/help — справка",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "again")
async def cb_again(callback: CallbackQuery):
    await callback.message.answer("Отправь артикул или ссылку на товар WB.")
    await callback.answer()


@router.message()
async def handle_message(message: Message):
    """Обработка артикула или ссылки на товар."""
    text = message.text or ""
    article = extract_wb_article(text)

    if not article:
        await message.answer(
            "Не нашёл артикул. Отправь число (5+ цифр) "
            "или ссылку на товар WB.\n\n"
            "Пример: <code>173295478</code>",
            parse_mode="HTML",
        )
        return

    # Шаг 1: Парсинг карточки
    status_msg = await message.answer(
        f"⏳ Ищу товар <b>{article}</b> на WB...",
        parse_mode="HTML",
    )

    card = await fetch_wb_card(article)

    if not card or not card.name:
        await status_msg.edit_text(
            f"❌ Товар {article} не найден на WB.\n"
            "Проверь артикул и попробуй ещё раз.",
            reply_markup=_again_kb(),
        )
        return

    # Показать что нашли, начать анализ
    price_text = ""
    if card.sale_price:
        price_text = f" | {card.sale_price // 100}₽"
    elif card.price:
        price_text = f" | {card.price // 100}₽"

    await status_msg.edit_text(
        f"📦 <b>{card.name[:80]}</b>\n"
        f"{card.brand or 'Без бренда'} | {card.category or '?'}{price_text}\n\n"
        f"🤖 Анализирую SEO... (20-40 сек)",
        parse_mode="HTML",
    )

    # Шаг 2: AI SEO-анализ
    report = await analyze_seo(card)

    # Шаг 3: Отправить отчёт
    if len(report) <= 4096:
        await status_msg.edit_text(
            report,
            reply_markup=_main_kb(),
        )
    else:
        # Длинный отчёт — разбить
        await status_msg.edit_text(
            f"📦 <b>{card.name[:80]}</b>\nАнализ готов ⬇️",
            parse_mode="HTML",
        )
        # Разбить на куски по 4000 символов
        chunks = []
        current = ""
        for line in report.split("\n"):
            if len(current) + len(line) + 1 > 4000:
                chunks.append(current)
                current = line
            else:
                current += "\n" + line if current else line
        if current:
            chunks.append(current)

        for i, chunk in enumerate(chunks):
            kb = _main_kb() if i == len(chunks) - 1 else None
            await message.answer(chunk, reply_markup=kb)


async def main():
    token = BOT_TOKEN
    if not token:
        print("Установи SEO_AUDITOR_BOT_TOKEN в переменных окружения")
        print("Получить токен: @BotFather в Telegram → /newbot")
        sys.exit(1)

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("SEO Auditor Bot starting...")
    await dp.start_polling(bot)
