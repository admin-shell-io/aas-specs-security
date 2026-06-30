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


class TimeLiteralFormatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.definition = schema_definition(COMMON_SCHEMA, "timeLiteralPattern")
        cls.time_literal = Draft7Validator(
            cls.definition,
            format_checker=Draft7Validator.FORMAT_CHECKER,
        )

    def assert_allowed(self, value):
        self.assertTrue(
            self.time_literal.is_valid(value),
            f"Expected timeLiteralPattern to allow: {value}",
        )

    def assert_not_allowed(self, value):
        self.assertFalse(
            self.time_literal.is_valid(value),
            f"Expected timeLiteralPattern to reject: {value}",
        )

    def test_allowed_time_literals(self):
        allowed = [
            "09:00:30Z",
            "09:00:30+01:00",
            "09:00:30.123+01:00",
            "09:00:30.123Z",
        ]

        for value in allowed:
            with self.subTest(value=value):
                self.assert_allowed(value)

    def test_not_allowed_time_literals(self):
        not_allowed = [
            "09:00",
            "09:00Z",
            "09:00+01:00",
            "09:00:30",
            "09:00:30.123",
            "09:00.123",
            "09:00.123Z",
            "09:00.123+01:00",
        ]

        for value in not_allowed:
            with self.subTest(value=value):
                self.assert_not_allowed(value)

    def test_duplicate_time_literal_definitions_are_in_sync(self):
        self.assertEqual(self.definition, schema_definition(FORMULAS_SCHEMA, "timeLiteralPattern"))


if __name__ == "__main__":
    unittest.main()
