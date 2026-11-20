from decimal import Decimal
import unittest

from dante_squash.domain import calculate_payment


class PaymentRuleTests(unittest.TestCase):
    def test_partial_payment_creates_positive_open_balance(self) -> None:
        result = calculate_payment(
            total_due=Decimal("100.00"),
            amount_paid=Decimal("60.00"),
            discount=Decimal("0.00"),
        )

        self.assertFalse(result.paid_in_full)
        self.assertEqual(result.balance, Decimal("40.00"))

    def test_discount_is_recorded_as_negative_paid_entry(self) -> None:
        result = calculate_payment(
            total_due=Decimal("100.00"),
            amount_paid=Decimal("90.00"),
            discount=Decimal("10.00"),
        )

        self.assertTrue(result.paid_in_full)
        self.assertEqual(result.discount_entry, Decimal("-10.00"))
        self.assertEqual(result.balance, Decimal("0.00"))

    def test_overpayment_preserves_negative_balance_as_credit(self) -> None:
        result = calculate_payment(
            total_due=Decimal("100.00"),
            amount_paid=Decimal("110.00"),
            discount=Decimal("0.00"),
        )

        self.assertEqual(result.balance, Decimal("-10.00"))

    def test_float_precision_behavior_is_preserved_for_payment_comparison(self) -> None:
        result = calculate_payment(
            total_due=Decimal("0.30000000000000004"),
            amount_paid=Decimal("0.30"),
            discount=Decimal("0"),
        )

        self.assertFalse(result.paid_in_full)
        self.assertGreater(result.balance, Decimal("0"))

    def test_nan_payment_passes_the_legacy_positive_value_check(self) -> None:
        result = calculate_payment(
            total_due=Decimal("10.00"),
            amount_paid=Decimal("NaN"),
            discount=Decimal("0"),
        )

        self.assertFalse(result.paid_in_full)
        self.assertTrue(result.balance.is_nan())


if __name__ == "__main__":
    unittest.main()
