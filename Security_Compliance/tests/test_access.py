from utils.validation import can_export, tabs_for_role


def test_viewer_has_no_export_permission():
    assert can_export("viewer") is False


def test_analyst_and_admin_can_export():
    assert can_export("analyst") is True
    assert can_export("admin") is True


def test_unknown_role_gets_no_tabs():
    assert tabs_for_role("nonexistent-role") == []


def test_viewer_cannot_see_safety_reports_or_audit_log():
    tabs = tabs_for_role("viewer")
    assert "Safety Reports" not in tabs
    assert "Audit Log" not in tabs


def test_analyst_cannot_see_safety_reports_or_audit_log():
    tabs = tabs_for_role("analyst")
    assert "Safety Reports" not in tabs
    assert "Audit Log" not in tabs


def test_admin_sees_every_tab():
    admin_tabs = set(tabs_for_role("admin"))
    for role in ("viewer", "analyst"):
        assert set(tabs_for_role(role)).issubset(admin_tabs)
