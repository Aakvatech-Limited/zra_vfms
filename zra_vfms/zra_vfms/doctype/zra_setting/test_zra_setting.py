# Copyright (c) 2026, Administrator and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase


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

	def setUp(self):
		"""Set up test data before each test."""

	def tearDown(self):
		"""Clean up test data after each test."""

	def test_zra_setting_creation(self):
		"""Test creating a new ZRA Setting."""
		# Create test document
		doc = frappe.get_doc(
			{
				"doctype": "ZRA Setting",
				# Add required fields here
			}
		)
		doc.insert()

		# Assertions
		self.assertEqual(doc.doctype, "ZRA Setting")
		self.assertIsNotNone(doc.name)

		# Clean up
		doc.delete()
