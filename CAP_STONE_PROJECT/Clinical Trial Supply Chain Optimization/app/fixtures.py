"""Versioned synthetic fixtures — CLAUDE.md §5. Not real patient, site, or shipment data."""
from app.models import Enrollment, Inventory, Shipment, Site

AUTHORIZED_STUDY = "PH3-ONC-2027"

SITES: dict[str, Site] = {
    "IND001": Site(
        site_id="IND001", study_id="PH3-ONC-2027", country="Germany", status="Active",
        enrollment=Enrollment(actual=34, dropout_rate=0.05, trend_per_week=1.0, timestamp="2026-09-25T08:00:00Z"),
        inventory=Inventory(usable_kits=260, safety_stock=40, pack_size=10, timestamp="2026-09-25T07:30:00Z"),
        shipment=Shipment(status="IN_TRANSIT", eta_days=6, qty=60),
        kit_per_visit=1, visit_interval_days=21,
    ),
    "IND002": Site(
        site_id="IND002", study_id="PH3-ONC-2027", country="Poland", status="Active",
        enrollment=Enrollment(actual=50, dropout_rate=0.08, trend_per_week=2.5, timestamp="2026-09-25T09:10:00Z"),
        inventory=Inventory(usable_kits=100, safety_stock=20, pack_size=10, timestamp="2026-09-25T09:00:00Z"),
        shipment=Shipment(status="PLANNED", eta_days=35, qty=80),
        kit_per_visit=1, visit_interval_days=14,
    ),
    "IND003": Site(
        site_id="IND003", study_id="PH3-ONC-2027", country="Brazil", status="Active",
        enrollment=Enrollment(actual=60, dropout_rate=0.10, trend_per_week=3.0, timestamp="2026-09-24T14:00:00Z"),
        inventory=Inventory(usable_kits=45, safety_stock=15, pack_size=10, timestamp="2026-09-25T06:00:00Z"),
        shipment=Shipment(status="DELAYED", eta_days=40, qty=70),
        kit_per_visit=1, visit_interval_days=14,
    ),
    "IND004": Site(
        site_id="IND004", study_id="PH3-ONC-2027", country="India", status="Active",
        enrollment=Enrollment(actual=None, dropout_rate=0.05, trend_per_week=1.5, timestamp="2026-09-25T05:00:00Z"),
        inventory=Inventory(usable_kits=120, safety_stock=20, pack_size=10, timestamp="2026-09-25T05:00:00Z"),
        shipment=Shipment(status="IN_TRANSIT", eta_days=8, qty=40),
        kit_per_visit=1, visit_interval_days=21,
    ),
    "IND005": Site(
        site_id="IND005", study_id="PH3-ONC-2027", country="Spain", status="Active",
        enrollment=Enrollment(actual=28, dropout_rate=0.04, trend_per_week=0.8, timestamp="2026-09-25T10:00:00Z"),
        inventory=Inventory(usable_kits=90, safety_stock=25, pack_size=10, timestamp="2026-09-22T09:00:00Z"),
        shipment=Shipment(status="IN_TRANSIT", eta_days=10, qty=30),
        kit_per_visit=1, visit_interval_days=21,
    ),
    "IND201": Site(
        site_id="IND201", study_id="PH2-CARD-2026", country="Unlisted", status="Active",
        enrollment=Enrollment(actual=20, dropout_rate=0.05, trend_per_week=1.0, timestamp="2026-09-25T10:00:00Z"),
        inventory=Inventory(usable_kits=50, safety_stock=10, pack_size=10, timestamp="2026-09-25T10:00:00Z"),
        shipment=Shipment(status="IN_TRANSIT", eta_days=12, qty=20),
        kit_per_visit=1, visit_interval_days=21,
    ),
}
