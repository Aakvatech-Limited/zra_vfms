# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from zra_vfms.api.sales_invoice import on_submit, process_tax_submission


def make_zra_setting(**kwargs):
	setting = frappe.get_doc(
		{
			"doctype": "ZRA Setting",
			"company": "_Test Company",
			"base_url": "https://vfms.zra.example",
			"zra_start_date": kwargs.pop("zra_start_date", today()),
			"auto_send_tax": kwargs.pop("auto_send_tax", 1),
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
	)
	setting.update(kwargs)
	setting.insert(ignore_permissions=True)
	return setting


class IntegrationTestZraVfmsSalesInvoiceHook(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()
		frappe.db.delete("ZRA Setting", {"company": "_Test Company"})
		frappe.db.delete("ZRA Tax Invoice")
		frappe.db.delete("ZRA Einvoice Log")
		frappe.db.commit()

	def test_on_submit_skips_when_no_zra_setting(self):
		sinv = create_sales_invoice()
		# "Not Sent" is the field's static default; the hook never touched it.
		self.assertEqual(frappe.db.get_value("Sales Invoice", sinv.name, "tax_status"), "Not Sent")

	def test_on_submit_skips_when_non_taxable(self):
		make_zra_setting()
		sinv = create_sales_invoice(do_not_submit=True)
		sinv.is_non_taxable = 1
		sinv.submit()

		self.assertEqual(frappe.db.get_value("Sales Invoice", sinv.name, "tax_status"), "Not Sent")

	def test_on_submit_skips_when_return_invoice(self):
		make_zra_setting()

		with patch(
			"zra_vfms.api.sales_invoice.send_request",
			return_value={"success": True, "response": {"receiptNumber": "RCPT-1"}, "error": None},
		) as mock_send_request:
			original = create_sales_invoice()
			credit_note = create_sales_invoice(is_return=1, return_against=original.name, qty=-1)

		# on_submit ran for the original invoice only; the return invoice's
		# on_submit returned early without calling send_request at all.
		mock_send_request.assert_called_once()
		self.assertEqual(frappe.db.get_value("Sales Invoice", credit_note.name, "tax_status"), "Not Sent")

	def test_on_submit_skips_when_auto_send_disabled(self):
		make_zra_setting(auto_send_tax=0)
		sinv = create_sales_invoice()

		self.assertEqual(frappe.db.get_value("Sales Invoice", sinv.name, "tax_status"), "Not Sent")

	def test_on_submit_skips_before_zra_start_date(self):
		make_zra_setting(zra_start_date=add_days(today(), 1))
		sinv = create_sales_invoice()

		self.assertEqual(frappe.db.get_value("Sales Invoice", sinv.name, "tax_status"), "Not Sent")

	def test_on_submit_sends_tax_and_records_success(self):
		make_zra_setting()

		with patch(
			"zra_vfms.api.sales_invoice.send_request",
			return_value={"success": True, "response": {"receiptNumber": "RCPT-1"}, "error": None},
		):
			sinv = create_sales_invoice()

		self.assertEqual(frappe.db.get_value("Sales Invoice", sinv.name, "tax_status"), "Success")

		tax_inv = frappe.get_last_doc("ZRA Tax Invoice", filters={"sales_invoice": sinv.name})
		self.assertEqual(tax_inv.status, "Success")
		self.assertEqual(tax_inv.receipt_number, "RCPT-1")

	def test_failed_submission_does_not_leave_a_partial_submit(self):
		"""process_tax_submission used to call frappe.db.commit() before
		frappe.throw() on failure. Per the v16 migration guide, committing
		inside a document hook is unsafe: it flushes the *entire* current
		transaction, so the Sales Invoice's own docstatus=1 update would be
		made durable even though the request-level response is a thrown
		error. With the commit removed, nothing is durable until the request
		ends, so a rollback — what frappe's request handler performs on an
		unhandled error — undoes the whole submit atomically.
		"""
		make_zra_setting()
		sinv = create_sales_invoice(do_not_submit=True)

		with patch(
			"zra_vfms.api.sales_invoice.send_request",
			return_value={"success": False, "response": None, "error": "VFMS unreachable"},
		):
			with self.assertRaises(frappe.ValidationError):
				sinv.submit()

		# Simulate the rollback frappe's request handler performs on an
		# unhandled error escaping a whitelisted call. The invoice itself was
		# inserted in this same uncommitted transaction, so the rollback
		# undoes the insert too, not just the submit.
		frappe.db.rollback()

		self.assertIsNone(frappe.db.get_value("Sales Invoice", sinv.name, "docstatus"))
		self.assertEqual(frappe.db.count("ZRA Tax Invoice", {"sales_invoice": sinv.name}), 0)

	def test_process_tax_submission_returns_pending_without_setting(self):
		sinv = create_sales_invoice(do_not_submit=True)

		result = process_tax_submission(sinv.name)

		self.assertFalse(result["success"])
		self.assertEqual(frappe.db.get_value("Sales Invoice", sinv.name, "tax_status"), "Pending")

	def test_on_submit_is_noop_without_hook_side_effects_for_non_taxable(self):
		make_zra_setting()
		sinv = create_sales_invoice(do_not_submit=True)
		sinv.is_non_taxable = 1

		# Calling the hook function directly must not raise even though no
		# ZRA records exist yet for this invoice.
		on_submit(sinv, "on_submit")
