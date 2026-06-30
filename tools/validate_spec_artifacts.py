#!/usr/bin/env python3
"""Validate JSON Schema, JSON examples, and BNF artifacts."""

from __future__ import annotations

import json
import re
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from jsonschema import Draft7Validator

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from jsonschema import RefResolver
except ImportError as exc:  # pragma: no cover - exercised in CI setup failures.
    print("Missing dependency: jsonschema. Install it with: python -m pip install jsonschema")
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]
PARTIALS = ROOT / "documentation/IDTA-01004/modules/ROOT/partials"
JSON_DIR = PARTIALS / "json"
BNF_DIR = PARTIALS / "bnf"
EXAMPLES_DIR = PARTIALS / "examples"

RULE_RE = re.compile(r"^\s*<([^<>]+)>\s*::=\s*(.*)$")
REF_RE = re.compile(r"<([^<>]+)>")
OBJECT_LINE_RE = re.compile(r"^\s*(IDENTIFIABLE|REFERABLE|DESCRIPTOR)\s+(.+?)\s*$")
FRAGMENT_LINE_RE = re.compile(r'^\s*FRAGMENT\s+"([^"]+)"\s*$')
FIELD_TOKEN_RE = re.compile(
    r"\$(?:aasdesc|smdesc|aas|sm|sme|cd)"
    r"(?:\.[A-Za-z](?:[A-Za-z0-9_-]*[A-Za-z0-9_])?(?:\[(?:0|[1-9][0-9]*)?\])*)*"
    r"#[A-Za-z][A-Za-z0-9_.\[\]-]*"
)

OBJECT_DEFINITION = {
    "IDENTIFIABLE": "IdentifiableIdentifier",
    "REFERABLE": "ReferableIdentifier",
    "DESCRIPTOR": "DescriptorIdentifier",
}


@dataclass(frozen=True)
class BnfRule:
    name: str
    path: Path
    line: int
    rhs: str


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def fail(self, path: Path | str, message: str) -> None:
        self.errors.append(f"{display_path(path)}: {message}")

    def assert_ok(self) -> None:
        if self.errors:
            print("Validation failed:")
            for error in self.errors:
                print(f"  - {error}")
            raise SystemExit(1)


def display_path(path: Path | str) -> str:
    path = Path(path)
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def json_files() -> list[Path]:
    return sorted(PARTIALS.rglob("*.json"))


def schema_files() -> list[Path]:
    return sorted(JSON_DIR.glob("*.json"))


def example_json_files() -> list[Path]:
    return sorted(EXAMPLES_DIR.glob("*.json"))


def bnf_files() -> list[Path]:
    return sorted(BNF_DIR.glob("*.bnf"))


def example_bnf_files() -> list[Path]:
    return sorted(EXAMPLES_DIR.glob("*.bnf"))


def load_json(path: Path, validation: Validation) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - include parser detail in validation output.
        validation.fail(path, f"invalid JSON: {exc}")
        return None


def iter_refs(node: Any) -> Iterable[str]:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            yield ref
        for value in node.values():
            yield from iter_refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_refs(value)


def resolve_pointer(document: Any, pointer: str) -> Any:
    current = document
    if pointer in ("", "/"):
        return current
    for raw_part in pointer.lstrip("/").split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        current = current[part]
    return current


def schema_validator(schema_path: Path, schema: dict[str, Any], ref: str) -> Draft7Validator:
    resolver = RefResolver(base_uri=schema_path.resolve().as_uri(), referrer=schema)
    return Draft7Validator({"$ref": ref}, resolver=resolver, format_checker=Draft7Validator.FORMAT_CHECKER)


def definition_validator(
    schema_path: Path,
    schema: dict[str, Any],
    definition_name: str,
) -> Draft7Validator:
    return schema_validator(schema_path, schema, f"#/definitions/{definition_name}")


def validate_json_artifacts(validation: Validation) -> dict[str, Any] | None:
    loaded_json: dict[Path, Any] = {}
    for path in json_files():
        data = load_json(path, validation)
        if data is not None:
            loaded_json[path] = data

    if validation.errors:
        return None
    print(f"OK: parsed {len(loaded_json)} JSON files")

    for path in schema_files():
        schema = loaded_json[path]
        try:
            Draft7Validator.check_schema(schema)
        except Exception as exc:  # noqa: BLE001 - include schema detail in validation output.
            validation.fail(path, f"invalid draft-07 schema: {exc}")
    print(f"OK: checked {len(schema_files())} JSON schema files")

    validate_json_refs(loaded_json, validation)
    validate_json_examples(loaded_json, validation)

    common_schema = loaded_json.get(JSON_DIR / "aas-queries-and-access-rules-schema.json")
    if isinstance(common_schema, dict):
        validate_schema_smoke_tests(JSON_DIR / "aas-queries-and-access-rules-schema.json", common_schema, validation)
        return common_schema
    validation.fail(JSON_DIR / "aas-queries-and-access-rules-schema.json", "schema could not be loaded")
    return None


def validate_json_refs(loaded_json: dict[Path, Any], validation: Validation) -> None:
    checked = 0
    for path in schema_files():
        schema = loaded_json[path]
        for ref in iter_refs(schema):
            checked += 1
            if ref.startswith("#/"):
                target_path = path
                pointer = ref[1:]
            elif "#" in ref:
                target_name, pointer = ref.split("#", 1)
                target_path = path.parent / target_name
            else:
                continue

            target_doc = loaded_json.get(target_path)
            if target_doc is None:
                validation.fail(path, f"$ref target file does not exist: {ref}")
                continue

            try:
                resolve_pointer(target_doc, pointer)
            except Exception as exc:  # noqa: BLE001 - include ref detail in validation output.
                validation.fail(path, f"unresolved $ref {ref}: {exc}")
    print(f"OK: resolved {checked} JSON schema references")


def validate_json_examples(loaded_json: dict[Path, Any], validation: Validation) -> None:
    schema_paths = [
        JSON_DIR / "aas-queries-and-access-rules-schema.json",
        JSON_DIR / "access-rule-model.json",
    ]
    validators = [
        schema_validator(path, loaded_json[path], "#")
        for path in schema_paths
        if isinstance(loaded_json.get(path), dict)
    ]

    for path in example_json_files():
        data = loaded_json[path]
        for validator in validators:
            errors = sorted(validator.iter_errors(data), key=lambda error: list(error.absolute_path))
            for error in errors:
                location = "/".join(str(part) for part in error.absolute_path) or "<root>"
                validation.fail(path, f"{location}: {error.message}")
    print(f"OK: validated {len(example_json_files())} JSON examples against {len(validators)} schemas")


def validate_schema_smoke_tests(schema_path: Path, schema: dict[str, Any], validation: Validation) -> None:
    cases = [
        ("FieldIdentifier", "$sm#supplementalSemanticIds[]", True),
        ("FieldIdentifier", "$sm#supplementalSemanticIds[0]", True),
        ("FieldIdentifier", "$sm#supplementalSemanticIds[01]", False),
        ("FieldIdentifier", "$aas#submodels[01]", False),
        ("FragmentFieldIdentifier", "$sm#supplementalSemanticIds[]", True),
        ("FragmentFieldIdentifier", "$sm#supplementalSemanticIds[0].keys[]", True),
        ("FragmentFieldIdentifier", "$sm#supplementalSemanticIds[01]", False),
        ("ReferenceIdentifier", "$sm(\"SubmodelID\")#id", True),
        ("ReferenceIdentifier", "$sme(\"SubmodelID\").machineState#value", True),
        ("ReferenceIdentifier", "$sm#id", False),
        ("ReferenceIdentifier", "$sm(\"SubmodelID\")#martinwarhier", False),
        ("timeLiteralPattern", "09:00:00Z", True),
        ("timeLiteralPattern", "09:00:30Z", True),
        ("timeLiteralPattern", "09:00:30.123Z", True),
        ("timeLiteralPattern", "09:00:30+01:00", True),
        ("timeLiteralPattern", "09:00", False),
        ("timeLiteralPattern", "09:00:30", False),
        ("timeLiteralPattern", "09:00.123", False),
        ("Value", {"$dayOfWeek": {"$dateTimeVal": "2026-06-30T09:00:00Z"}}, True),
        ("Value", {"$dayOfWeek": {"$dateTimeCast": {"$strVal": "2026-06-30T09:00:00Z"}}}, True),
        ("Value", {"$dayOfWeek": {"$attribute": {"GLOBAL": "UTCNOW"}}}, True),
        ("Value", {"$dayOfWeek": "2026-06-30T09:00:00Z"}, False),
        ("Value", {"$dayOfWeek": {"$attribute": {"GLOBAL": "ANONYMOUS"}}}, False),
        ("Value", {"$dayOfWeek": {"$attribute": {"CLAIM": "iat"}}}, False),
        ("logicalExpression", {"$eq": [{"$boolean": True}, {"$boolean": False}]}, True),
        ("logicalExpression", {"$gt": [{"$boolean": True}, {"$boolean": False}]}, False),
        ("logicalExpression", {"$boolCast": {"$strVal": "true"}}, True),
        (
            "logicalExpression",
            {"$eq": [{"$dateTimeCast": {"$strVal": "2026-06-30T09:00:00Z"}}, {"$dateTimeVal": "2026-06-30T09:00:00Z"}]},
            True,
        ),
        (
            "logicalExpression",
            {"$eq": [{"$dateTimeCast": {"$numVal": 1}}, {"$dateTimeVal": "2026-06-30T09:00:00Z"}]},
            False,
        ),
        ("logicalExpression", {"$eq": [{"$timeCast": {"$dateTimeVal": "2026-06-30T09:00:00Z"}}, {"$timeVal": "09:00:00Z"}]}, True),
        ("logicalExpression", {"$eq": [{"$timeCast": {"$numVal": 1}}, {"$timeVal": "09:00:00Z"}]}, False),
        ("matchExpression", {"$boolean": True}, False),
    ]

    validators: dict[str, Draft7Validator] = {}
    for definition_name, value, should_pass in cases:
        validators.setdefault(definition_name, definition_validator(schema_path, schema, definition_name))
        is_valid = validators[definition_name].is_valid(value)
        if is_valid != should_pass:
            expected = "valid" if should_pass else "invalid"
            validation.fail(schema_path, f"{definition_name} smoke test expected {expected}: {value}")
    print(f"OK: ran {len(cases)} JSON schema smoke tests")


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == "\\":
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def without_quoted_literals(text: str) -> tuple[str, bool]:
    result: list[str] = []
    in_string = False
    for index, char in enumerate(text):
        if char == '"' and not is_escaped(text, index):
            in_string = not in_string
            result.append(" ")
        elif in_string:
            result.append(" ")
        else:
            result.append(char)
    return "".join(result), in_string


def validate_balanced_delimiters(path: Path, text: str, validation: Validation) -> None:
    stack: list[tuple[str, int, int]] = []
    opening = {"(": ")", "[": "]"}
    closing = {")": "(", "]": "["}

    for line_number, line in enumerate(text.splitlines(), start=1):
        clean_line, unclosed_string = without_quoted_literals(line)
        if unclosed_string:
            validation.fail(path, f"line {line_number}: unclosed quoted literal")

        for column, char in enumerate(clean_line, start=1):
            if char in opening:
                stack.append((char, line_number, column))
            elif char in closing:
                if not stack or stack[-1][0] != closing[char]:
                    validation.fail(path, f"line {line_number}: unmatched {char}")
                    continue
                stack.pop()

    for char, line_number, column in stack:
        validation.fail(path, f"line {line_number}, column {column}: unmatched {char}")


def parse_bnf_rules(path: Path, validation: Validation) -> list[BnfRule]:
    rules: list[BnfRule] = []
    seen_in_file: dict[str, int] = {}
    current_name: str | None = None
    current_line = 0
    current_rhs: list[str] = []

    def finish_current() -> None:
        nonlocal current_name, current_line, current_rhs
        if current_name is None:
            return
        rhs = "\n".join(current_rhs).strip()
        if not rhs:
            validation.fail(path, f"line {current_line}: rule <{current_name}> has no production")
        rules.append(BnfRule(current_name, path, current_line, rhs))
        current_name = None
        current_line = 0
        current_rhs = []

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue

        match = RULE_RE.match(line)
        if match:
            finish_current()
            current_name = match.group(1).strip()
            current_line = line_number
            current_rhs = [match.group(2)]
            previous_line = seen_in_file.get(current_name)
            if previous_line is not None:
                validation.fail(
                    path,
                    f"line {line_number}: duplicate rule <{current_name}> previously defined on line {previous_line}",
                )
            seen_in_file[current_name] = line_number
            continue

        if "::=" in line:
            validation.fail(path, f"line {line_number}: malformed rule definition")
        elif current_name is None:
            validation.fail(path, f"line {line_number}: content before first rule")
        else:
            current_rhs.append(line)

    finish_current()
    return rules


def validate_bnf_grammar_files(validation: Validation) -> None:
    all_rules: list[BnfRule] = []
    for path in bnf_files():
        text = path.read_text(encoding="utf-8")
        validate_balanced_delimiters(path, text, validation)
        all_rules.extend(parse_bnf_rules(path, validation))

    defined_rules = {rule.name for rule in all_rules}
    for rule in all_rules:
        for referenced_rule in sorted(set(REF_RE.findall(rule.rhs))):
            if referenced_rule not in defined_rules:
                validation.fail(
                    rule.path,
                    f"line {rule.line}: <{rule.name}> references undefined <{referenced_rule}>",
                )
    print(f"OK: checked {len(bnf_files())} BNF grammar files with {len(all_rules)} rule definitions")


def extract_function_calls(text: str, function_name: str) -> list[str]:
    calls: list[str] = []
    needle = f"{function_name}("
    cursor = 0
    while True:
        start = text.find(needle, cursor)
        if start < 0:
            return calls

        index = start + len(needle)
        depth = 1
        in_string = False
        while index < len(text):
            char = text[index]
            if char == '"' and not is_escaped(text, index):
                in_string = not in_string
            elif not in_string and char == "(":
                depth += 1
            elif not in_string and char == ")":
                depth -= 1
                if depth == 0:
                    calls.append(text[start + len(needle) : index].strip())
                    cursor = index + 1
                    break
            index += 1
        else:
            return calls


def validate_string_with_definition(
    path: Path,
    value: str,
    definition_name: str,
    validators: dict[str, Draft7Validator],
    validation: Validation,
) -> None:
    validator = validators[definition_name]
    errors = list(validator.iter_errors(value))
    if errors:
        validation.fail(path, f"{definition_name} does not accept {value!r}: {errors[0].message}")


def validate_bnf_examples(common_schema: dict[str, Any], validation: Validation) -> None:
    schema_path = JSON_DIR / "aas-queries-and-access-rules-schema.json"
    validators = {
        definition_name: definition_validator(schema_path, common_schema, definition_name)
        for definition_name in [
            "FieldIdentifier",
            "FragmentFieldIdentifier",
            "IdentifiableIdentifier",
            "ReferableIdentifier",
            "DescriptorIdentifier",
            "ReferenceIdentifier",
        ]
    }

    json_stems = {path.stem for path in example_json_files()}
    bnf_stems = {path.stem for path in example_bnf_files()}
    for missing in sorted(bnf_stems - json_stems):
        validation.fail(EXAMPLES_DIR / f"{missing}.bnf", "missing matching JSON example")
    for missing in sorted(json_stems - bnf_stems):
        validation.fail(EXAMPLES_DIR / f"{missing}.json", "missing matching BNF example")

    for path in example_bnf_files():
        text = path.read_text(encoding="utf-8")
        validate_balanced_delimiters(path, text, validation)
        validate_bnf_example_identifiers(path, text, validators, validation)

    print(f"OK: checked {len(example_bnf_files())} BNF examples")


def validate_bnf_example_identifiers(
    path: Path,
    text: str,
    validators: dict[str, Draft7Validator],
    validation: Validation,
) -> None:
    for line in text.splitlines():
        object_match = OBJECT_LINE_RE.match(line)
        if object_match:
            keyword = object_match.group(1)
            value = object_match.group(2).strip()
            validate_string_with_definition(path, value, OBJECT_DEFINITION[keyword], validators, validation)

        fragment_match = FRAGMENT_LINE_RE.match(line)
        if fragment_match:
            validate_string_with_definition(
                path,
                fragment_match.group(1),
                "FragmentFieldIdentifier",
                validators,
                validation,
            )

    for value in extract_function_calls(text, "REFERENCE"):
        validate_string_with_definition(path, value, "ReferenceIdentifier", validators, validation)

    text_without_strings, _ = without_quoted_literals(text)
    for match in FIELD_TOKEN_RE.finditer(text_without_strings):
        value = match.group(0)
        if "(" in value:
            continue
        validate_string_with_definition(path, value, "FieldIdentifier", validators, validation)


def main() -> int:
    validation = Validation()
    common_schema = validate_json_artifacts(validation)
    validate_bnf_grammar_files(validation)
    if isinstance(common_schema, dict):
        validate_bnf_examples(common_schema, validation)

    validation.assert_ok()
    print("OK: spec artifact validation completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
