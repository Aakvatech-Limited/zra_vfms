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

	def setUp(self):
		"""Set up test data before each test."""

	def tearDown(self):
		"""Clean up test data after each test."""

	def test_zra_non_tax_item_creation(self):
		"""Test creating a new ZRA Non Tax Item."""
		# Create test document
		doc = frappe.get_doc(
			{
				"doctype": "ZRA Non Tax Item",
				# Add required fields here
			}
		)
		doc.insert()

		# Assertions
		self.assertEqual(doc.doctype, "ZRA Non Tax Item")
		self.assertIsNotNone(doc.name)

		# Clean up
		doc.delete()
