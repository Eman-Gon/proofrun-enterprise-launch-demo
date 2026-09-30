"""Feature acceptance tests for the sales team's numeric sample CSV files."""

import unittest

from northstar.preview import MAX_ROWS, preview_import


class BulkPreviewTests(unittest.TestCase):
    def test_multiple_customers_are_ready(self):
        result = preview_import({"csv": "customer_id,name\n123,Aster Labs\n456,Harbor Works\n"})
        self.assertEqual((result["total"], result["ready"], result["rejected"]), (2, 2, 0))
        self.assertEqual(result["rows"], [
            {"row": 2, "status": "ready", "customer": {"customer_id": "123", "name": "Aster Labs"}},
            {"row": 3, "status": "ready", "customer": {"customer_id": "456", "name": "Harbor Works"}},
        ])

    def test_duplicates_are_rejected_after_the_first_row(self):
        result = preview_import({"csv": "customer_id,name\n123,Aster\n123,Repeated\n"})
        self.assertEqual((result["ready"], result["rejected"]), (1, 1))
        self.assertEqual(result["rows"][1], {"row": 3, "status": "rejected", "error": "duplicate_id"})

    def test_invalid_rows_do_not_block_valid_rows(self):
        result = preview_import({"csv": "customer_id,name\n,Missing ID\n123,\n456,Valid customer\n"})
        self.assertEqual((result["total"], result["ready"], result["rejected"]), (3, 1, 2))
        self.assertEqual([row["error"] for row in result["rows"][:2]], ["invalid_customer"] * 2)
        self.assertEqual(result["rows"][2]["customer"]["customer_id"], "456")

    def test_quoted_names_remain_intact(self):
        result = preview_import({"csv": 'customer_id,name\r\n123,"Aster, Inc."\r\n'})
        self.assertEqual(result["rows"][0]["customer"]["name"], "Aster, Inc.")

    def test_rejected_row_does_not_reserve_its_customer_id(self):
        result = preview_import({"csv": "customer_id,name\n123,\n123,Aster\n"})
        self.assertEqual(result["rows"][1]["status"], "ready")

    def test_extra_values_are_invalid_customer_rows(self):
        result = preview_import({"csv": "customer_id,name\n123,Aster,extra\n456,Harbor\n"})
        self.assertEqual(result["rows"][0]["error"], "invalid_customer")
        self.assertEqual(result["ready"], 1)

    def test_empty_and_bad_headers_are_invalid_csv(self):
        for source in ("", "customer_id,name\n", "id,name\n123,Aster", "name,customer_id\nAster,123"):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "^invalid_csv$"):
                preview_import({"csv": source})

    def test_malformed_csv_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "^invalid_csv$"):
            preview_import({"csv": 'customer_id,name\n123,"unterminated'})

    def test_non_csv_payloads_are_rejected(self):
        for payload in (None, [], {}, {"csv": None}, {"csv": 42}):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "^invalid_csv$"):
                preview_import(payload)

    def test_accepts_one_hundred_rows_and_rejects_more(self):
        source = "customer_id,name\n" + "".join(f"{i},Customer {i}\n" for i in range(1, MAX_ROWS + 1))
        result = preview_import({"csv": source})
        self.assertEqual((result["total"], result["ready"]), (100, 100))
        with self.assertRaisesRegex(ValueError, "^invalid_csv$"):
            preview_import({"csv": source + "101,Too many\n"})


if __name__ == "__main__":
    unittest.main()
