# Copyright (c) 2026, Administrator and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import today


class UnitTestZRAEndpoint(UnitTestCase):
	"""
	Unit tests for ZRA Endpoint.
	Use this class for testing individual functions and methods.
	"""


class IntegrationTestZRAEndpoint(IntegrationTestCase):
	"""
	Integration tests for ZRA Endpoint.

	ZRA Endpoint is a child table (istable=1) of ZRA Setting, so rows are
	only ever created through the parent document.
	"""

	def tearDown(self):
		frappe.db.rollback()

	def test_zra_endpoint_creation_via_parent(self):
		setting = frappe.get_doc(
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
						"http_method": "POST",
					}
				],
			}
		).insert()

		self.assertEqual(len(setting.endpoints), 1)
		row = setting.endpoints[0]
		self.assertEqual(row.doctype, "ZRA Endpoint")
		self.assertEqual(row.parent, setting.name)
		self.assertEqual(row.parenttype, "ZRA Setting")
		self.assertEqual(row.endpoint_path, "/vfms/api/normalSales/")

		setting.delete()
