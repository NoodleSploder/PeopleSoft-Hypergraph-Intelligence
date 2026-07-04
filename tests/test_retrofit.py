import unittest
from unittest.mock import patch

from connectors import retrofit


class RetrofitPageFieldsTests(unittest.TestCase):
    def setUp(self):
        self.rows_a = [
            {"recname": "JOB", "fieldname": "DEPTID", "fieldnum": 5, "occurslevel": 0,
             "fieldtop": 100, "fieldleft": 50, "fieldtype": 0},
            {"recname": "JOB", "fieldname": "CUST_FLAG", "fieldnum": 6, "occurslevel": 0,
             "fieldtop": 110, "fieldleft": 50, "fieldtype": 0},
            {"recname": "JOB", "fieldname": "OLD_FIELD", "fieldnum": 7, "occurslevel": 0,
             "fieldtop": 120, "fieldleft": 50, "fieldtype": 0},
        ]
        self.rows_b = [
            {"recname": "JOB", "fieldname": "DEPTID", "fieldnum": 7, "occurslevel": 0,
             "fieldtop": 140, "fieldleft": 50, "fieldtype": 0},
            {"recname": "JOB", "fieldname": "CUST_FLAG", "fieldnum": 8, "occurslevel": 0,
             "fieldtop": 150, "fieldleft": 50, "fieldtype": 0},
            {"recname": "JOB", "fieldname": "NEW_DELIVERED_FIELD", "fieldnum": 5, "occurslevel": 0,
             "fieldtop": 100, "fieldleft": 50, "fieldtype": 0},
            {"recname": "JOB", "fieldname": "NEW_DELIVERED_FIELD2", "fieldnum": 6, "occurslevel": 0,
             "fieldtop": 110, "fieldleft": 50, "fieldtype": 0},
        ]

    def test_detects_added_removed_and_repositioned_fields(self):
        def fake_query(env, sql, params=None):
            return self.rows_a if env == "HCM" else self.rows_b

        with patch("connectors.retrofit.psdb.query", side_effect=fake_query), \
             patch("connectors.retrofit.ptmetadata.has_table", return_value=True):
            result = retrofit.compare_page_fields("HCM", "FSCM", "JOB_DATA1")

        self.assertEqual(result["only_in_hcm"], ["JOB.OLD_FIELD"])
        self.assertEqual(sorted(result["only_in_fscm"]),
                          ["JOB.NEW_DELIVERED_FIELD", "JOB.NEW_DELIVERED_FIELD2"])
        moved_fields = {m["record_field"] for m in result["moved_or_repositioned"]}
        self.assertEqual(moved_fields, {"JOB.CUST_FLAG", "JOB.DEPTID"})
        self.assertFalse(result["identical_layout"])

    def test_identical_layout_when_nothing_differs(self):
        def fake_query(env, sql, params=None):
            return self.rows_a

        with patch("connectors.retrofit.psdb.query", side_effect=fake_query), \
             patch("connectors.retrofit.ptmetadata.has_table", return_value=True):
            result = retrofit.compare_page_fields("HCM", "FSCM", "JOB_DATA1")

        self.assertTrue(result["identical_layout"])
        self.assertEqual(result["moved_or_repositioned"], [])


class RetrofitVerifyVerdictTests(unittest.TestCase):
    def setUp(self):
        self.row_target = {"recname": "JOB", "descr": "new desc", "other_col": "X",
                            "lastupdoprid": "PPLSOFT", "lastupddttm": "2026-01-01"}

    def _verify(self, row_current, previous_diff_columns):
        def fake_query(env, sql, params=None):
            return [row_current] if env == "HCM" else [self.row_target]

        with patch("connectors.retrofit.psdb.query", side_effect=fake_query), \
             patch("connectors.retrofit.ptmetadata.has_table", return_value=True):
            return retrofit.retrofit_verify("HCM", "FSCM", "record", "JOB",
                                             previous_diff_columns=previous_diff_columns)

    def test_resolved_when_change_matches_target(self):
        row_fixed = {"recname": "JOB", "descr": "new desc", "other_col": "X",
                     "lastupdoprid": "PS", "lastupddttm": "2026-01-01"}
        result = self._verify(row_fixed, previous_diff_columns=["descr"])
        self.assertEqual(result["verdict"], "RESOLVED")

    def test_still_divergent_when_nothing_changed(self):
        row_unchanged = {"recname": "JOB", "descr": "old desc", "other_col": "X",
                         "lastupdoprid": "PS", "lastupddttm": "2026-01-01"}
        result = self._verify(row_unchanged, previous_diff_columns=["descr"])
        self.assertEqual(result["verdict"], "STILL_DIVERGENT")

    def test_new_issue_introduced_when_a_different_column_now_diverges(self):
        row_new_break = {"recname": "JOB", "descr": "new desc", "other_col": "BROKEN",
                          "lastupdoprid": "PS", "lastupddttm": "2026-01-01"}
        result = self._verify(row_new_break, previous_diff_columns=["descr"])
        self.assertEqual(result["verdict"], "NEW_ISSUE_INTRODUCED")


if __name__ == "__main__":
    unittest.main()
