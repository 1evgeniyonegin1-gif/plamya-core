"""Тесты для SEO-анализатора.

Проверяем: форматирование отчётов, fallback-анализ, хелперы.
AI-вызовы НЕ тестируем (требуют Claude CLI) — только чистые функции.
"""

import pytest

from demos.seo_auditor_bot.seo_analyzer import (
    _score_bar,
    _score_emoji,
    fallback_report,
    format_report,
)
from demos.seo_auditor_bot.wb_parser import WBCard


@pytest.fixture
def good_card():
    """Карточка с хорошим SEO."""
    return WBCard(
        article=173295478,
        name="Платье женское летнее миди хлопок свободный крой повседневное",
        brand="TestBrand",
        category="Платья",
        description="Красивое летнее платье из натурального хлопка. " * 20,  # ~600 символов
        options=[{"name": f"Опция {i}", "value": f"Значение {i}"} for i in range(12)],
        photo_count=8,
        video_count=1,
        rating=4.7,
        feedbacks=150,
        price=350000,
        sale_price=250000,
    )


@pytest.fixture
def bad_card():
    """Карточка с плохим SEO."""
    return WBCard(
        article=12345678,
        name="Платье",
        brand="",
        category="Платья",
        description="Красивое",
        options=[{"name": "Цвет", "value": "Красный"}],
        photo_count=2,
        video_count=0,
        rating=3.1,
        feedbacks=3,
        price=100000,
        sale_price=80000,
    )


class TestScoreHelpers:
    """Хелперы оценки."""

    def test_score_emoji_good(self):
        assert _score_emoji("good") == "✅"

    def test_score_emoji_warning(self):
        assert _score_emoji("warning") == "⚠️"

    def test_score_emoji_bad(self):
        assert _score_emoji("bad") == "❌"

    def test_score_emoji_unknown(self):
        assert _score_emoji("xyz") == "❓"

    def test_score_bar_min(self):
        result = _score_bar(1)
        assert "1/10" in result
        assert "█" in result

    def test_score_bar_max(self):
        result = _score_bar(10)
        assert "10/10" in result
        assert "░" not in result

    def test_score_bar_mid(self):
        result = _score_bar(5)
        assert "5/10" in result
        assert "█████" in result
        assert "░░░░░" in result


class TestFallbackReport:
    """Fallback-отчёт (без AI)."""

    def test_bad_card_low_score(self, bad_card):
        report = fallback_report(bad_card)
        assert "SEO-аудит" in report
        assert "12345678" in report
        assert "❌" in report  # есть проблемы

    def test_bad_card_short_title(self, bad_card):
        report = fallback_report(bad_card)
        assert "Заголовок" in report

    def test_bad_card_short_description(self, bad_card):
        report = fallback_report(bad_card)
        assert "Описание" in report

    def test_bad_card_few_photos(self, bad_card):
        report = fallback_report(bad_card)
        assert "фото" in report.lower()

    def test_bad_card_no_video(self, bad_card):
        report = fallback_report(bad_card)
        assert "видео" in report.lower()

    def test_good_card_has_checkmarks(self, good_card):
        report = fallback_report(good_card)
        assert "✅" in report

    def test_good_card_higher_score(self, good_card):
        report = fallback_report(good_card)
        # Хорошая карточка не должна получить 1/10
        assert "1/10" not in report

    def test_score_clamped(self):
        """Оценка не уходит ниже 1."""
        terrible_card = WBCard(
            article=11111111,
            name="A",  # 1 символ
            description="",
            options=[],
            photo_count=0,
            video_count=0,
            rating=1.0,
            feedbacks=0,
        )
        report = fallback_report(terrible_card)
        assert "1/10" in report
        assert "0/10" not in report


class TestFormatReport:
    """AI-отчёт из JSON."""

    @pytest.fixture
    def sample_analysis(self):
        return {
            "score": 6,
            "title_analysis": {
                "length": 23,
                "score": "bad",
                "issue": "Слишком короткий",
                "fix": "Добавить ключевые слова",
            },
            "description_analysis": {
                "length": 15,
                "has_keywords": False,
                "score": "bad",
                "issue": "Нет ключей",
                "fix": "Переписать",
            },
            "options_analysis": {
                "filled": 3,
                "expected": 12,
                "score": "bad",
                "missing": ["Состав", "Страна"],
            },
            "media_analysis": {
                "photos": 3,
                "video": False,
                "score": "warning",
                "fix": "Добавить фото",
            },
            "reviews_analysis": {
                "count": 12,
                "rating": 4.2,
                "score": "warning",
                "note": "Мало отзывов",
            },
            "top_recommendations": [
                "Расширить заголовок",
                "Переписать описание",
                "Заполнить характеристики",
            ],
            "keywords_to_add": ["платье", "летнее", "хлопок"],
        }

    def test_contains_score(self, bad_card, sample_analysis):
        report = format_report(bad_card, sample_analysis)
        assert "6/10" in report

    def test_contains_title_analysis(self, bad_card, sample_analysis):
        report = format_report(bad_card, sample_analysis)
        assert "Заголовок" in report
        assert "Слишком короткий" in report

    def test_contains_recommendations(self, bad_card, sample_analysis):
        report = format_report(bad_card, sample_analysis)
        assert "Расширить заголовок" in report
        assert "Переписать описание" in report

    def test_contains_keywords(self, bad_card, sample_analysis):
        report = format_report(bad_card, sample_analysis)
        assert "платье" in report
        assert "хлопок" in report

    def test_contains_missing_options(self, bad_card, sample_analysis):
        report = format_report(bad_card, sample_analysis)
        assert "Состав" in report

    def test_contains_article(self, bad_card, sample_analysis):
        report = format_report(bad_card, sample_analysis)
        assert "12345678" in report

    def test_empty_analysis(self, bad_card):
        """Пустой JSON не должен крашить."""
        report = format_report(bad_card, {})
        assert "SEO-аудит" in report

    def test_partial_analysis(self, bad_card):
        """Частичный JSON — только то что есть."""
        report = format_report(bad_card, {"score": 3})
        assert "3/10" in report
