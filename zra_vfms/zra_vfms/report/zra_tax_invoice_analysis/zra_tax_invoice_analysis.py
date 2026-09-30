import frappe
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, today


def execute(filters=None):
    filters = frappe._dict(filters or {})
    from_datetime, to_datetime = get_date_range(filters)
    analysis_view = filters.get("analysis_view") or "Detail"

    rows = get_rows(filters, from_datetime, to_datetime)

    if analysis_view == "Detail":
        return get_detail_columns(), get_detail_data(rows)

    return get_summary_columns(), get_summary_data(rows, analysis_view)


def get_date_range(filters):
    time_span = filters.get("time_span") or "Today"
    selected_from_date = filters.get("from_date")
    selected_to_date = filters.get("to_date")

    current_date = today()
    from_date = current_date
    to_date = current_date

    if time_span == "Yesterday":
        from_date = add_days(current_date, -1)
        to_date = from_date

    elif time_span == "This Week":
        weekday_number = getdate(current_date).weekday()
        from_date = add_days(current_date, -weekday_number)
        to_date = add_days(from_date, 6)

    elif time_span == "Last Week":
        weekday_number = getdate(current_date).weekday()
        this_week_start = add_days(current_date, -weekday_number)
        from_date = add_days(this_week_start, -7)
        to_date = add_days(this_week_start, -1)

    elif time_span == "This Month":
        from_date = get_first_day(current_date)
        to_date = get_last_day(current_date)

    elif time_span == "Last Month":
        previous_month = add_months(current_date, -1)
        from_date = get_first_day(previous_month)
        to_date = get_last_day(previous_month)

    elif time_span == "This Year":
        year = getdate(current_date).year
        from_date = f"{year}-01-01"
        to_date = f"{year}-12-31"

    elif time_span == "Period":
        if not selected_from_date or not selected_to_date:
            frappe.throw("From Date and To Date are required when Time Span is Period.")

        if getdate(selected_from_date) > getdate(selected_to_date):
            frappe.throw("From Date cannot be after To Date.")

        from_date = selected_from_date
        to_date = selected_to_date

    # Use a half-open interval [from, next day) so receipts with fractional
    # seconds at the end of the selected date are not accidentally excluded.
    from_datetime = f"{from_date} 00:00:00"
    to_datetime = f"{add_days(to_date, 1)} 00:00:00"

    return from_datetime, to_datetime


def get_rows(filters, from_datetime, to_datetime):
    zra = frappe.qb.DocType("ZRA Tax Invoice")
    sales_invoice = frappe.qb.DocType("Sales Invoice")

    query = (
        frappe.qb.from_(zra)
        .left_join(sales_invoice)
        .on(sales_invoice.name == zra.sales_invoice)
        .select(
            zra.name,
            zra.sales_invoice,
            zra.company,
            zra.tax_type,
            zra.status,
            zra.receipt_number,
            zra.receipt_time,
            zra.znumber,
            zra.type,
            zra.urn,
            zra.response_number,
            zra.business_name,
            zra.receipt_amount,
            zra.tax_exclusive,
            zra.tax_amount,
            zra.is_cancellation,
            zra.is_correction,
            sales_invoice.customer,
            sales_invoice.currency,
            sales_invoice.grand_total,
        )
        .where(zra.receipt_time >= from_datetime)
        .where(zra.receipt_time < to_datetime)
    )

    if filters.get("company"):
        query = query.where(zra.company == filters.get("company"))

    if filters.get("customer"):
        query = query.where(sales_invoice.customer == filters.get("customer"))

    if filters.get("sales_invoice"):
        query = query.where(zra.sales_invoice == filters.get("sales_invoice"))

    if filters.get("tax_type"):
        query = query.where(zra.tax_type == filters.get("tax_type"))

    if filters.get("status"):
        query = query.where(zra.status == filters.get("status"))

    if filters.get("document_type"):
        query = query.where(zra.type == filters.get("document_type"))

    if filters.get("receipt_number"):
        query = query.where(
            zra.receipt_number.like("%" + filters.get("receipt_number") + "%")
        )

    if filters.get("znumber"):
        query = query.where(zra.znumber.like("%" + filters.get("znumber") + "%"))

    transaction_type = filters.get("transaction_type")

    if transaction_type == "Normal":
        query = query.where(zra.is_cancellation == 0)
        query = query.where(zra.is_correction == 0)

    elif transaction_type == "Cancellation":
        query = query.where(zra.is_cancellation == 1)

    elif transaction_type == "Correction":
        query = query.where(zra.is_correction == 1)

    return query.orderby(zra.receipt_time).run(as_dict=True)


def get_detail_columns():
    return [
        {"label": "Receipt Time", "fieldname": "receipt_time", "fieldtype": "Datetime", "width": 155},
        {"label": "ZRA Tax Invoice", "fieldname": "name", "fieldtype": "Link", "options": "ZRA Tax Invoice", "width": 140},
        {"label": "Sales Invoice", "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 170},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 170},
        {"label": "Tax Type", "fieldname": "tax_type", "fieldtype": "Data", "width": 90},
        {"label": "Type", "fieldname": "document_type", "fieldtype": "Data", "width": 70},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 90},
        {"label": "Transaction Type", "fieldname": "transaction_type", "fieldtype": "Data", "width": 115},
        {"label": "Receipt No.", "fieldname": "receipt_number", "fieldtype": "Data", "width": 130},
        {"label": "Z Number", "fieldname": "znumber", "fieldtype": "Data", "width": 120},
        {"label": "Business Name", "fieldname": "business_name", "fieldtype": "Data", "width": 170},
        {"label": "Receipt Amount", "fieldname": "receipt_amount", "fieldtype": "Currency", "options": "currency", "width": 130},
        {"label": "Tax Exclusive", "fieldname": "tax_exclusive", "fieldtype": "Currency", "options": "currency", "width": 130},
        {"label": "Tax Amount", "fieldname": "tax_amount", "fieldtype": "Currency", "options": "currency", "width": 120},
        {"label": "Effective Tax %", "fieldname": "effective_tax_rate", "fieldtype": "Percent", "width": 115},
        {"label": "ZRA Amount Variance", "fieldname": "amount_variance", "fieldtype": "Currency", "options": "currency", "width": 140},
        {"label": "SI Grand Total", "fieldname": "invoice_grand_total", "fieldtype": "Currency", "options": "currency", "width": 125},
        {"label": "Receipt vs SI", "fieldname": "invoice_variance", "fieldtype": "Currency", "options": "currency", "width": 125},
        {"label": "URN", "fieldname": "urn", "fieldtype": "Data", "width": 120},
        {"label": "Response Number", "fieldname": "response_number", "fieldtype": "Data", "width": 230},
        {"label": "Currency", "fieldname": "currency", "fieldtype": "Data", "width": 80},
    ]


def get_detail_data(rows):
    data = []

    for row in rows:
        receipt_amount = flt(row.receipt_amount)
        tax_exclusive = flt(row.tax_exclusive)
        tax_amount = flt(row.tax_amount)
        invoice_grand_total = flt(row.grand_total)

        effective_tax_rate = 0
        if tax_exclusive:
            effective_tax_rate = (tax_amount / tax_exclusive) * 100

        amount_variance = receipt_amount - (tax_exclusive + tax_amount)

        invoice_variance = 0
        if row.sales_invoice and row.grand_total is not None:
            invoice_variance = receipt_amount - invoice_grand_total

        transaction_type = "Normal"
        if row.is_cancellation:
            transaction_type = "Cancellation"
        elif row.is_correction:
            transaction_type = "Correction"

        data.append(
            {
                "name": row.name,
                "receipt_time": row.receipt_time,
                "sales_invoice": row.sales_invoice,
                "customer": row.customer,
                "company": row.company,
                "tax_type": row.tax_type,
                "document_type": row.type,
                "status": row.status,
                "transaction_type": transaction_type,
                "receipt_number": row.receipt_number,
                "znumber": row.znumber,
                "business_name": row.business_name,
                "receipt_amount": receipt_amount,
                "tax_exclusive": tax_exclusive,
                "tax_amount": tax_amount,
                "effective_tax_rate": effective_tax_rate,
                "amount_variance": amount_variance,
                "invoice_grand_total": invoice_grand_total,
                "invoice_variance": invoice_variance,
                "urn": row.urn,
                "response_number": row.response_number,
                "currency": row.currency,
            }
        )

    return data


def get_summary_columns():
    return [
        {"label": "Analysis", "fieldname": "analysis_key", "fieldtype": "Data", "width": 200},
        {"label": "Receipts", "fieldname": "receipt_count", "fieldtype": "Int", "width": 90},
        {"label": "Receipt Amount", "fieldname": "receipt_amount", "fieldtype": "Currency", "width": 140},
        {"label": "Tax Exclusive", "fieldname": "tax_exclusive", "fieldtype": "Currency", "width": 140},
        {"label": "Tax Amount", "fieldname": "tax_amount", "fieldtype": "Currency", "width": 130},
        {"label": "Effective Tax %", "fieldname": "effective_tax_rate", "fieldtype": "Percent", "width": 120},
        {"label": "Cancellations", "fieldname": "cancellations", "fieldtype": "Int", "width": 110},
        {"label": "Corrections", "fieldname": "corrections", "fieldtype": "Int", "width": 100},
        {"label": "Amount Variance", "fieldname": "amount_variance", "fieldtype": "Currency", "width": 135},
    ]


def get_summary_data(rows, analysis_view):
    summary_map = {}

    for row in rows:
        if analysis_view == "Daily Summary":
            analysis_key = str(row.receipt_time)[:10] if row.receipt_time else "Not Set"
        elif analysis_view == "Tax Type Summary":
            analysis_key = row.tax_type or "Not Set"
        elif analysis_view == "Status Summary":
            analysis_key = row.status or "Not Set"
        elif analysis_view == "Company Summary":
            analysis_key = row.company or "Not Set"
        elif analysis_view == "Document Type Summary":
            analysis_key = row.type or "Not Set"
        else:
            analysis_key = "All"

        summary = summary_map.setdefault(
            analysis_key,
            {
                "analysis_key": analysis_key,
                "receipt_count": 0,
                "receipt_amount": 0,
                "tax_exclusive": 0,
                "tax_amount": 0,
                "cancellations": 0,
                "corrections": 0,
                "amount_variance": 0,
            },
        )

        receipt_amount = flt(row.receipt_amount)
        tax_exclusive = flt(row.tax_exclusive)
        tax_amount = flt(row.tax_amount)

        summary["receipt_count"] += 1
        summary["receipt_amount"] += receipt_amount
        summary["tax_exclusive"] += tax_exclusive
        summary["tax_amount"] += tax_amount
        summary["amount_variance"] += receipt_amount - (tax_exclusive + tax_amount)

        if row.is_cancellation:
            summary["cancellations"] += 1

        if row.is_correction:
            summary["corrections"] += 1

    data = []

    for key in sorted(summary_map):
        summary = summary_map[key]
        effective_tax_rate = 0

        if summary["tax_exclusive"]:
            effective_tax_rate = (
                summary["tax_amount"] / summary["tax_exclusive"]
            ) * 100

        data.append(
            {
                **summary,
                "effective_tax_rate": effective_tax_rate,
            }
        )

    return data
