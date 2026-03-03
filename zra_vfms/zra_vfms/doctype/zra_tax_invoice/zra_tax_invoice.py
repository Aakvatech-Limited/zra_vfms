# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ZRATaxInvoice(Document):
	def validate(self):
		self._set_company_from_invoice()

	def _set_company_from_invoice(self):
		"""Auto-set company from the linked Sales Invoice."""
		if self.sales_invoice and not self.company:
			self.company = frappe.db.get_value(
				"Sales Invoice", self.sales_invoice, "company"
			)
