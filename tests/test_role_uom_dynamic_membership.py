from connectors import uom


def test_sections_for_role_shows_dynamic_membership_when_rule_flags_are_enabled():
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

    assert dynamic is not None
    assert dynamic["data"]["rule_type"] == "Y"
