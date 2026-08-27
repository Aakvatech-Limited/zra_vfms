# Copyright (c) 2026, Administrator and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import today


class UnitTestZRASetting(UnitTestCase):
	"""
	Unit tests for ZRA Setting.
	Use this class for testing individual functions and methods.
	"""


class IntegrationTestZRASetting(IntegrationTestCase):
	"""
	Integration tests for ZRA Setting.
	Use this class for testing interactions with the database.
	"""

	def tearDown(self):
		frappe.db.rollback()

	def test_zra_setting_creation(self):
		doc = frappe.get_doc(
			{
				"doctype": "ZRA Setting",
				"company": "_Test Company",
				"base_url": "https://vfms.zra.example",
				"zra_start_date": today(),
				"credentials": [
					{
						"tax_type": "VAT",
						"integration_id": "int-1",
						"token_id": "secret-token",
						"enabled": 1,
					}
				],
				"endpoints": [
					{
						"endpoint_name": "Normal Sales",
						"endpoint_path": "/vfms/api/normalSales/",
						"request_type": "Normal Sales",
						"http_method": "POST",
					}
				],
			}
		)
		doc.insert()

		self.assertEqual(doc.doctype, "ZRA Setting")
		self.assertEqual(doc.name, "_Test Company")
		self.assertEqual(len(doc.credentials), 1)
		self.assertEqual(len(doc.endpoints), 1)

		doc.delete()

	def test_zra_setting_name_is_company(self):
		"""autoname is `field:company`, so the record name must equal the company."""
		doc = frappe.get_doc(
			{
				"doctype": "ZRA Setting",
				"company": "_Test Company",
				"base_url": "https://vfms.zra.example",
				"zra_start_date": today(),
				"credentials": [
					{"tax_type": "VAT", "integration_id": "int-1", "token_id": "secret", "enabled": 1}
				],
				"endpoints": [
					{
						"endpoint_name": "Normal Sales",
						"endpoint_path": "/vfms/api/normalSales/",
						"request_type": "Normal Sales",
					}
				],
			}
		).insert()

		self.assertEqual(doc.name, doc.company)
		doc.delete()
