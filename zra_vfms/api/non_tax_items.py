# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime

from zra_vfms.utils.utils import send_request


def fetch_non_tax_items():
	"""Weekly scheduled job: fetch non-taxable items from VFMS.

	Per VFMS API Guide v1.5 Section 3.6 (Get Non-tax Items):
	- Endpoint: /vfms/api/getNonTaxItems/
	- Request: no payload required (GET-style, but HTTP POST)
	- Response: array of {id, unitMeasure, isTaxable, name}

	Iterates over all companies with active ZRA Settings and fetches
	non-tax items once per unique base_url to avoid duplicating calls
	to the same VFMS server.
	"""
	settings = frappe.get_all(
		"ZRA Setting",
		filters={"docstatus": 0},
		fields=["name", "company", "base_url"],
	)

	if not settings:
		return

	# Deduplicate by base_url — same VFMS server returns same list
	processed_urls = set()

	for row in settings:
		if row.base_url in processed_urls:
			continue

		setting = frappe.get_cached_doc("ZRA Setting", row.name)

		try:
			fetch_and_sync_items(setting)
			processed_urls.add(row.base_url)
		except Exception as e:
			msg = f"{row.company}: {e!s} <br><br>Traceback:</b><br>{frappe.get_traceback()}"
			frappe.log_error(
				title="ZRA VFMS: Failed to fetch non-tax items",
				message=msg,
				reference_doctype="ZRA Setting",
				reference_name=row.name,
			)


def fetch_and_sync_items(setting):
	"""Fetch non-tax items from VFMS and upsert into ZRA Non Tax Item.

	Args:
	    setting: ZRA Setting document.
	"""
	# getNonTaxItems has no request payload
	result = send_request(setting, "Get Non-Tax Items", {}, "VAT")

	if not result["success"]:
		frappe.log_error(
			title=f"ZRA VFMS: Non-tax items fetch failed for {setting.company}",
			message=result["error"],
			reference_doctype="ZRA Setting",
			reference_name=setting.name,
		)
		frappe.throw(result["error"])

	items = result["response"]
	if not items or not isinstance(items, list):
		return {"new_count": 0, "updated_count": 0}

	synced_at = now_datetime()
	new_count = 0
	updated_count = 0

	for item_data in items:
		vfms_id = item_data.get("id")
		if not vfms_id:
			continue

		item_name = item_data.get("name") or ""
		unit_measure = item_data.get("unitMeasure") or ""

		existing = frappe.db.get_value(
			"ZRA Non Tax Item",
			{"item_id": vfms_id},
			"name",
		)

		if existing:
			frappe.db.set_value(
				"ZRA Non Tax Item",
				existing,
				{
					"item_name": item_name,
					"unit_measure": unit_measure,
					"last_synced": synced_at,
				},
				update_modified=True,
			)
			updated_count += 1
		else:
			doc = frappe.new_doc("ZRA Non Tax Item")
			doc.item_id = vfms_id
			doc.item_name = item_name
			doc.unit_measure = unit_measure
			doc.last_synced = synced_at
			doc.company = setting.company
			doc.insert(ignore_permissions=True)
			new_count += 1

	frappe.db.commit()  # nosemgrep

	if new_count or updated_count:
		frappe.log_error(
			title=f"ZRA VFMS: Non-tax items synced for {setting.company}",
			message=f"New: {new_count}, Updated: {updated_count}",
			reference_doctype="ZRA Setting",
			reference_name=setting.name,
		)

	return {"new_count": new_count, "updated_count": updated_count}
