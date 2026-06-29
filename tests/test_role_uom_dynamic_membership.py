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
            "_metadata": {"raw": {"role_query_rule_on": "Y", "qryname_sec": "SEC_QUERY", "pc_event_type": "3"}},
        }

        sections = uom.sections_for_role(role)
        dynamic = next((s for s in sections if s["name"] == "Dynamic Membership"), None)

        self.assertIsNotNone(dynamic)
        self.assertEqual(dynamic["data"]["rule_type"], "Dynamic Query")
        labels = [item.get("label", "") for item in dynamic["items"]]
        self.assertTrue(any("Security Query" in label for label in labels))
        self.assertTrue(any("PeopleCode Event" in label for label in labels))


if __name__ == "__main__":
    unittest.main()
