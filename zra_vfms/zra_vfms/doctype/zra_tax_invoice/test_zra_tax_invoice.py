# Copyright (c) 2026, Administrator and Contributors
# See license.txt

import frappe
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from frappe.tests import IntegrationTestCase, UnitTestCase

from zra_vfms.zra_vfms.doctype.zra_tax_invoice.zra_tax_invoice import (
	create_tax_invoice,
	get_tax_invoice,
	update_tax_invoice,
)


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
		# No ZRA Setting exists for _Test Company, so submitting does not
		# trigger the on_submit tax-send hook.
		self.sinv = create_sales_invoice()

	def tearDown(self):
		frappe.db.rollback()

	def test_zra_tax_invoice_creation(self):
		doc = frappe.get_doc(
			{
				"doctype": "ZRA Tax Invoice",
				"sales_invoice": self.sinv.name,
				"company": self.sinv.company,
				"tax_type": "VAT",
				"status": "Pending",
			}
		)
		doc.insert()

		self.assertEqual(doc.doctype, "ZRA Tax Invoice")
		self.assertIsNotNone(doc.name)

		doc.delete()

	def test_company_is_auto_set_from_sales_invoice(self):
		"""ZRATaxInvoice.validate backfills company from the linked invoice."""
		doc = frappe.get_doc(
			{
				"doctype": "ZRA Tax Invoice",
				"sales_invoice": self.sinv.name,
				"tax_type": "VAT",
				"status": "Pending",
			}
		)
		doc.insert()

		self.assertEqual(doc.company, self.sinv.company)

		doc.delete()

	def test_create_and_get_tax_invoice_round_trip(self):
		created = create_tax_invoice(
			sales_invoice=self.sinv.name,
			company=self.sinv.company,
			tax_type="VAT",
		)

		fetched = get_tax_invoice(self.sinv.name, "VAT")

		self.assertIsNotNone(fetched)
		self.assertEqual(fetched.name, created.name)

		fetched.delete()

	def test_update_tax_invoice_parses_vfms_response(self):
		tax_inv = create_tax_invoice(
			sales_invoice=self.sinv.name,
			company=self.sinv.company,
			tax_type="VAT",
		)

		updated = update_tax_invoice(
			tax_inv.name,
			status="Success",
			response_data={
				"receiptNumber": "RCPT-42",
				"issueDate": "2026-03-05T19:02:58.103+03:00",
			},
		)

		self.assertEqual(updated.status, "Success")
		self.assertEqual(updated.receipt_number, "RCPT-42")
		self.assertEqual(str(updated.receipt_time), "2026-03-05 19:02:58.103000")

		updated.delete()
