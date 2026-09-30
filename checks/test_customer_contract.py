"""Additional acceptance checks: intentionally fail on v1.1.0-rc1."""
import unittest

from northstar.customers import import_customer


class CustomerCompatibilityTests(unittest.TestCase):
    def test_leading_zeros_are_preserved(self):
        customer = import_customer({"customer_id": "00123", "name": "Avery Chen"})
        self.assertEqual(customer["customer_id"], "00123")

    def test_partner_identifier_is_accepted(self):
        customer = import_customer({"customer_id": "abc-123", "name": "Jordan Lee"})
        self.assertEqual(customer["customer_id"], "abc-123")


if __name__ == "__main__":
    unittest.main()
