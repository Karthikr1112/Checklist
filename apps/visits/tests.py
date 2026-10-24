from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.checklists.models import ChecklistTemplate
from apps.core.geo import calculate_distance_meters, verify_user_at_store
from apps.stores.models import Store
from apps.visits.forms import StartVisitForm
from apps.visits.models import AuditType, Visit


class GeofenceVerificationTests(TestCase):
    def setUp(self):
        # Store 1501: Attakulangara SC (8.479712, 76.948793)
        self.store = Store.objects.create(
            code="1501",
            name="ATTAKULANGARA SC",
            city="Thiruvananthapuram",
            latitude=Decimal("8.479712"),
            longitude=Decimal("76.948793"),
            geofence_radius_meters=250,
        )

        self.cm_user = User.objects.create_user(
            email="cm@example.com",
            password="pass",
            role=Role.CLUSTER_MANAGER,
        )

        self.store.cluster_manager = self.cm_user
        self.store.save()

        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="pass",
            role=Role.ADMIN,
        )

        self.template = ChecklistTemplate.objects.create(
            name="Cluster Manager Store Visit Checklist",
            audience=ChecklistTemplate.Audience.CLUSTER_MANAGER,
            is_active=True,
            version=1,
        )

    def test_distance_calculation(self):
        # Same location should be ~0 distance
        d = calculate_distance_meters(8.479712, 76.948793, 8.479712, 76.948793)
        self.assertAlmostEqual(d, 0.0, places=1)

        # 100 meters away approx (0.0009 deg lat is ~100m)
        d_close = calculate_distance_meters(8.479712, 76.948793, 8.480612, 76.948793)
        self.assertTrue(90 <= d_close <= 110)

    def test_verify_user_at_store_within_radius(self):
        # User is right at the store (~10m away)
        is_valid, err, dist = verify_user_at_store(
            store=self.store,
            user_latitude=Decimal("8.479720"),
            user_longitude=Decimal("76.948795"),
            is_admin_bypass=False,
        )
        self.assertTrue(is_valid)
        self.assertIsNone(err)
        self.assertLessEqual(dist, 250)

    def test_verify_user_at_store_outside_radius(self):
        # User is in Ulloor (8.535946, 76.927034) while trying to start visit at Attakulangara (~6.6km away)
        is_valid, err, dist = verify_user_at_store(
            store=self.store,
            user_latitude=Decimal("8.535946"),
            user_longitude=Decimal("76.927034"),
            is_admin_bypass=False,
        )
        self.assertFalse(is_valid)
        self.assertIn("Location verification failed", err)
        self.assertIn("Company rule", err)
        self.assertGreater(dist, 1000)

    def test_verify_user_at_store_admin_bypass(self):
        # Admin can bypass even if far away
        is_valid, err, dist = verify_user_at_store(
            store=self.store,
            user_latitude=Decimal("8.535946"),
            user_longitude=Decimal("76.927034"),
            is_admin_bypass=True,
        )
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_start_visit_form_enforces_geofence_for_non_admin(self):
        # Far away coordinates provided by cluster manager
        data = {
            "store": str(self.store.pk),
            "department": "CLUSTER_MANAGER",
            "visit_date": str(timezone.localdate()),
            "audit_type": AuditType.FULL,
            "user_latitude": "8.535946",
            "user_longitude": "76.927034",
        }
        form = StartVisitForm(data=data, user=self.cm_user)
        self.assertFalse(form.is_valid())
        self.assertIn("store", form.errors)
        self.assertIn("Location verification failed", form.errors["store"][0])

    def test_start_visit_form_accepts_when_at_store(self):
        # Close coordinates provided by cluster manager
        data = {
            "store": str(self.store.pk),
            "department": "CLUSTER_MANAGER",
            "visit_date": str(timezone.localdate()),
            "audit_type": AuditType.FULL,
            "user_latitude": "8.479715",
            "user_longitude": "76.948790",
        }
        form = StartVisitForm(data=data, user=self.cm_user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["store"], self.store)
        self.assertIsNotNone(form.cleaned_data.get("started_latitude"))

    def test_store_manager_start_visit_and_visibility(self):
        sm_template = ChecklistTemplate.objects.create(
            name="Store Manager Daily Store Walk Checklist",
            audience=ChecklistTemplate.Audience.STORE_MANAGER,
            is_active=True,
            version=1,
        )
        sm_user = User.objects.create_user(
            email="sm@example.com",
            password="pass",
            role=Role.STORE_MANAGER,
        )
        self.store.store_manager = sm_user
        self.store.save()

        # Check form defaults
        form = StartVisitForm(user=sm_user)
        self.assertEqual(form.fields["department"].initial, "STORE_MANAGER")

        # Submit form as SM at the store
        data = {
            "store": str(self.store.pk),
            "department": "STORE_MANAGER",
            "visit_date": str(timezone.localdate()),
            "audit_type": AuditType.FULL,
            "user_latitude": "8.479715",
            "user_longitude": "76.948790",
        }
        form = StartVisitForm(data=data, user=sm_user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["template"], sm_template)

        # Check visit visibility
        from apps.visits.selectors import visits_visible_to
        from apps.visits.services import start_visit

        visit = start_visit(
            store=self.store,
            template=sm_template,
            cluster_manager=sm_user,
            visit_date=timezone.localdate(),
            audit_type=AuditType.FULL,
        )
        visible = visits_visible_to(sm_user)
        self.assertTrue(visible.filter(pk=visit.pk).exists())
        self.assertTrue(visit.is_store_manager_checklist)

