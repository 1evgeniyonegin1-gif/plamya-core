"""Парсинг карточки WB для SEO-аудита.

Используем открытые API WB (без токена продавца):
- basket API: card.json — название, описание, характеристики, фото
- feedbacks API: рейтинг, количество отзывов
- search API: позиция в выдаче по ключевым словам
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field

import aiohttp

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


@dataclass
class WBCard:
    """Данные карточки WB для SEO-аудита."""

    article: int = 0
    name: str = ""
    brand: str = ""
    category: str = ""
    description: str = ""
    options: list[dict] = field(default_factory=list)  # характеристики [{name, value}]
    colors: list[str] = field(default_factory=list)
    photo_count: int = 0
    video_count: int = 0
    rating: float = 0.0
    feedbacks: int = 0
    price: int = 0  # копейки
    sale_price: int = 0  # со скидкой
    compositions: list[str] = field(default_factory=list)  # составы


def _get_basket_host(article: int) -> str:
    """Определить basket host по артикулу WB."""
    vol = article // 100000
    ranges = [
        (143, "01"), (287, "02"), (431, "03"), (719, "04"),
        (1007, "05"), (1061, "06"), (1115, "07"), (1169, "08"),
        (1313, "09"), (1601, "10"), (1655, "11"), (1919, "12"),
        (2045, "13"), (2189, "14"), (2405, "15"), (2621, "16"),
        (2837, "17"),
    ]
    for threshold, num in ranges:
        if vol <= threshold:
            return f"basket-{num}"
    return "basket-18"


async def _fetch_card_json(session: aiohttp.ClientSession, article: int) -> dict | None:
    """Получить card.json из basket API."""
    vol = article // 100000
    part = article // 1000
    host = _get_basket_host(article)

    # Основной хост
    url = f"https://{host}.wbbasket.ru/vol{vol}/part{part}/{article}/info/ru/card.json"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return await resp.json(content_type=None)
    except Exception:
        pass

    # Перебор хостов
    for h in range(1, 19):
        alt_host = f"basket-{h:02d}"
        if alt_host == host:
            continue
        alt_url = f"https://{alt_host}.wbbasket.ru/vol{vol}/part{part}/{article}/info/ru/card.json"
        try:
            async with session.get(alt_url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    return await resp.json(content_type=None)
        except Exception:
            continue

    return None


async def _fetch_detail_json(session: aiohttp.ClientSession, article: int) -> dict | None:
    """Получить detail.json — цены, рейтинг, отзывы."""
    vol = article // 100000
    part = article // 1000
    host = _get_basket_host(article)

    url = f"https://{host}.wbbasket.ru/vol{vol}/part{part}/{article}/info/price-history.json"
    # Альтернативный endpoint для деталей
    detail_url = f"https://card.wb.ru/cards/v2/detail?appType=1&curr=rub&dest=-1257786&nm={article}"
    try:
        async with session.get(detail_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                products = data.get("data", {}).get("products", [])
                if products:
                    return products[0]
    except Exception as e:
        logger.debug(f"Detail fetch error: {e}")

    return None


async def _fetch_feedbacks_stats(session: aiohttp.ClientSession, article: int) -> dict:
    """Статистика отзывов (рейтинг, количество)."""
    try:
        url = f"https://feedbacks1.wb.ru/feedbacks/v2/{article}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                return {
                    "rating": data.get("valuation", 0),
                    "feedbacks": data.get("feedbackCount", 0),
                }
    except Exception as e:
        logger.debug(f"Feedbacks stats error: {e}")
    return {"rating": 0, "feedbacks": 0}


def _parse_card_data(data: dict, article: int) -> WBCard:
    """Парсинг card.json в WBCard."""
    card = WBCard(article=article)
    card.name = data.get("imt_name", "")
    card.brand = data.get("selling", {}).get("brand_name", "")
    card.category = data.get("subj_name", "") or data.get("subj_root_name", "")
    card.description = data.get("description", "")

    # Характеристики
    options_raw = data.get("options", [])
    for opt in options_raw:
        name = opt.get("name", "")
        value = opt.get("value", "")
        if name and value:
            card.options.append({"name": name, "value": value})

    # Цвета
    colors = data.get("colors", [])
    for c in colors:
        name = c.get("name", "")
        if name:
            card.colors.append(name)

    # Составы
    compositions = data.get("compositions", [])
    for comp in compositions:
        name = comp.get("name", "")
        if name:
            card.compositions.append(name)

    # Фото — считаем из media
    media = data.get("media", {})
    photo_count = media.get("photo_count", 0)
    if not photo_count:
        # Пробуем посчитать из photos
        photos = media.get("photos", [])
        photo_count = len(photos) if photos else 0
    card.photo_count = photo_count

    video_url = media.get("video", "")
    card.video_count = 1 if video_url else 0

    return card


async def fetch_wb_card(article: int) -> WBCard | None:
    """Получить полные данные карточки WB для SEO-аудита."""
    async with aiohttp.ClientSession(headers=_HEADERS) as session:
        # Параллельно: card.json + feedbacks + detail
        card_task = _fetch_card_json(session, article)
        fb_task = _fetch_feedbacks_stats(session, article)
        detail_task = _fetch_detail_json(session, article)

        card_data, fb_stats, detail = await asyncio.gather(
            card_task, fb_task, detail_task, return_exceptions=True
        )

        if isinstance(card_data, Exception) or card_data is None:
            logger.error(f"Card not found for article {article}")
            return None

        card = _parse_card_data(card_data, article)

        # Отзывы
        if isinstance(fb_stats, dict):
            card.rating = fb_stats.get("rating", 0)
            card.feedbacks = fb_stats.get("feedbacks", 0)

        # Цена из detail
        if isinstance(detail, dict):
            sizes = detail.get("sizes", [])
            if sizes:
                price_info = sizes[0].get("price", {})
                card.price = price_info.get("basic", 0)
                card.sale_price = price_info.get("total", 0)
            if not card.rating:
                card.rating = detail.get("reviewRating", 0)
            if not card.feedbacks:
                card.feedbacks = detail.get("feedbacks", 0)

        return card


def extract_wb_article(text: str) -> int | None:
    """Извлечь артикул WB из текста или ссылки."""
    text = text.strip()

    # WB URL: wildberries.ru/catalog/12345678/detail.aspx
    wb_match = re.search(r"wildberries\.ru/catalog/(\d+)", text)
    if wb_match:
        return int(wb_match.group(1))

    # Просто число (5+ цифр)
    num_match = re.search(r"(\d{5,})", text)
    if num_match:
        return int(num_match.group(1))

    return None
