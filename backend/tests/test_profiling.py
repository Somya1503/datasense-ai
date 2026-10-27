"""Tests for advanced column profiling and quality findings.

Run from the backend folder:
    python -m unittest discover -s tests -v
or, if pytest is installed:
    pytest -v

Expected values are computed independently (NumPy / hand arithmetic), not by
reading back what analyzer.py produced.
"""

import json
import os
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import analyzer  # noqa: E402
from analyzer import CSVAnalysisError, analyze_csv_bytes  # noqa: E402

HERE = os.path.dirname(__file__)
SAMPLE = os.path.join(HERE, "..", "sample_students.csv")
MESSY = os.path.join(HERE, "..", "sample_data", "messy_orders.csv")

LEGACY_KEYS = ["summary", "columns", "numeric_stats", "categorical_summary",
               "correlations", "outliers", "preview", "meta"]
NEW_KEYS = ["column_profiles", "quality_summary", "quality_findings", "profiling_error"]


def run(csv_text: str) -> dict:
    return analyze_csv_bytes(csv_text.encode("utf-8"))


def run_file(path: str) -> dict:
    with open(path, "rb") as handle:
        return analyze_csv_bytes(handle.read())


def profile(result: dict, name: str) -> dict:
    return next(p for p in result["column_profiles"] if p["name"] == name)


def finding_ids(result: dict) -> list:
    return [f["id"] for f in result["quality_findings"]]


def get_finding(result: dict, fid: str) -> dict:
    return next(f for f in result["quality_findings"] if f["id"] == fid)


class NumericProfileTests(unittest.TestCase):
    VALUES = [10, 12, 12, 13, 12, 11, 100]

    def setUp(self):
        # 7 numeric values plus one row where "metric" is blank (missing).
        body = "\n".join(f"{v},a" for v in self.VALUES)
        self.result = run("metric,label\n" + body + "\n,b\n")
        self.p = profile(self.result, "metric")
        self.num = self.p["numeric"]

    def test_basic_statistics_match_numpy(self):
        v = np.array(self.VALUES, dtype=float)
        self.assertEqual(self.p["analytical_type"], "numeric")
        self.assertAlmostEqual(self.num["mean"], v.mean())
        self.assertAlmostEqual(self.num["median"], float(np.median(v)))
        self.assertAlmostEqual(self.num["std"], v.std(ddof=1))
        self.assertEqual(self.num["min"], 10.0)
        self.assertEqual(self.num["max"], 100.0)

    def test_percentiles_and_iqr_match_numpy(self):
        v = np.array(self.VALUES, dtype=float)
        q1, q2, q3 = np.percentile(v, [25, 50, 75])
        self.assertAlmostEqual(self.num["p25"], q1)
        self.assertAlmostEqual(self.num["p50"], q2)
        self.assertAlmostEqual(self.num["p75"], q3)
        self.assertAlmostEqual(self.num["iqr"], q3 - q1)

    def test_outliers_use_iqr_rule(self):
        v = np.array(self.VALUES, dtype=float)
        q1, q3 = np.percentile(v, [25, 75])
        iqr = q3 - q1
        expected = int(((v < q1 - 1.5 * iqr) | (v > q3 + 1.5 * iqr)).sum())
        expected_extreme = int(((v < q1 - 3 * iqr) | (v > q3 + 3 * iqr)).sum())
        out = self.num["outliers"]
        self.assertEqual(out["count"], expected)
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["extreme_count"], expected_extreme)
        self.assertEqual(out["sample_values"], [100.0])
        self.assertAlmostEqual(out["percent"], round(1 / 7 * 100, 2))  # finite values only

    def test_profile_agrees_with_legacy_sections(self):
        legacy = self.result["numeric_stats"]["metric"]
        self.assertEqual(self.num["mean"], legacy["mean"])
        self.assertEqual(self.num["median"], legacy["median"])
        self.assertEqual(self.result["outliers"]["metric"]["count"], self.num["outliers"]["count"])

    def test_missing_vs_zero_vs_counts(self):
        self.assertEqual(self.p["row_count"], 8)
        self.assertEqual(self.p["non_missing_count"], 7)
        self.assertEqual(self.p["missing_count"], 1)
        self.assertEqual(self.p["missing_percent"], 12.5)
        self.assertEqual(self.num["zero_count"], 0)  # missing is NOT counted as zero

    def test_zero_is_counted_separately_from_missing(self):
        r = run("x,y\n0,a\n0,b\n5,c\n,d\n")  # last row: x is blank (missing)
        p = profile(r, "x")
        self.assertEqual(p["numeric"]["zero_count"], 2)
        self.assertEqual(p["missing_count"], 1)

    def test_unique_percent_uses_non_missing_denominator(self):
        # 7 non-missing values, 5 distinct -> 5/7, NOT 5/8
        self.assertEqual(self.p["unique_count"], 5)
        self.assertEqual(self.p["unique_percent_basis"], "non_missing_count")
        self.assertAlmostEqual(self.p["unique_percent"], round(5 / 7 * 100, 2))

    def test_no_categorical_block_for_numeric(self):
        self.assertIsNone(self.p["categorical"])
        self.assertIsNone(self.p["cardinality"])


class CategoricalProfileTests(unittest.TestCase):
    def setUp(self):
        self.result = run_file(SAMPLE)

    def test_top_values_and_percent_denominator(self):
        cat = profile(self.result, "city")["categorical"]
        # city has 9 non-missing values: Mumbai 4, Delhi 3, Bengaluru 2
        tops = {t["value"]: (t["count"], t["percent"]) for t in cat["top_values"]}
        self.assertEqual(tops["Mumbai"], (4, round(4 / 9 * 100, 2)))
        self.assertEqual(tops["Delhi"], (3, round(3 / 9 * 100, 2)))
        self.assertEqual(tops["Bengaluru"], (2, round(2 / 9 * 100, 2)))
        self.assertEqual(cat["percent_basis"], "non_missing_count")
        self.assertEqual(cat["modes"], ["Mumbai"])
        self.assertEqual(cat["mode_count"], 4)

    def test_no_numeric_block_for_categorical(self):
        p = profile(self.result, "city")
        self.assertIsNone(p["numeric"])
        self.assertEqual(p["analytical_type"], "categorical")

    def test_boolean_like_text_detected(self):
        p = profile(self.result, "passed")
        self.assertEqual(p["type_detail"], "boolean_like")
        self.assertEqual(p["cardinality"]["level"], "low")

    def test_multiple_modes_and_no_mode(self):
        r = run("c\na\na\nb\nb\nc\n")
        cat = profile(r, "c")["categorical"]
        self.assertEqual(sorted(cat["modes"]), ["a", "b"])
        r2 = run("c\na\nb\nc\nd\ne\n")
        cat2 = profile(r2, "c")["categorical"]
        self.assertEqual(cat2["modes"], [])
        self.assertIsNone(cat2["mode_count"])
        self.assertIsNotNone(cat2["mode_note"])

    def test_high_cardinality_is_truncated_and_flagged(self):
        body = "\n".join(f"item{i}" for i in range(60))
        r = run("c\n" + body + "\n")
        p = profile(r, "c")
        cat = p["categorical"]
        self.assertEqual(p["cardinality"]["level"], "high")
        self.assertTrue(p["cardinality"]["all_values_unique"])
        self.assertEqual(cat["shown_count"], analyzer.TOP_CATEGORIES)
        self.assertTrue(cat["truncated"])
        self.assertEqual(cat["other_count"], 60 - analyzer.TOP_CATEGORIES)

    def test_cardinality_levels(self):
        self.assertEqual(analyzer.cardinality_info(1, 10)["level"], "constant")
        self.assertEqual(analyzer.cardinality_info(3, 100)["level"], "low")
        self.assertEqual(analyzer.cardinality_info(30, 1000)["level"], "medium")
        self.assertEqual(analyzer.cardinality_info(51, 10000)["level"], "high")
        self.assertEqual(analyzer.cardinality_info(9, 10)["level"], "high")   # near-unique
        self.assertEqual(analyzer.cardinality_info(4, 4)["level"], "low")     # too few rows to call it
        self.assertIsNone(analyzer.cardinality_info(0, 0))


class QualityCountTests(unittest.TestCase):
    def setUp(self):
        self.result = run_file(SAMPLE)
        self.q = self.result["quality_summary"]

    def test_missing_counts_and_percentages(self):
        for col in ("age", "score", "city"):
            p = profile(self.result, col)
            self.assertEqual(p["missing_count"], 1)
            self.assertEqual(p["missing_percent"], 10.0)
        self.assertEqual(profile(self.result, "name")["missing_count"], 0)
        self.assertEqual(self.q["missing_cells"], 3)
        self.assertEqual(self.q["total_cells"], 50)
        self.assertEqual(self.q["missing_cells_percent"], 6.0)
        self.assertEqual(self.q["completeness_percent"], 94.0)
        # rows 3, 4 and 8 each have exactly one gap -> 3 incomplete rows
        self.assertEqual(self.q["rows_with_missing"], 3)
        self.assertEqual(self.q["complete_rows"], 7)

    def test_duplicates(self):
        self.assertEqual(self.q["duplicate_rows"], 1)
        self.assertEqual(self.q["duplicate_percent"], 10.0)
        self.assertEqual(self.q["rows_in_duplicate_groups"], 2)
        f = get_finding(self.result, "duplicates.exact_rows")
        self.assertEqual(f["evidence"]["duplicate_rows"], 1)
        self.assertEqual(f["severity"], "warning")  # 10% >= 1% threshold
        self.assertEqual(f["confidence"], "confirmed")

    def test_small_duplicate_share_is_info(self):
        body = "\n".join(f"{i},x" for i in range(200)) + "\n0,x\n"
        f = get_finding(run("a,b\n" + body), "duplicates.exact_rows")
        self.assertEqual(f["severity"], "info")  # 1/201 < 1%

    def test_extreme_outlier_is_flagged_for_review(self):
        f = get_finding(self.result, "outliers.extreme")
        self.assertEqual(f["affected_columns"], ["score"])
        self.assertEqual(f["confidence"], "needs_review")
        self.assertEqual(f["evidence"]["columns"][0]["sample_values"], [300.0])

    def test_finding_shape_and_unique_ids(self):
        required = {"id", "category", "severity", "confidence", "title", "affected_columns",
                    "evidence", "explanation", "recommendation"}
        ids = finding_ids(self.result)
        self.assertEqual(len(ids), len(set(ids)))
        for f in self.result["quality_findings"]:
            self.assertTrue(required <= set(f))
            self.assertIn(f["severity"], ("critical", "warning", "info"))
            self.assertIn(f["confidence"], ("confirmed", "needs_review"))
            self.assertTrue(f["explanation"] and f["recommendation"])

    def test_findings_sorted_by_severity(self):
        order = {"critical": 0, "warning": 1, "info": 2}
        sev = [order[f["severity"]] for f in self.result["quality_findings"]]
        self.assertEqual(sev, sorted(sev))

    def test_finding_counts_match_list(self):
        counts = self.q["finding_counts"]
        findings = self.result["quality_findings"]
        self.assertEqual(counts["total"], len(findings))
        for s in ("critical", "warning", "info"):
            self.assertEqual(counts[s], sum(1 for f in findings if f["severity"] == s))

    def test_no_critical_without_all_missing_column(self):
        self.assertEqual(self.q["finding_counts"]["critical"], 0)

    def test_no_quality_score_field(self):
        self.assertFalse([k for k in self.q if "score" in k.lower()])


class ConstantAndEmptyColumnTests(unittest.TestCase):
    def setUp(self):
        self.result = run("keep,const,empty,partial\n1,x,,a\n2,x,,\n3,x,,a\n4,x,,b\n")

    def test_constant_column(self):
        p = profile(self.result, "const")
        self.assertTrue(p["is_constant"])
        self.assertEqual(p["constant_value"], "x")
        f = get_finding(self.result, "structure.constant_columns")
        self.assertEqual(f["affected_columns"], ["const"])
        self.assertEqual(f["severity"], "info")

    def test_all_missing_column(self):
        p = profile(self.result, "empty")
        self.assertTrue(p["is_all_missing"])
        self.assertEqual(p["analytical_type"], "other")
        self.assertEqual(p["missing_percent"], 100.0)
        self.assertIsNone(p["unique_percent"])         # undefined, not 0
        self.assertIsNone(p["numeric"])
        self.assertIsNone(p["categorical"])
        f = get_finding(self.result, "missing_values.all_missing")
        self.assertEqual(f["severity"], "critical")
        self.assertEqual(f["affected_columns"], ["empty"])

    def test_all_missing_is_not_also_reported_as_constant_or_partial(self):
        self.assertNotIn("empty", get_finding(self.result, "structure.constant_columns")["affected_columns"])
        for fid in ("missing_values.high", "missing_values.low"):
            if fid in finding_ids(self.result):
                self.assertNotIn("empty", get_finding(self.result, fid)["affected_columns"])

    def test_partial_missing_severity_split(self):
        # 'partial' is 25% missing -> warning bucket (>= 20%)
        f = get_finding(self.result, "missing_values.high")
        self.assertEqual(f["affected_columns"], ["partial"])
        self.assertEqual(f["severity"], "warning")


class TypeInferenceTests(unittest.TestCase):
    def test_identifier_by_name_is_not_treated_as_measurement(self):
        r = run("customer_id,zip_code,amount\n101,560001,10.5\n205,400001,11.5\n101,560001,9.0\n")
        for col in ("customer_id", "zip_code"):
            p = profile(r, col)
            self.assertEqual(p["analytical_type"], "other")
            self.assertEqual(p["type_detail"], "identifier_like")
            self.assertIsNone(p["numeric"])
        self.assertEqual(profile(r, "amount")["analytical_type"], "numeric")
        self.assertIn("types.identifier_like_numeric", finding_ids(r))

    def test_row_number_pattern_is_identifier_like(self):
        r = run("n,v\n" + "\n".join(f"{i},{i * 3.5}" for i in range(1, 8)) + "\n")
        self.assertEqual(profile(r, "n")["type_detail"], "identifier_like")

    def test_year_like_sequence_is_not_flagged(self):
        r = run("year,v\n" + "\n".join(f"{2015 + i},{i * 2.5}" for i in range(8)) + "\n")
        self.assertEqual(profile(r, "year")["analytical_type"], "numeric")

    def test_identifier_columns_do_not_produce_outlier_findings(self):
        ids = [str(1000 + i) for i in range(12)] + ["999999"]
        r = run("user_id,v\n" + "\n".join(f"{i},{n}" for n, i in enumerate(ids)) + "\n")
        for fid in ("outliers.extreme", "outliers.moderate"):
            if fid in finding_ids(r):
                self.assertNotIn("user_id", get_finding(r, fid)["affected_columns"])

    def test_original_values_untouched_in_preview(self):
        r = run("zip_code,v\n00501,1\n02134,2\n")
        # pandas parses leading-zero codes as numbers; we report that, we don't alter data
        self.assertEqual(r["preview"][0]["zip_code"], 501)
        self.assertEqual(profile(r, "zip_code")["type_detail"], "identifier_like")

    def test_numeric_stored_as_text(self):
        values = [str(i) for i in range(1, 10)] + ["abc"]
        r = run("v\n" + "\n".join(values) + "\n")
        p = profile(r, "v")
        self.assertEqual(p["analytical_type"], "categorical")
        self.assertIsNone(p["numeric"])
        f = get_finding(r, "types.numeric_stored_as_text")
        ev = f["evidence"]["columns"][0]
        self.assertEqual(ev["numeric_like_count"], 9)
        self.assertEqual(ev["non_numeric_count"], 1)
        self.assertEqual(f["confidence"], "confirmed")
        self.assertTrue(ev["examples"][0].startswith("abc"))

    def test_mostly_text_column_is_not_numeric_like(self):
        r = run("v\n1\n2\nfoo\nbar\nbaz\n")
        self.assertNotIn("types.numeric_stored_as_text", finding_ids(r))

    def test_iso_dates_detected_with_range(self):
        r = run("d,v\n2026-01-05,1\n2026-03-01,2\n2026-02-10,3\n")
        p = profile(r, "d")
        self.assertEqual(p["analytical_type"], "datetime")
        self.assertTrue(p["datetime"]["earliest"].startswith("2026-01-05"))
        self.assertTrue(p["datetime"]["latest"].startswith("2026-03-01"))
        self.assertIsNone(p["numeric"])

    def test_ambiguous_dates_have_no_range(self):
        r = run("d,v\n01/02/2026,1\n03/04/2026,2\n05/06/2026,3\n")
        p = profile(r, "d")
        self.assertEqual(p["analytical_type"], "datetime")
        self.assertTrue(p["datetime"]["ambiguous_day_month"])
        self.assertIsNone(p["datetime"]["earliest"])

    def test_two_date_like_values_are_not_enough(self):
        r = run("d,v\n2026-01-05,1\n2026-03-01,2\n")
        self.assertEqual(profile(r, "d")["analytical_type"], "categorical")

    def test_plain_text_is_not_datetime(self):
        r = run("t\nhello\nworld\nfoo\n")
        self.assertEqual(profile(r, "t")["analytical_type"], "categorical")

    def test_name_words(self):
        self.assertIn("id", analyzer._name_words("customerId"))
        self.assertIn("zip", analyzer._name_words("Zip-Code"))
        self.assertNotIn("id", analyzer._name_words("valid"))
        self.assertNotIn("id", analyzer._name_words("paid"))


class ConsistencyFindingTests(unittest.TestCase):
    def test_case_and_whitespace_variants(self):
        r = run("c\nMumbai\nmumbai\nMumbai \nDelhi\nDelhi\n")
        f = get_finding(r, "consistency.case_whitespace_variants")
        ev = f["evidence"]["columns"][0]
        self.assertEqual(ev["group_count"], 1)
        self.assertEqual(ev["affected_values"], 3)
        self.assertEqual(f["confidence"], "needs_review")

    def test_no_variants_when_values_differ(self):
        r = run("c\nMumbai\nDelhi\nPune\nMumbai\n")
        self.assertNotIn("consistency.case_whitespace_variants", finding_ids(r))

    def test_placeholder_tokens(self):
        r = run("c\nred\n?\nblue\nunknown\n?\nred\n")
        f = get_finding(r, "consistency.placeholder_tokens")
        ev = f["evidence"]["columns"][0]
        self.assertEqual(ev["total_count"], 3)
        self.assertTrue(ev["examples"][0].startswith('"?"'))

    def test_unexpected_negative_needs_name_evidence(self):
        r = run("age,delta\n30,-2\n-5,3\n41,-1\n50,4\n")
        f = get_finding(r, "values.unexpected_negative")
        self.assertEqual(f["affected_columns"], ["age"])  # 'delta' has no name hint
        self.assertEqual(f["evidence"]["columns"][0]["negative_count"], 1)


class EdgeCaseTests(unittest.TestCase):
    def test_empty_inputs_still_rejected(self):
        with self.assertRaises(CSVAnalysisError):
            analyze_csv_bytes(b"")
        with self.assertRaises(CSVAnalysisError):
            analyze_csv_bytes(b"a,b,c\n")  # header only

    def test_single_row_dataset(self):
        r = run("a,b\n5,x\n")
        pa = profile(r, "a")
        self.assertIsNone(pa["numeric"]["std"])               # undefined for n=1, not 0
        self.assertTrue(any("undefined" in n for n in pa["notes"]))
        self.assertFalse(pa["is_constant"])                   # needs >= 2 values
        self.assertNotIn("structure.constant_columns", finding_ids(r))
        self.assertIn("note", pa["numeric"]["outliers"])
        self.assertIsNotNone(pa["numeric"]["outliers"]["note"])
        json.dumps(r, allow_nan=False)

    def test_two_row_dataset(self):
        r = run("a,b\n1,x\n2,y\n")
        self.assertEqual(profile(r, "a")["numeric"]["outliers"]["count"], 0)
        json.dumps(r, allow_nan=False)

    def test_only_numeric_dataset(self):
        r = run("a,b\n1,2.5\n2,3.5\n3,4.5\n4,9.5\n")
        self.assertEqual(r["quality_summary"]["type_counts"]["categorical"], 0)
        self.assertTrue(all(p["categorical"] is None for p in r["column_profiles"]))

    def test_only_categorical_dataset(self):
        r = run("a,b\nx,u\ny,v\nx,u\n")
        self.assertEqual(r["quality_summary"]["type_counts"]["numeric"], 0)
        self.assertFalse(r["correlations"]["available"])
        self.assertTrue(all(p["numeric"] is None for p in r["column_profiles"]))

    def test_clean_dataset_has_no_findings(self):
        r = run("a,b\n12,x\n15,y\n11,z\n14,x\n13,y\n")
        self.assertEqual(r["quality_findings"], [])
        self.assertEqual(r["quality_summary"]["finding_counts"]["total"], 0)

    def test_infinite_values_are_excluded_and_reported(self):
        r = run("v,w\n1,a\n2,b\ninf,c\n3,d\n4,e\n5,f\n")
        n = profile(r, "v")["numeric"]
        self.assertEqual(n["infinite_count"], 1)
        self.assertEqual(n["finite_count"], 5)
        self.assertEqual(n["max"], 5.0)
        text = json.dumps(r, allow_nan=False)
        self.assertNotIn("Infinity", text)

    def test_duplicate_and_blank_header_names(self):
        r = run("a,a,\n1,2,3\n4,5,6\n")
        names = [p["name"] for p in r["column_profiles"]]
        self.assertEqual(len(names), len(set(names)))

    def test_wide_dataset_caps_evidence_rows(self):
        header = ",".join(f"c{i}" for i in range(80))
        rows = "\n".join(",".join("" if j % 2 == 0 else "1" for j in range(80)) for _ in range(5))
        r = run(header + "\n" + rows + "\n")
        f = get_finding(r, "missing_values.all_missing")
        self.assertEqual(f["affected_columns_total"], 40)
        self.assertLessEqual(len(f["evidence"]["columns"]), analyzer.MAX_EVIDENCE_COLUMNS)


class SerializationAndCompatibilityTests(unittest.TestCase):
    FILES = [SAMPLE, MESSY]

    def test_full_response_is_strict_json(self):
        for path in self.FILES:
            r = run_file(path)
            text = json.dumps(r, allow_nan=False)  # raises on NaN / Infinity
            self.assertNotIn("NaN", text)
            self.assertEqual(json.loads(text)["quality_summary"]["rows"], r["summary"]["rows"])

    def test_legacy_fields_preserved_and_new_fields_added(self):
        for path in self.FILES:
            r = run_file(path)
            for key in LEGACY_KEYS + NEW_KEYS:
                self.assertIn(key, r)
            self.assertEqual(r["summary"]["rows"], r["quality_summary"]["rows"])
            self.assertEqual(len(r["column_profiles"]), r["summary"]["columns"])
            self.assertEqual([c["name"] for c in r["columns"]],
                             [p["name"] for p in r["column_profiles"]])
            self.assertIsNone(r["profiling_error"])

    def test_legacy_column_fields_agree_with_profiles(self):
        r = run_file(MESSY)
        for col, prof in zip(r["columns"], r["column_profiles"]):
            self.assertEqual(col["missing_count"], prof["missing_count"])
            self.assertEqual(col["missing_percent"], prof["missing_percent"])
            self.assertEqual(col["unique_count"], prof["unique_count"])
            self.assertEqual(col["dtype"], prof["dtype"])

    def test_messy_demo_produces_expected_findings(self):
        r = run_file(MESSY)
        ids = set(finding_ids(r))
        expected = {
            "missing_values.all_missing", "duplicates.exact_rows", "outliers.extreme",
            "types.numeric_stored_as_text", "consistency.case_whitespace_variants",
            "consistency.placeholder_tokens", "values.unexpected_negative",
            "structure.constant_columns", "types.identifier_like_numeric",
        }
        self.assertTrue(expected <= ids, expected - ids)
        self.assertEqual(r["quality_summary"]["finding_counts"]["critical"], 1)
        # one underlying issue (TBD in discount_pct) must not be warned about twice
        self.assertNotIn("discount_pct", get_finding(r, "consistency.placeholder_tokens")["affected_columns"])

    def test_profiling_failure_does_not_break_legacy_analysis(self):
        with mock.patch.object(analyzer, "build_column_profiles", side_effect=RuntimeError("boom")):
            r = run_file(SAMPLE)
        for key in LEGACY_KEYS:
            self.assertIn(key, r)
        self.assertEqual(r["column_profiles"], [])
        self.assertEqual(r["quality_findings"], [])
        self.assertIsNone(r["quality_summary"])
        self.assertIsInstance(r["profiling_error"], str)
        self.assertNotIn("boom", r["profiling_error"])  # no internals leaked
        json.dumps(r, allow_nan=False)

    def test_rules_and_definitions_are_documented_in_response(self):
        q = run_file(SAMPLE)["quality_summary"]
        self.assertIn("definitions", q)
        self.assertEqual(q["rules"]["high_missing_percent"], analyzer.HIGH_MISSING_PERCENT)
        self.assertEqual(set(q["rules"]["severity"]), {"critical", "warning", "info"})


@unittest.skipUnless(
    all(__import__("importlib").util.find_spec(m) for m in ("fastapi", "httpx", "multipart")),
    "fastapi, httpx and python-multipart are required for API tests (pip install -r requirements-dev.txt)",
)
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import main
        cls.client = TestClient(main.app)

    def post(self, name, data, ctype="text/csv"):
        return self.client.post("/analyze", files={"file": (name, data, ctype)})

    def test_health(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "healthy"})

    def test_analyze_returns_legacy_and_new_fields(self):
        with open(SAMPLE, "rb") as handle:
            resp = self.post("sample_students.csv", handle.read())
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["filename"], "sample_students.csv")
        for key in LEGACY_KEYS + NEW_KEYS:
            self.assertIn(key, body["analysis"])

    def test_existing_validation_unchanged(self):
        self.assertEqual(self.post("x.txt", b"a,b\n1,2\n").status_code, 400)
        self.assertEqual(self.post("empty.csv", b"").status_code, 400)
        resp = self.post("header_only.csv", b"a,b\n")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("detail", resp.json())
        self.assertEqual(self.client.post("/analyze").status_code, 400)


if __name__ == "__main__":
    unittest.main()
