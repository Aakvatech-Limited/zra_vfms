# Copyright (c) 2026, Aakvatech Limited and contributors
# For license information, please see license.txt

import frappe
import requests


def get_zra_setting(company):
    """Get ZRA Setting for a company.

    Args:
        company: Company name.

    Returns:
        ZRA Setting document or None if no setting exists.
    """
    setting_name = frappe.db.get_value("ZRA Setting", {"company": company})
    if not setting_name:
        return None
    return frappe.get_cached_doc("ZRA Setting", setting_name)


def get_credential(setting, tax_type):
    """Get enabled credential for a specific tax type.

    Args:
        setting: ZRA Setting document.
        tax_type: "VAT", "Seaport", or "Stamp Duty".

    Returns:
        ZRA Credential child row or None.
    """
    for row in setting.credentials:
        if row.tax_type == tax_type and row.enabled:
            return row
    return None


def get_endpoint_by_name(setting, endpoint_name):
    """Get endpoint details by name.

    Args:
        setting: ZRA Setting document.
        endpoint_name: Endpoint name (e.g., "Normal Sales", "B2B Sales").

    Returns:
        Tuple of (full_url, request_type) or (None, None).
    """
    for row in setting.endpoints:
        if row.endpoint_name == endpoint_name:
            url = setting.base_url.rstrip("/") + row.endpoint_path
            return url, row.request_type
    return None, None


def send_request(setting, endpoint_name, payload, tax_type="VAT"):
    """Send a request to the VFMS API.

    Handles authentication, HTTP errors, timeouts, and connection failures.

    Args:
        setting: ZRA Setting document.
        endpoint_name: Name of the endpoint (e.g., "Normal Sales").
        payload: Dict of the request body.
        tax_type: Tax type for credential lookup (default: "VAT").

    Returns:
        Dict with keys:
            - success (bool): Whether the API call succeeded.
            - response (dict or None): Parsed JSON response.
            - error (str or None): Error message on failure.
    """
    # Get credential
    credential = get_credential(setting, tax_type)
    if not credential:
        return {
            "success": False,
            "response": None,
            "error": (
                f"No enabled credential found for tax type '{tax_type}' "
                f"in ZRA Setting for company '{setting.company}'"
            ),
        }

    # Get endpoint
    url, request_type = get_endpoint_by_name(setting, endpoint_name)
    if not url:
        return {
            "success": False,
            "response": None,
            "error": (
                f"Endpoint '{endpoint_name}' not found in ZRA Setting " f"for company '{setting.company}'"
            ),
        }

    # Get decrypted token
    token_id = credential.get_password("token_id")

    # Build headers per VFMS API Guide v1.5 (Section 1.4)
    headers = {
        "Content-Type": "application/json",
        "vfms-request-type": request_type,
        "vfms-intergration-id": credential.integration_id,
        "vfms-token-id": token_id,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )
        response_data = response.json()

        # VFMS API returns HTTP 200 for both success and error.
        # Some endpoints (e.g., getNonTaxItems) return a JSON array
        # directly — a list response on HTTP 200 is always success.
        if response.status_code == 200:
            if isinstance(response_data, list):
                return {
                    "success": True,
                    "response": response_data,
                    "error": None,
                }

            error_msg = (
                response_data.get("error")
                or response_data.get("message")
                or response_data.get("statusMessage")
            )
            if not error_msg:
                return {
                    "success": True,
                    "response": response_data,
                    "error": None,
                }

            return {
                "success": False,
                "response": response_data,
                "error": error_msg,
            }
        else:
            error_msg = f"HTTP {response.status_code}"
            if isinstance(response_data, dict):
                error_msg = (
                    response_data.get("error")
                    or response_data.get("message")
                    or response_data.get("statusMessage")
                    or error_msg
                )

            return {
                "success": False,
                "response": response_data,
                "error": error_msg,
            }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "response": None,
            "error": f"Request to {url} timed out after 30 seconds",
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "response": None,
            "error": f"Failed to connect to VFMS server at {url}",
        }
    except ValueError:
        return {
            "success": False,
            "response": None,
            "error": f"Invalid JSON response from {url}",
        }
    except Exception as e:
        return {
            "success": False,
            "response": None,
            "error": str(e),
        }
