import unittest
from unittest.mock import patch

from connectors import psdb


class PermissionDecodingTests(unittest.TestCase):
    def test_explain_operator_component_access_enriches_grant_paths_with_permissionlist_detail(self):
        fake_access = [{
            "roleuser": "JSMITH",
            "rolename": "ROLE1",
            "classid": "PL1",
            "pnlgrpname": "COMP1",
            "authorizedactions": 3,
            "displayonly": "N",
        }]

        with patch.object(psdb, "operator_detail", return_value={"oprid": "JSMITH"}), \
             patch.object(psdb, "component", return_value={"pnlgrpname": "COMP1"}), \
             patch.object(psdb, "operator_roles_full", return_value=[{"rolename": "ROLE1"}]), \
             patch.object(psdb, "operator_permissionlists", return_value=[]), \
             patch.object(psdb, "component_permissionlists", return_value=[]), \
             patch.object(psdb, "component_access", return_value=fake_access), \
             patch.object(psdb, "permissionlist", return_value={"classid": "PL1", "classdefndesc": "Payroll Access"}):
            result = psdb.explain_operator_component_access("HCM", "JSMITH", "COMP1")

        self.assertTrue(result["has_access"])
        self.assertEqual(result["grant_paths"][0]["permissionlist_detail"]["classid"], "PL1")
        self.assertEqual(result["grant_paths"][0]["permissionlist_detail"]["classdefndesc"], "Payroll Access")
        self.assertEqual(result["grant_paths"][0]["decoded_actions"], ["Add", "Update/Display"])
        self.assertIn("permissionlist:PL1", result["grant_paths"][0]["path_summary"])

    def test_explain_operator_menu_access_enriches_grant_paths_with_permissionlist_detail(self):
        fake_menus = [{
            "menuname": "MENU1",
            "rolename": "ROLE1",
            "classid": "PL1",
            "barname": "NAV",
            "baritemname": "ITEM1",
            "authorizedactions": 5,
            "displayonly": "N",
        }]

        with patch.object(psdb, "operator_menus", return_value=fake_menus), \
             patch.object(psdb, "permissionlist", return_value={"classid": "PL1", "classdefndesc": "Payroll Access"}):
            result = psdb.explain_operator_menu_access("HCM", "JSMITH", "MENU1")

        self.assertTrue(result["has_access"])
        self.assertEqual(result["grant_paths"][0]["permissionlist_detail"]["classid"], "PL1")
        self.assertEqual(result["grant_paths"][0]["permissionlist_detail"]["classdefndesc"], "Payroll Access")
        self.assertEqual(result["grant_paths"][0]["decoded_actions"], ["Add", "Update/Display All"])
        self.assertIn("menu:MENU1", result["grant_paths"][0]["path_summary"])


if __name__ == "__main__":
    unittest.main()
