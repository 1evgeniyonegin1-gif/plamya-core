"""SEO-анализ карточки WB через Claude CLI.

Получает WBCard, формирует промпт, отправляет в Claude,
парсит результат и форматирует для Telegram.
"""

import asyncio
import json
import logging
import os
import shutil

from .wb_parser import WBCard

logger = logging.getLogger(__name__)


async def _call_claude(prompt: str, timeout: int = 120) -> str:
    """Вызвать Claude через CLI."""
    claude_path = shutil.which("claude") or shutil.which("claude.cmd")
    if not claude_path:
        logger.error("claude CLI not found in PATH")
        return ""

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        proc = await asyncio.create_subprocess_exec(
            claude_path, "-p", prompt, "--max-turns", "1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        result = stdout.decode("utf-8", errors="replace").strip()
        if not result:
            logger.warning(f"Claude empty response. stderr: {stderr.decode('utf-8', errors='replace')[:200]}")
        return result
    except asyncio.TimeoutError:
        logger.error(f"Claude call timed out ({timeout}s)")
        proc.kill()
        return ""
    except Exception as e:
        logger.error(f"Claude call error: {e}")
        return ""


def _build_prompt(card: WBCard) -> str:
    """Сформировать промпт для SEO-анализа."""
    # Характеристики
    options_text = ""
    if card.options:
        options_lines = [f"  - {o['name']}: {o['value']}" for o in card.options]
        options_text = "\n".join(options_lines)
    else:
        options_text = "  (не заполнены)"

    # Цена
    price_text = ""
    if card.sale_price:
        price_text = f"{card.sale_price // 100} руб."
        if card.price and card.price != card.sale_price:
            price_text += f" (без скидки: {card.price // 100} руб.)"
    elif card.price:
        price_text = f"{card.price // 100} руб."

    return f"""Ты — SEO-эксперт по маркетплейсам WB и Ozon. Проведи аудит карточки товара Wildberries.

ДАННЫЕ КАРТОЧКИ:
- Артикул: {card.article}
- Название: {card.name}
- Бренд: {card.brand}
- Категория: {card.category}
- Цена: {price_text or 'не указана'}
- Описание: {card.description[:500] if card.description else '(пусто)'}
- Характеристики:
{options_text}
- Фото: {card.photo_count} шт.
- Видео: {'есть' if card.video_count else 'нет'}
- Рейтинг: {card.rating} | Отзывов: {card.feedbacks}

ЗАДАЧА: Проведи SEO-аудит и выдай ответ СТРОГО в таком JSON-формате (без markdown, без ```):
{{
  "score": 7,
  "title_analysis": {{
    "length": 45,
    "score": "bad",
    "issue": "Слишком короткий, нет ключевых слов",
    "fix": "Добавить: ключевое1, ключевое2, ключевое3"
  }},
  "description_analysis": {{
    "length": 120,
    "has_keywords": false,
    "score": "bad",
    "issue": "Нет ключевых слов, слишком короткое",
    "fix": "Переписать с ключами, расширить до 500+ символов"
  }},
  "options_analysis": {{
    "filled": 5,
    "expected": 12,
    "score": "warning",
    "missing": ["Состав", "Страна производства", "Сезон"]
  }},
  "media_analysis": {{
    "photos": 3,
    "video": false,
    "score": "warning",
    "fix": "Добавить фото до 7+, снять видеообзор"
  }},
  "reviews_analysis": {{
    "count": 12,
    "rating": 4.2,
    "score": "warning",
    "note": "Мало отзывов для конкурентной ниши"
  }},
  "top_recommendations": [
    "Конкретная рекомендация 1",
    "Конкретная рекомендация 2",
    "Конкретная рекомендация 3"
  ],
  "keywords_to_add": ["ключ1", "ключ2", "ключ3", "ключ4", "ключ5"]
}}

Правила оценки score (1-10):
- Название: 60-120 символов с ключевыми словами = good. <40 или >200 = bad
- Описание: 500+ символов с ключами = good. <200 или без ключей = bad
- Характеристики: 80%+ заполнено = good. <50% = bad
- Фото: 7+ = good. <4 = bad. Видео = бонус
- Отзывы: 50+ = good. <20 = warning. <5 = bad

Общий score = среднее всех параметров. Будь строгим — не завышай.
Отвечай ТОЛЬКО JSON, без пояснений."""


def _score_emoji(score: str) -> str:
    """Эмодзи для оценки."""
    return {"good": "✅", "warning": "⚠️", "bad": "❌"}.get(score, "❓")


def _score_bar(score: int) -> str:
    """Визуальная шкала 1-10."""
    filled = "█" * score
    empty = "░" * (10 - score)
    return f"{filled}{empty} {score}/10"


def format_report(card: WBCard, analysis: dict) -> str:
    """Форматировать JSON-анализ в красивый Telegram-отчёт."""
    score = analysis.get("score", 5)
    title = analysis.get("title_analysis", {})
    desc = analysis.get("description_analysis", {})
    opts = analysis.get("options_analysis", {})
    media = analysis.get("media_analysis", {})
    reviews = analysis.get("reviews_analysis", {})
    recs = analysis.get("top_recommendations", [])
    keywords = analysis.get("keywords_to_add", [])

    lines = [
        f"🔍 SEO-аудит: {card.name[:60]}",
        f"Артикул: {card.article}" + (f" | {card.brand}" if card.brand else ""),
        "",
        f"📊 Общая оценка: {_score_bar(score)}",
        "",
    ]

    # Заголовок
    t_emoji = _score_emoji(title.get("score", "warning"))
    t_len = title.get("length", len(card.name))
    lines.append(f"{t_emoji} Заголовок ({t_len} симв.)")
    if title.get("issue"):
        lines.append(f"   {title['issue']}")
    if title.get("fix"):
        lines.append(f"   → {title['fix']}")
    lines.append("")

    # Описание
    d_emoji = _score_emoji(desc.get("score", "warning"))
    d_len = desc.get("length", len(card.description))
    lines.append(f"{d_emoji} Описание ({d_len} симв.)")
    if desc.get("issue"):
        lines.append(f"   {desc['issue']}")
    if desc.get("fix"):
        lines.append(f"   → {desc['fix']}")
    lines.append("")

    # Характеристики
    o_emoji = _score_emoji(opts.get("score", "warning"))
    o_filled = opts.get("filled", len(card.options))
    o_expected = opts.get("expected", o_filled + 3)
    lines.append(f"{o_emoji} Характеристики ({o_filled}/{o_expected})")
    missing = opts.get("missing", [])
    if missing:
        lines.append(f"   Не заполнено: {', '.join(missing[:5])}")
    lines.append("")

    # Медиа
    m_emoji = _score_emoji(media.get("score", "warning"))
    lines.append(f"{m_emoji} Фото: {card.photo_count} | Видео: {'да' if card.video_count else 'нет'}")
    if media.get("fix"):
        lines.append(f"   → {media['fix']}")
    lines.append("")

    # Отзывы
    r_emoji = _score_emoji(reviews.get("score", "warning"))
    lines.append(f"{r_emoji} Отзывы: {card.feedbacks} | Рейтинг: {card.rating}")
    if reviews.get("note"):
        lines.append(f"   {reviews['note']}")
    lines.append("")

    # Рекомендации
    if recs:
        lines.append("💡 ТОП рекомендации:")
        for i, rec in enumerate(recs[:5], 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")

    # Ключевые слова
    if keywords:
        lines.append(f"🔑 Добавить в карточку: {', '.join(keywords[:7])}")
        lines.append("")

    return "\n".join(lines)


def fallback_report(card: WBCard) -> str:
    """Простой отчёт без AI — когда Claude недоступен."""
    score = 5
    issues = []
    good = []

    # Заголовок
    name_len = len(card.name)
    if name_len < 40:
        issues.append(f"❌ Заголовок слишком короткий ({name_len} симв., нужно 60-120)")
        score -= 1
    elif name_len > 200:
        issues.append(f"⚠️ Заголовок слишком длинный ({name_len} симв.)")
    else:
        good.append(f"✅ Заголовок: {name_len} симв.")

    # Описание
    desc_len = len(card.description)
    if desc_len < 100:
        issues.append(f"❌ Описание {'пустое' if desc_len == 0 else f'слишком короткое ({desc_len} симв.)'}")
        score -= 2
    elif desc_len < 500:
        issues.append(f"⚠️ Описание короткое ({desc_len} симв., рекомендуется 500+)")
        score -= 1
    else:
        good.append(f"✅ Описание: {desc_len} симв.")

    # Характеристики
    opt_count = len(card.options)
    if opt_count < 5:
        issues.append(f"❌ Мало характеристик ({opt_count}, нужно 10+)")
        score -= 1
    elif opt_count < 10:
        issues.append(f"⚠️ Характеристики: {opt_count} (рекомендуется 10+)")
    else:
        good.append(f"✅ Характеристики: {opt_count}")

    # Фото
    if card.photo_count < 4:
        issues.append(f"❌ Мало фото ({card.photo_count}, нужно 7+)")
        score -= 1
    elif card.photo_count < 7:
        issues.append(f"⚠️ Фото: {card.photo_count} (рекомендуется 7+)")
    else:
        good.append(f"✅ Фото: {card.photo_count}")

    if not card.video_count:
        issues.append("⚠️ Нет видео (видеообзор повышает конверсию)")

    # Отзывы
    if card.feedbacks < 5:
        issues.append(f"❌ Мало отзывов ({card.feedbacks})")
        score -= 1
    elif card.feedbacks < 50:
        issues.append(f"⚠️ Отзывов: {card.feedbacks} (для ТОП нужно 50+)")
    else:
        good.append(f"✅ Отзывов: {card.feedbacks}")

    score = max(1, min(10, score))

    lines = [
        f"🔍 SEO-аудит: {card.name[:60]}",
        f"Артикул: {card.article}",
        "",
        f"📊 Общая оценка: {_score_bar(score)}",
        "",
    ]

    if good:
        lines.extend(good)
        lines.append("")
    if issues:
        lines.extend(issues)
        lines.append("")

    lines.append("⚠️ Базовый аудит (AI-анализ временно недоступен)")
    return "\n".join(lines)


async def analyze_seo(card: WBCard) -> str:
    """Провести SEO-аудит карточки WB. Возвращает отформатированный отчёт."""
    prompt = _build_prompt(card)
    raw = await _call_claude(prompt)

    if not raw:
        logger.warning("Claude returned empty, using fallback")
        return fallback_report(card)

    # Попробуем извлечь JSON из ответа
    try:
        # Claude может обернуть в ```json ... ```
        json_text = raw
        if "```" in json_text:
            # Извлечь содержимое между ``` и ```
            import re
            match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", json_text, re.DOTALL)
            if match:
                json_text = match.group(1)

        # Попробуем найти JSON-объект
        start = json_text.find("{")
        end = json_text.rfind("}") + 1
        if start >= 0 and end > start:
            json_text = json_text[start:end]

        analysis = json.loads(json_text)
        return format_report(card, analysis)

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Failed to parse Claude JSON: {e}")
        # Если JSON не распарсился, попробуем отдать raw текст
        if len(raw) > 100:
            # Claude ответил текстом вместо JSON — тоже нормально
            header = (
                f"🔍 SEO-аудит: {card.name[:60]}\n"
                f"Артикул: {card.article}\n\n"
            )
            return header + raw[:3500]  # лимит Telegram

        return fallback_report(card)
