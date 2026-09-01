### ZRA VFMS

Zanzibar Revenue Authority (ZRA): Virtual Fiscal Management System (VFMS) integration.

This app sends Sales Invoices to ZRA as tax invoices, checks their status,
and keeps a log of every request and response. It works on Frappe/ERPNext
version 15 and version 16.

### User Manual

Follow these steps to start sending tax invoices to ZRA.

**1. Create a ZRA Setting for each company**

Go to **ZRA Setting** and create one record per company.

- `Company`: the company that sends tax invoices.
- `Sandbox`: turn this on to use the ZRA test server. Turn it off to use
  the live server. The app sets `Base URL` for you from this checkbox, so
  you do not enter it by hand.
- `ZRA Start Date`: the app does not send invoices dated before this date.
- `Auto Send Tax on Submit`: turn this on to send an invoice to ZRA when
  a user submits it. Leave it off to send invoices by hand.

**2. Add credentials**

In the same ZRA Setting record, add a row under `Credentials` for each
tax type you use.

- `Tax Type`: VAT, Seaport, or Stamp Duty.
- `Integration ID` and `Token ID`: ZRA gives you these for each tax type.
- `Enabled`: turn on the credentials you want the app to use.

**3. Check the endpoints (optional)**

The app fills the `Endpoints` table with the 10 default VFMS endpoints
when you create a new ZRA Setting. Most users do not need to change this
table. Edit or add a row only if ZRA changes an endpoint or gives you a
new one. Use the **Reset Endpoints to Defaults** button to restore the
original list.

**4. Set the customer ZRA Number (optional)**

This app relabels the Customer field "Tax ID" to **ZRA Number**. Fill in
a customer's ZRA Number when they have one. This is optional: VFMS also
accepts sales to pass-by customers with no ZRA Number, and the app sends
those as normal (walk-in) sales.

**5. Mark non-taxable items (optional)**

On an Item, use the **ZRA Non-Taxable** section to mark items that are
tax-exempt.

- `Is ZRA Non Taxable`: turn this on for the item.
- `ZRA Non Tax Item`: pick the matching non-tax item ZRA has registered.

The app fetches the list of non-tax items from ZRA once a week. To fetch
the list right away, open **ZRA Setting** and click **Actions** >
**Fetch Non-Tax Items**.

**6. Send invoices to ZRA**

- Automatic: turn on `Auto Send Tax on Submit` in ZRA Setting. The app
  sends every submitted Sales Invoice for that company right away.
- Manual: open a submitted Sales Invoice and click **Send Tax**.
- Retry: the app retries invoices that are still `Pending` every 15
  minutes.
- Non-taxable invoices: turn on `Is Non Taxable` on the Sales Invoice to
  skip sending it to ZRA.

Each Sales Invoice shows a `Tax Status`.

- `Not Sent`: the app has not sent the invoice yet.
- `Pending`: the app sent the invoice and waits for a response.
- `Success`: ZRA accepted the invoice. The app saves the receipt details.
- `Failed`: ZRA rejected the invoice. Check the error message on the
  related **ZRA Tax Invoice** record.

**7. Check invoice status**

Every attempt to send an invoice creates a **ZRA Tax Invoice** record.
Open it to see the status, receipt number, QR code URL, and error
message. The app also creates a **ZRA Einvoice Log** record for every
request, for full request and response tracing.

**8. Use tax relief**

Follow these steps when a customer has a ZRA tax relief number.

1. Enter the `Relief Number` on the Sales Invoice.
2. Click **Verify Relief Number**. On success, the invoice shows a green
   "Verified" mark.
3. Submit and send the invoice as usual.

### Installation

**Frappe Cloud**

1. Go to your bench in Frappe Cloud.
2. Add `zra_vfms` as an app from this repository.
3. Deploy the bench, then install the app on your site.

**Bench (self-hosted)**

Install the app with the [bench](https://github.com/frappe/bench) CLI.

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app zra_vfms
```

Run `bench migrate` after installation. This creates the extra fields and
labels the app needs on Sales Invoice, Item, and Customer.

### Contributing

This app uses `pre-commit` for code formatting and linting. [Install pre-commit](https://pre-commit.com/#installation) and enable it for this repository.

```bash
cd apps/zra_vfms
pre-commit install
```

Pre-commit uses the following tools to check and format your code.

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app uses GitHub Actions for CI. The following workflows apply.

- CI: installs this app and runs unit tests on every push to the `develop` branch.
- Linters: runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

gpl-3.0
