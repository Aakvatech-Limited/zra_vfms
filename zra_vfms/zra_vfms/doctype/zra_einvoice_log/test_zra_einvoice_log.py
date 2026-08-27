# Copyright (c) 2026, Administrator and Contributors
# See license.txt

import frappe
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from frappe.tests import IntegrationTestCase, UnitTestCase

from zra_vfms.zra_vfms.doctype.zra_einvoice_log.zra_einvoice_log import (
	create_log,
	increment_retry,
	update_log,
)


class UnitTestZRAEinvoiceLog(UnitTestCase):
	"""
	Unit tests for ZRA Einvoice Log.
	Use this class for testing individual functions and methods.
	"""


class IntegrationTestZRAEinvoiceLog(IntegrationTestCase):
	"""
	Integration tests for ZRA Einvoice Log.
	Use this class for testing interactions with the database.
	"""

	def setUp(self):
		# No ZRA Setting exists for _Test Company, so submitting does not
		# trigger the on_submit tax-send hook.
		self.sinv = create_sales_invoice()

	def tearDown(self):
		frappe.db.rollback()

	def test_zra_einvoice_log_creation(self):
		doc = frappe.get_doc(
			{
				"doctype": "ZRA Einvoice Log",
				"sales_invoice": self.sinv.name,
				"request_type": "Normal Sales",
				"status": "Pending",
			}
		)
		doc.insert()

		self.assertEqual(doc.doctype, "ZRA Einvoice Log")
		self.assertIsNotNone(doc.name)
		self.assertEqual(doc.sales_invoice, self.sinv.name)

		doc.delete()

	def test_create_log_stores_request_payload_as_json(self):
		log = create_log(
			sales_invoice=self.sinv.name,
			request_type="Normal Sales",
			request_payload={"amount": 100},
		)

		self.assertEqual(log.status, "Pending")
		self.assertIn('"amount": 100', log.request_payload)

		log.delete()

	def test_update_log_sets_status_and_response(self):
		log = create_log(sales_invoice=self.sinv.name, request_type="Normal Sales")

		updated = update_log(log.name, response_payload={"receiptNumber": "RCPT-1"}, status="Success")

		self.assertEqual(updated.status, "Success")
		self.assertIn("RCPT-1", updated.response_payload)

		updated.delete()

	def test_increment_retry_counts_up(self):
		log = create_log(sales_invoice=self.sinv.name, request_type="Normal Sales")
		self.assertEqual(frappe.db.get_value("ZRA Einvoice Log", log.name, "retry_count") or 0, 0)

		increment_retry(log.name)
		increment_retry(log.name)

		self.assertEqual(frappe.db.get_value("ZRA Einvoice Log", log.name, "retry_count"), 2)

		frappe.get_doc("ZRA Einvoice Log", log.name).delete()
