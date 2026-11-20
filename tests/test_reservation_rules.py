import unittest

from dante_squash.domain import BusinessRuleError, Reservation, validate_sauna_name


class ReservationRuleTests(unittest.TestCase):
    def test_game_can_have_multiple_distinct_customers(self) -> None:
        reservation = Reservation(
            weekday=1,
            time="18:00",
            court=1,
            is_game=True,
            customer_ids=(2, 5),
        )

        reservation.validate()

    def test_lesson_requires_exactly_one_customer(self) -> None:
        reservation = Reservation(
            weekday=2,
            time="10:00",
            court=2,
            is_game=False,
            customer_ids=(2, 5),
        )

        with self.assertRaises(BusinessRuleError):
            reservation.validate()

    def test_duplicate_customer_is_rejected(self) -> None:
        reservation = Reservation(
            weekday=1,
            time="18:00",
            court=1,
            is_game=True,
            customer_ids=(2, 2),
        )

        with self.assertRaises(BusinessRuleError):
            reservation.validate()

    def test_only_legacy_schedule_slots_and_registered_customers_are_allowed(self) -> None:
        reservation = Reservation(
            weekday=1,
            time="23:59",
            court=1,
            is_game=True,
            customer_ids=(2,),
        )

        with self.assertRaises(BusinessRuleError):
            reservation.validate()

        reservation = Reservation(
            weekday=1,
            time="18:00",
            court=1,
            is_game=True,
            customer_ids=(0,),
        )
        with self.assertRaises(BusinessRuleError):
            reservation.validate()

    def test_sauna_name_is_required_and_unique_without_case_sensitivity(self) -> None:
        with self.assertRaises(BusinessRuleError):
            validate_sauna_name("   ", ())
        with self.assertRaises(BusinessRuleError):
            validate_sauna_name("carla", ("Carla",))

        validate_sauna_name("Daniel", ("Carla",))


if __name__ == "__main__":
    unittest.main()
