# Copyright (c) 2026, Administrator and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase


class UnitTestZRANonTaxItem(UnitTestCase):
	"""
	Unit tests for ZRA Non Tax Item.
	Use this class for testing individual functions and methods.
	"""


class IntegrationTestZRANonTaxItem(IntegrationTestCase):
	"""
	Integration tests for ZRA Non Tax Item.
	Use this class for testing interactions with the database.
	"""

	def tearDown(self):
		frappe.db.rollback()

	def test_zra_non_tax_item_creation(self):
		doc = frappe.get_doc(
			{
				"doctype": "ZRA Non Tax Item",
				"item_id": 4242,
				"item_name": "Sample Non Tax Item",
				"unit_measure": "PCS",
				"company": "_Test Company",
			}
		)
		doc.insert()

		self.assertEqual(doc.doctype, "ZRA Non Tax Item")
		self.assertIsNotNone(doc.name)
		self.assertEqual(doc.item_id, 4242)

		doc.delete()
