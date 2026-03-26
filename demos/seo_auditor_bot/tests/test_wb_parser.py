"""Тесты для WB-парсера SEO Аудитора.

Проверяем: извлечение артикулов, определение basket host,
парсинг card.json, форматирование данных.
"""

import pytest

from demos.seo_auditor_bot.wb_parser import (
    WBCard,
    _get_basket_host,
    _parse_card_data,
    extract_wb_article,
)


class TestExtractWBArticle:
    """Извлечение артикула из текста/ссылки."""

    def test_plain_number(self):
        assert extract_wb_article("173295478") == 173295478

    def test_number_with_spaces(self):
        assert extract_wb_article("  173295478  ") == 173295478

    def test_wb_url_catalog(self):
        url = "https://www.wildberries.ru/catalog/173295478/detail.aspx"
        assert extract_wb_article(url) == 173295478

    def test_wb_url_short(self):
        url = "wildberries.ru/catalog/286845068"
        assert extract_wb_article(url) == 286845068

    def test_text_with_number(self):
        assert extract_wb_article("артикул 12345678 товара") == 12345678

    def test_short_number_rejected(self):
        """Числа меньше 5 цифр не считаются артикулами."""
        assert extract_wb_article("1234") is None

    def test_no_number(self):
        assert extract_wb_article("hello world") is None

    def test_empty_string(self):
        assert extract_wb_article("") is None

    def test_url_with_query_params(self):
        url = "https://www.wildberries.ru/catalog/173295478/detail.aspx?targetUrl=GP"
        assert extract_wb_article(url) == 173295478


class TestGetBasketHost:
    """Определение basket host по артикулу."""

    def test_low_article(self):
        # vol = 100025 // 100000 = 1, <= 143 → basket-01
        assert _get_basket_host(100025) == "basket-01"

    def test_mid_article(self):
        # vol = 50000000 // 100000 = 500, <= 719 → basket-04
        assert _get_basket_host(50000000) == "basket-04"

    def test_high_article(self):
        # vol = 300000000 // 100000 = 3000, > 2837 → basket-18
        assert _get_basket_host(300000000) == "basket-18"

    def test_boundary_143(self):
        # vol = 14300000 // 100000 = 143, <= 143 → basket-01
        assert _get_basket_host(14300000) == "basket-01"

    def test_boundary_144(self):
        # vol = 14400000 // 100000 = 144, <= 287 → basket-02
        assert _get_basket_host(14400000) == "basket-02"


class TestParseCardData:
    """Парсинг card.json ответа."""

    @pytest.fixture
    def sample_card_json(self):
        return {
            "imt_name": "Платье женское летнее миди",
            "selling": {"brand_name": "TestBrand"},
            "subj_name": "Платья",
            "subj_root_name": "Одежда",
            "description": "Красивое летнее платье из хлопка. Свободный крой.",
            "options": [
                {"name": "Цвет", "value": "Красный"},
                {"name": "Размер", "value": "S, M, L"},
                {"name": "Материал", "value": "Хлопок 100%"},
            ],
            "colors": [{"name": "Красный"}, {"name": "Синий"}],
            "compositions": [{"name": "Хлопок"}],
            "media": {"photo_count": 5, "video": "https://video.url"},
            "imt_id": 99999,
            "nm_id": 173295478,
        }

    def test_basic_fields(self, sample_card_json):
        card = _parse_card_data(sample_card_json, 173295478)
        assert card.article == 173295478
        assert card.name == "Платье женское летнее миди"
        assert card.brand == "TestBrand"
        assert card.category == "Платья"

    def test_description(self, sample_card_json):
        card = _parse_card_data(sample_card_json, 173295478)
        assert "хлопка" in card.description

    def test_options_parsed(self, sample_card_json):
        card = _parse_card_data(sample_card_json, 173295478)
        assert len(card.options) == 3
        assert card.options[0] == {"name": "Цвет", "value": "Красный"}

    def test_colors_parsed(self, sample_card_json):
        card = _parse_card_data(sample_card_json, 173295478)
        assert card.colors == ["Красный", "Синий"]

    def test_media_counts(self, sample_card_json):
        card = _parse_card_data(sample_card_json, 173295478)
        assert card.photo_count == 5
        assert card.video_count == 1

    def test_empty_card(self):
        card = _parse_card_data({}, 12345678)
        assert card.article == 12345678
        assert card.name == ""
        assert card.brand == ""
        assert card.photo_count == 0
        assert card.video_count == 0
        assert card.options == []

    def test_missing_media(self):
        data = {"imt_name": "Test", "media": {}}
        card = _parse_card_data(data, 12345678)
        assert card.photo_count == 0
        assert card.video_count == 0


class TestWBCard:
    """Dataclass WBCard — корректность дефолтов."""

    def test_defaults(self):
        card = WBCard()
        assert card.article == 0
        assert card.name == ""
        assert card.options == []
        assert card.colors == []
        assert card.photo_count == 0
        assert card.rating == 0.0
        assert card.feedbacks == 0
        assert card.price == 0
        assert card.sale_price == 0
