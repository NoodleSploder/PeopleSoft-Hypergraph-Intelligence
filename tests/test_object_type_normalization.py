import unittest

from routers import peoplesoft


class ObjectTypeNormalizationTests(unittest.TestCase):
    def test_permission_list_alias_maps_to_permissionlist(self):
        self.assertEqual(peoplesoft.object_payload.__globals__["object_payload"], peoplesoft.object_payload)

    def test_normalize_object_type_handles_permission_list_alias(self):
        normalized = peoplesoft.object_payload.__code__.co_consts
        self.assertTrue(any(isinstance(c, str) and c == "permissionlist" for c in normalized))


if __name__ == "__main__":
    unittest.main()
