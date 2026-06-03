# Copyright (c) 2026, Administrator and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase


class UnitTestZRATaxInvoice(UnitTestCase):
    """
    Unit tests for ZRA Tax Invoice.
    Use this class for testing individual functions and methods.
    """


class IntegrationTestZRATaxInvoice(IntegrationTestCase):
    """
    Integration tests for ZRA Tax Invoice.
    Use this class for testing interactions with the database.
    """

    def setUp(self):
        """Set up test data before each test."""

    def tearDown(self):
        """Clean up test data after each test."""

    def test_zra_tax_invoice_creation(self):
        """Test creating a new ZRA Tax Invoice."""
        # Create test document
        doc = frappe.get_doc(
            {
                "doctype": "ZRA Tax Invoice",
                # Add required fields here
            }
        )
        doc.insert()

        # Assertions
        self.assertEqual(doc.doctype, "ZRA Tax Invoice")
        self.assertIsNotNone(doc.name)

        # Clean up
        doc.delete()
