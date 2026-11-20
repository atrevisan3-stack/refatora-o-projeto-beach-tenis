import unittest

from dante_squash.infrastructure.postgres import _legacy_month_year


class LegacyDateCompatibilityTests(unittest.TestCase):
    def test_eight_digit_date_uses_the_legacy_zero_based_month(self) -> None:
        self.assertEqual(_legacy_month_year(12032026), (2, 2026))

    def test_single_digit_day_retains_the_legacy_seven_digit_parsing_defect(self) -> None:
        self.assertEqual(_legacy_month_year(5032026), (31, 26))


if __name__ == "__main__":
    unittest.main()
