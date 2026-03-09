Goal
This wizard replaces standard auto-reconcile with a manual allocation workflow:

pick one payment journal item,
add multiple target journal items (invoices/entries),
enter amount per target,
reconcile those amounts, leaving any remainder open.
File: account_auto_partial_reconcile_wizard.py

1) Main wizard model
AccountAutoPartialReconcileWizard is a TransientModel (temporary records used in popups).

Key fields:

company_id, company_currency_id: company context + currency.
source_line_ids: lines passed from current list/domain (when launched from Reconcile list).
available_payment_line_ids: computed candidates for payment line selection.
payment_line_id: the line you want to allocate from (your payment/open credit/debit).
available_counterpart_line_ids: computed candidates to allocate to.
partner_id, account_id: shown from selected payment line.
allocation_line_ids: the one2many rows where you choose item + amount.
payment_residual: open residual of payment line.
total_allocated_amount: sum of entered allocation amounts.
remaining_amount: payment_residual - total_allocated_amount.
2) Default loading
default_get:

reads context domain (self.env.context.get('domain')),
loads matching journal items into source_line_ids,
if only 1 line is found, auto-sets payment_line_id.
So popup can start prefilled depending on where you open it.

3) Amount computation
_compute_amounts:

updates payment_residual,
sums allocation amounts,
computes remaining balance live in the popup.
4) Candidate payment lines
_compute_available_payment_line_ids:

if source_line_ids exists, limits to those.
otherwise searches all open reconcilable posted lines in company.
5) Candidate counterpart lines
_compute_available_counterpart_line_ids:

needs payment_line_id.
uses _get_counterpart_domain(payment_line):
same company,
posted, unreconciled,
same account,
opposite sign (balance < 0 or > 0 depending on payment line),
optionally same partner.
if source_line_ids exists, intersects with them.
6) Payment change behavior
_onchange_payment_line_id:

clears existing allocation rows when payment line changes.
7) Reconciliation helpers
_compute_currency_amount_for_line:

converts company amount into line currency proportionally using current residuals.
needed for proper multi-currency partial reconcile values.
_create_one_partial(payment_line, counterpart_line, amount_company):

validates line exigibility,
determines debit/credit side,
prepares partial reconcile values via Odoo core _prepare_reconciliation_partials,
creates account.partial.reconcile,
creates exchange difference move if needed,
creates cash-basis moves if applicable.
_create_full_reconcile_for_completed_groups:

after partials, checks matched groups (matching_number),
if a group is now fully settled and not yet full-reconciled, creates account.full.reconcile.
8) Main button action
action_partial_reconcile (called by Reconcile button):

ensures payment line exists.
ensures allocation rows exist with positive amounts.
checks total allocation does not exceed payment residual.
loops each allocation row:
validates same company/account and opposite sign,
validates amount <= current possible amount,
performs one partial reconcile.
then tries to finalize full reconciles where possible.
returns action opening related journal items.
9) Allocation line model
AccountAutoPartialReconcileWizardLine:

each row = one counterpart + one amount.
fields:
wizard_id: parent wizard.
counterpart_line_id: selected target journal item.
amount: amount for that item.
max_amount: current open residual of target.
_sql_constraints: same counterpart cannot be added twice in same wizard.
_onchange_counterpart_line_id: prefill amount with full open residual.
_check_amount: amount must be > 0 and <= open amount.
How to use in UI

Open Accounting -> Actions -> Reconcile.
Click Auto-reconcile (your module redirects to this popup).
Select Payment Journal Item.
In Allocation Lines, add rows:
choose Journal Item,
enter Amount.
Click Reconcile.
Remaining payment stays open for later reconciliation.