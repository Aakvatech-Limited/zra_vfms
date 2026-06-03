# Copyright (c) 2026, Administrator and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ZRANonTaxItem(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        # TODO: Add type hints for fields here
    # end: auto-generated types

    def validate(self):
        """Validate document before saving."""

    def before_save(self):
        """Called before document is saved."""

    def on_update(self):
        """Called after document is saved."""

    def on_submit(self):
        """Called when document is submitted."""

    def on_cancel(self):
        """Called when document is cancelled."""

    def on_trash(self):
        """Called before document is deleted."""
