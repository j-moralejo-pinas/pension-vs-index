"""Tests for visualization label helpers."""

from pension_vs_index.visualization import (
    format_extraction_rate_label,
    format_salary_extraction_chart_name,
)


def test_format_extraction_rate_label_uses_compact_spanish_percentages() -> None:
    """Extraction rates use compact labels without rounding away decimals."""
    assert format_extraction_rate_label(None) == "total"
    assert format_extraction_rate_label(0.04) == "4%"
    assert format_extraction_rate_label(0.068) == "6,8%"


def test_format_salary_extraction_chart_name_describes_salary_and_extraction() -> None:
    """Chart names include salary before retirement, salary after retirement, and extraction."""
    expected_name = (
        "Salario antes del retiro 61k · salario después del retiro 18,5k · extracción 6,8%"
    )

    assert (
        format_salary_extraction_chart_name(
            salary_before_retirement=61_000,
            salary_after_retirement=18_500,
            withdrawal_rate=0.068,
        )
        == expected_name
    )
