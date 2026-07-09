import json
import unittest
from pathlib import Path

from jsonschema import Draft7Validator


ROOT = Path(__file__).resolve().parents[2]
COMMON_SCHEMA = ROOT / "documentation/IDTA-01004/modules/ROOT/partials/json/aas-queries-and-access-rules-schema.json"
FORMULAS_SCHEMA = ROOT / "documentation/IDTA-01004/modules/ROOT/partials/json/formulas-and-logical-expressions.json"


def schema_definition(schema_path, definition):
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    return schema["definitions"][definition]


class TimeAndDateTimeLiteralPatternTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.time_definition = schema_definition(COMMON_SCHEMA, "timeLiteralPattern")
        cls.time_literal = Draft7Validator(
            cls.time_definition,
        )
        cls.date_time_definition = schema_definition(COMMON_SCHEMA, "dateTimeLiteralPattern")
        cls.date_time_literal = Draft7Validator(
            cls.date_time_definition,
        )

    def assert_time_allowed(self, value):
        self.assertTrue(
            self.time_literal.is_valid(value),
            f"Expected timeLiteralPattern to allow: {value}",
        )

    def assert_time_not_allowed(self, value):
        self.assertFalse(
            self.time_literal.is_valid(value),
            f"Expected timeLiteralPattern to reject: {value}",
        )

    def assert_date_time_allowed(self, value):
        self.assertTrue(
            self.date_time_literal.is_valid(value),
            f"Expected dateTimeLiteralPattern to allow: {value}",
        )

    def assert_date_time_not_allowed(self, value):
        self.assertFalse(
            self.date_time_literal.is_valid(value),
            f"Expected dateTimeLiteralPattern to reject: {value}",
        )

    def test_allowed_time_literals(self):
        allowed = [
            "09:00:30",
            "09:00:30Z",
            "09:00:30+01:00",
            "09:00:30+14:00",
            "09:00:30.123+01:00",
            "09:00:30.123Z",
            "24:00:00",
            "24:00:00.000Z",
        ]

        for value in allowed:
            with self.subTest(value=value):
                self.assert_time_allowed(value)

    def test_not_allowed_time_literals(self):
        not_allowed = [
            "09:00",
            "09:00Z",
            "09:00+01:00",
            "09:00.123",
            "09:00.123Z",
            "09:00.123+01:00",
            "09:00:30+14:01",
            "09:00:30+15:00",
            "24:00:01",
            "24:00:00.001",
        ]

        for value in not_allowed:
            with self.subTest(value=value):
                self.assert_time_not_allowed(value)

    def test_allowed_date_time_literals(self):
        allowed = [
            "2026-06-30T09:00:00",
            "2026-06-30T09:00:00Z",
            "2026-06-30T09:00:00+01:00",
            "2026-06-30T09:00:00.123Z",
            "2026-06-30T24:00:00",
            "-2026-06-30T09:00:00Z",
            "12026-06-30T09:00:00Z",
        ]

        for value in allowed:
            with self.subTest(value=value):
                self.assert_date_time_allowed(value)

    def test_not_allowed_date_time_literals(self):
        not_allowed = [
            "2026-06-30T09:00",
            "2026-06-30T09:00Z",
            "2026-06-30T09:00:00+14:01",
            "2026-06-30T24:00:01",
            "2026-13-30T09:00:00Z",
            "2026-06-32T09:00:00Z",
        ]

        for value in not_allowed:
            with self.subTest(value=value):
                self.assert_date_time_not_allowed(value)

    def test_duplicate_literal_definitions_are_in_sync(self):
        self.assertEqual(self.time_definition, schema_definition(FORMULAS_SCHEMA, "timeLiteralPattern"))
        self.assertEqual(self.date_time_definition, schema_definition(FORMULAS_SCHEMA, "dateTimeLiteralPattern"))


if __name__ == "__main__":
    unittest.main()
