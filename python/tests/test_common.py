import unittest

from controls_pack.common import flag, number, unique


class ValidationTests(unittest.TestCase):
    def test_numbers_and_flags(self):
        self.assertEqual(number("12.5", "amount"), 12.5)
        self.assertFalse(flag("False", "secured"))
        for invalid in ["nan", "inf", -1, True]:
            with self.assertRaises(ValueError):
                number(invalid, "amount", 0)

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError):
            unique([{"id": "a"}, {"id": "a"}], ["id"])
