# Copyright (c) 2026, Administrator and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import today


class UnitTestZRACredential(UnitTestCase):
	"""
	Unit tests for ZRA Credential.
	Use this class for testing individual functions and methods.
	"""


class IntegrationTestZRACredential(IntegrationTestCase):
	"""
	Integration tests for ZRA Credential.

	ZRA Credential is a child table (istable=1) of ZRA Setting, so rows are
	only ever created through the parent document.
	"""

	def tearDown(self):
		frappe.db.rollback()

	def test_zra_credential_creation_via_parent(self):
		setting = frappe.get_doc(
			{
				"doctype": "ZRA Setting",
				"company": "_Test Company",
				"base_url": "https://vfms.zra.example",
				"zra_start_date": today(),
				"credentials": [
					{"tax_type": "VAT", "integration_id": "int-1", "token_id": "s3cr3t", "enabled": 1}
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

		self.assertEqual(len(setting.credentials), 1)
		row = setting.credentials[0]
		self.assertEqual(row.doctype, "ZRA Credential")
		self.assertEqual(row.tax_type, "VAT")
		self.assertEqual(row.get_password("token_id"), "s3cr3t")

		setting.delete()
