# Copyright (c) 2026, Administrator and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase


class UnitTestZRACredential(UnitTestCase):
	"""
	Unit tests for ZRA Credential.
	Use this class for testing individual functions and methods.
	"""


class IntegrationTestZRACredential(IntegrationTestCase):
	"""
	Integration tests for ZRA Credential.
	Use this class for testing interactions with the database.
	"""

	def setUp(self):
		"""Set up test data before each test."""

	def tearDown(self):
		"""Clean up test data after each test."""

	def test_zra_credential_creation(self):
		"""Test creating a new ZRA Credential."""
		# Create test document
		doc = frappe.get_doc(
			{
				"doctype": "ZRA Credential",
				# Add required fields here
			}
		)
		doc.insert()

		# Assertions
		self.assertEqual(doc.doctype, "ZRA Credential")
		self.assertIsNotNone(doc.name)

		# Clean up
		doc.delete()
