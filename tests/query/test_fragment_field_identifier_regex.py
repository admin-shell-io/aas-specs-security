import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMMON_SCHEMA = ROOT / "documentation/IDTA-01004/modules/ROOT/partials/json/aas-queries-and-access-rules-schema.json"


def schema_pattern(schema_path, definition):
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
    return schema["definitions"][definition]["pattern"]


class FragmentFieldIdentifierRegexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pattern = schema_pattern(COMMON_SCHEMA, "FragmentFieldIdentifier")
        cls.fragment_field_identifier = re.compile(cls.pattern)

    def assert_allowed(self, value):
        self.assertIsNotNone(
            self.fragment_field_identifier.fullmatch(value),
            f"Expected FragmentFieldIdentifier to allow: {value}",
        )

    def assert_not_allowed(self, value):
        self.assertIsNone(
            self.fragment_field_identifier.fullmatch(value),
            f"Expected FragmentFieldIdentifier to reject: {value}",
        )

    def test_allowed_fragment_field_identifiers(self):
        allowed = [
            "$aas#idShort",
            "$aas#assetInformation.assetType",
            "$aas#assetInformation.globalAssetId",
            "$aas#assetInformation.specificAssetIds",
            "$aas#assetInformation.specificAssetIds[]",
            "$aas#assetInformation.specificAssetIds[0]",
            "$aas#assetInformation.specificAssetIds[].externalSubjectId",
            "$aas#assetInformation.specificAssetIds[].externalSubjectId.keys",
            "$aas#assetInformation.specificAssetIds[].externalSubjectId.keys[]",
            "$aas#assetInformation.specificAssetIds[].externalSubjectId.keys[0]",
            "$aas#submodels",
            "$aas#submodels[]",
            "$aas#submodels[0]",
            "$aas#submodels[].keys",
            "$aas#submodels[].keys[]",
            "$aas#submodels[].keys[0]",
            "$sm#semanticId",
            "$sm#semanticId.keys",
            "$sm#semanticId.keys[]",
            "$sm#semanticId.keys[0]",
            "$sm#supplementalSemanticIds",
            "$sm#supplementalSemanticIds[]",
            "$sm#supplementalSemanticIds[0]",
            "$sm#supplementalSemanticIds[].keys",
            "$sm#supplementalSemanticIds[].keys[]",
            "$sm#supplementalSemanticIds[0].keys[0]",
            "$sm#idShort",
            "$sme",
            "$sme.AddressInformation",
            "$sme.AddressInformation[]",
            "$sme.AddressInformation[0]",
            "$sme.AddressInformation.Zipcode",
            "$sme.AddressInformation[]#value",
            "$sme.AddressInformation#semanticId",
            "$sme.AddressInformation#semanticId.keys",
            "$sme.AddressInformation#semanticId.keys[]",
            "$sme.AddressInformation#supplementalSemanticIds",
            "$sme.AddressInformation#supplementalSemanticIds[]",
            "$sme.AddressInformation#supplementalSemanticIds[].keys",
            "$sme.AddressInformation#supplementalSemanticIds[].keys[]",
            "$sme#idShort",
            "$sme#value",
            "$sme#valueType",
            "$sme#language",
            "$cd#idShort",
            "$aasdesc#idShort",
            "$aasdesc#description",
            "$aasdesc#displayName",
            "$aasdesc#extension",
            "$aasdesc#administration",
            "$aasdesc#assetKind",
            "$aasdesc#assetType",
            "$aasdesc#globalAssetId",
            "$aasdesc#specificAssetIds",
            "$aasdesc#specificAssetIds[]",
            "$aasdesc#specificAssetIds[].externalSubjectId.keys[]",
            "$aasdesc#endpoints",
            "$aasdesc#endpoints[]",
            "$aasdesc#endpoints[0]",
            "$aasdesc#submodelDescriptors",
            "$aasdesc#submodelDescriptors[]",
            "$aasdesc#submodelDescriptors[0]",
            "$aasdesc#submodelDescriptors[].semanticId",
            "$aasdesc#submodelDescriptors[].semanticId.keys[]",
            "$aasdesc#submodelDescriptors[].supplementalSemanticIds",
            "$aasdesc#submodelDescriptors[].supplementalSemanticIds[]",
            "$aasdesc#submodelDescriptors[].supplementalSemanticIds[].keys",
            "$aasdesc#submodelDescriptors[].supplementalSemanticIds[].keys[]",
            "$aasdesc#submodelDescriptors[].idShort",
            "$aasdesc#submodelDescriptors[].endpoints",
            "$aasdesc#submodelDescriptors[].endpoints[]",
            "$smdesc#semanticId",
            "$smdesc#semanticId.keys",
            "$smdesc#semanticId.keys[]",
            "$smdesc#supplementalSemanticIds",
            "$smdesc#supplementalSemanticIds[]",
            "$smdesc#supplementalSemanticIds[].keys",
            "$smdesc#supplementalSemanticIds[].keys[]",
            "$smdesc#idShort",
            "$smdesc#endpoints",
            "$smdesc#endpoints[]",
        ]

        for value in allowed:
            with self.subTest(value=value):
                self.assert_allowed(value)

    def test_not_allowed_fragment_field_identifiers(self):
        not_allowed = [
            "$aas#id",
            "$aas#assetInformation.assetKind",
            "$aas#assetInformation.specificAssetIds.name",
            "$aas#assetInformation.specificAssetIds[01]",
            "$aas#assetInformation.specificAssetIds[].name",
            "$aas#assetInformation.specificAssetIds[].value",
            "$aas#assetInformation.specificAssetIds.keys[]",
            "$aas#assetInformation.specificAssetIds.externalSubjectId.keys[]",
            "$aas#submodels[01]",
            "$aas#submodels.keys[]",
            "$aas#submodels[].type",
            "$aas#submodels[].keys[].value",
            "$sm#semanticId.type",
            "$sm#semanticId.keys[].value",
            "$sm#id",
            "$sm#supplementalSemanticIds[01]",
            "$sm#supplementalSemanticIds.type",
            "$sm#supplementalSemanticIds.keys",
            "$sm#supplementalSemanticIds[].type",
            "$sm#supplementalSemanticIds[].keys[].value",
            "$sme.1Invalid",
            "$sme.AddressInformation[01]",
            "$sme.AddressInformation#id",
            "$sme.AddressInformation#bogus",
            "$sme.AddressInformation#semanticId.type",
            "$sme.AddressInformation#semanticId.keys[].value",
            "$sme.AddressInformation#supplementalSemanticIds[01]",
            "$sme.AddressInformation#supplementalSemanticIds.type",
            "$sme.AddressInformation#supplementalSemanticIds.keys",
            "$sme.AddressInformation#supplementalSemanticIds[].keys[].value",
            "$cd#id",
            "$aasdesc#id",
            "$aasdesc#specificAssetIds.name",
            "$aasdesc#specificAssetIds[01]",
            "$aasdesc#specificAssetIds[].name",
            "$aasdesc#endpoints[01]",
            "$aasdesc#endpoints.protocolinformation.href",
            "$aasdesc#submodelDescriptors[01]",
            "$aasdesc#submodelDescriptors.endpoints[]",
            "$aasdesc#submodelDescriptors[].id",
            "$aasdesc#submodelDescriptors[].supplementalSemanticIds[01]",
            "$aasdesc#submodelDescriptors[].supplementalSemanticIds.type",
            "$aasdesc#submodelDescriptors[].supplementalSemanticIds.keys",
            "$aasdesc#submodelDescriptors[].supplementalSemanticIds[].keys[].value",
            "$aasdesc#submodelDescriptors[].endpoints.protocolinformation.href",
            "$smdesc#id",
            "$smdesc#supplementalSemanticIds[01]",
            "$smdesc#supplementalSemanticIds.type",
            "$smdesc#supplementalSemanticIds.keys",
            "$smdesc#supplementalSemanticIds[].keys[].value",
            "$smdesc#endpoints[01]",
            "$smdesc#endpoints.protocolinformation.href",
        ]

        for value in not_allowed:
            with self.subTest(value=value):
                self.assert_not_allowed(value)


if __name__ == "__main__":
    unittest.main()
