import unittest

from connectors import uom


class PermissionlistUomTests(unittest.TestCase):
    def test_sections_for_permissionlist_shows_dynamic_membership_when_rules_are_present(self):
        permissionlist = {
            "name": "HCM45",
            "type": "permissionlist",
            "display_name": "HCM45",
            "status": "available",
            "description": "",
            "_relationships": {},
            "_graph": {"nodes": [], "edges": []},
            "_metadata": {"raw": {"classdefndesc": "HCM Approval", "dynamic_sw": "Y"}},
        }

        sections = uom.sections_for_permissionlist(permissionlist)
        dynamic = next((s for s in sections if s["name"] == "Dynamic Membership"), None)

        self.assertIsNotNone(dynamic)
        self.assertEqual(dynamic["data"]["rule_type"], "Y")


if __name__ == "__main__":
    unittest.main()
