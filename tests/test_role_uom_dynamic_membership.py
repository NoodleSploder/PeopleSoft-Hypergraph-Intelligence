import unittest

from connectors import uom


class RoleUomDynamicMembershipTests(unittest.TestCase):
    def test_sections_for_role_shows_dynamic_membership_when_rule_flags_are_enabled(self):
        role = {
            "name": "JOB_REQUISITION_AUTHORIZOR",
            "type": "role",
            "display_name": "JOB_REQUISITION_AUTHORIZOR",
            "status": "available",
            "description": "",
            "_relationships": {},
            "_graph": {"nodes": [], "edges": []},
            "_metadata": {"raw": {"role_query_rule_on": "Y"}},
        }

        sections = uom.sections_for_role(role)
        dynamic = next((s for s in sections if s["name"] == "Dynamic Membership"), None)

        self.assertIsNotNone(dynamic)
        self.assertEqual(dynamic["data"]["rule_type"], "Dynamic Query")


if __name__ == "__main__":
    unittest.main()
