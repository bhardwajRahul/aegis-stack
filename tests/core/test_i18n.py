"""
Tests for i18n locale normalization and message completeness.

Verifies that locale detection, normalization, and message catalogs
work correctly across all supported languages.
"""

from aegis.i18n.locales import AVAILABLE_LOCALES
from aegis.i18n.locales.en import MESSAGES as EN_MESSAGES
from aegis.i18n.registry import _normalize_locale


class TestLocaleNormalization:
    """Test locale string normalization."""

    def test_english_variants(self) -> None:
        """English locale variants all normalize to 'en'."""
        assert _normalize_locale("en") == "en"
        assert _normalize_locale("en_US") == "en"
        assert _normalize_locale("en-GB") == "en"
        assert _normalize_locale("en_US.UTF-8") == "en"
        assert _normalize_locale("en.UTF-8") == "en"

    def test_simplified_chinese_variants(self) -> None:
        """Simplified Chinese variants all normalize to 'zh'."""
        assert _normalize_locale("zh") == "zh"
        assert _normalize_locale("zh_CN") == "zh"
        assert _normalize_locale("zh-Hans") == "zh"
        assert _normalize_locale("zh_CN.UTF-8") == "zh"

    def test_traditional_chinese_variants(self) -> None:
        """Traditional Chinese variants all normalize to 'zh_Hant'."""
        assert _normalize_locale("zh_TW") == "zh_Hant"
        assert _normalize_locale("zh_HK") == "zh_Hant"
        assert _normalize_locale("zh-Hant") == "zh_Hant"
        assert _normalize_locale("zh_MO") == "zh_Hant"
        assert _normalize_locale("zh_TW.UTF-8") == "zh_Hant"
        assert _normalize_locale("zh_HK.UTF-8") == "zh_Hant"

    def test_japanese_variants(self) -> None:
        """Japanese locale variants normalize to 'ja'."""
        assert _normalize_locale("ja") == "ja"
        assert _normalize_locale("ja_JP") == "ja"
        assert _normalize_locale("ja_JP.UTF-8") == "ja"
        assert _normalize_locale("ja-JP") == "ja"

    def test_korean_variants(self) -> None:
        """Korean locale variants normalize to 'ko'."""
        assert _normalize_locale("ko") == "ko"
        assert _normalize_locale("ko_KR") == "ko"
        assert _normalize_locale("ko_KR.UTF-8") == "ko"
        assert _normalize_locale("ko-KR") == "ko"

    def test_unsupported_falls_back_to_english(self) -> None:
        """Unsupported locales fall back to 'en'."""
        assert _normalize_locale("fr") == "en"
        assert _normalize_locale("de_DE") == "en"
        assert _normalize_locale("xx") == "en"
        assert _normalize_locale("es_MX.UTF-8") == "en"

    def test_encoding_and_modifier_stripped(self) -> None:
        """Encoding suffixes and modifiers are stripped."""
        assert _normalize_locale("ja_JP.EUC-JP") == "ja"
        assert _normalize_locale("zh_TW.Big5") == "zh_Hant"
        assert _normalize_locale("en_US.UTF-8@euro") == "en"


class TestMessageCompleteness:
    """Test that all locale catalogs have the same keys as English."""

    def test_all_locales_registered(self) -> None:
        """All expected locales are in AVAILABLE_LOCALES."""
        assert "en" in AVAILABLE_LOCALES
        assert "zh" in AVAILABLE_LOCALES
        assert "zh_Hant" in AVAILABLE_LOCALES
        assert "ja" in AVAILABLE_LOCALES
        assert "ko" in AVAILABLE_LOCALES

    def test_zh_has_all_keys(self) -> None:
        """Simplified Chinese has all English keys."""
        from aegis.i18n.locales.zh import MESSAGES as ZH

        missing = set(EN_MESSAGES) - set(ZH)
        extra = set(ZH) - set(EN_MESSAGES)
        assert not missing, f"Keys in en but not zh: {missing}"
        assert not extra, f"Keys in zh but not en: {extra}"

    def test_zh_hant_has_all_keys(self) -> None:
        """Traditional Chinese has all English keys."""
        from aegis.i18n.locales.zh_hant import MESSAGES as ZH_HANT

        missing = set(EN_MESSAGES) - set(ZH_HANT)
        extra = set(ZH_HANT) - set(EN_MESSAGES)
        assert not missing, f"Keys in en but not zh_Hant: {missing}"
        assert not extra, f"Keys in zh_Hant but not en: {extra}"

    def test_ja_has_all_keys(self) -> None:
        """Japanese has all English keys."""
        from aegis.i18n.locales.ja import MESSAGES as JA

        missing = set(EN_MESSAGES) - set(JA)
        extra = set(JA) - set(EN_MESSAGES)
        assert not missing, f"Keys in en but not ja: {missing}"
        assert not extra, f"Keys in ja but not en: {extra}"

    def test_ko_has_all_keys(self) -> None:
        """Korean has all English keys."""
        from aegis.i18n.locales.ko import MESSAGES as KO

        missing = set(EN_MESSAGES) - set(KO)
        extra = set(KO) - set(EN_MESSAGES)
        assert not missing, f"Keys in en but not ko: {missing}"
        assert not extra, f"Keys in ko but not en: {extra}"

    def test_no_empty_values(self) -> None:
        """No locale has empty string values."""
        from aegis.i18n.locales.ja import MESSAGES as JA
        from aegis.i18n.locales.ko import MESSAGES as KO
        from aegis.i18n.locales.zh import MESSAGES as ZH
        from aegis.i18n.locales.zh_hant import MESSAGES as ZH_HANT

        for name, messages in [
            ("zh", ZH),
            ("zh_Hant", ZH_HANT),
            ("ja", JA),
            ("ko", KO),
        ]:
            empty = [k for k, v in messages.items() if not v.strip()]
            assert not empty, f"{name} has empty values: {empty}"
