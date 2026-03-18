# -*- coding: utf-8 -*-

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountAutoPartialReconcileWizard(models.TransientModel):
    _name = 'account.auto.partial.reconcile.wizard'
    _description = 'Assistant de rapprochement partiel'
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        readonly=True,
    )
    source_line_ids = fields.Many2many(
        comodel_name='account.move.line',
        string='Pieces comptables source',
        readonly=True,
    )
    available_payment_line_ids = fields.Many2many(
        comodel_name='account.move.line',
        compute='_compute_available_payment_line_ids',
        string='Pieces de paiement disponibles',
    )
    payment_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Piece de paiement',
        required=True,
        domain="[('id', 'in', available_payment_line_ids)]",
    )
    available_counterpart_line_ids = fields.Many2many(
        comodel_name='account.move.line',
        compute='_compute_available_counterpart_line_ids',
        string='Pieces de contrepartie disponibles',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        related='payment_line_id.partner_id',
        readonly=True,
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        related='payment_line_id.account_id',
        readonly=True,
    )
    payment_residual = fields.Monetary(
        string='Residuel du paiement',
        currency_field='company_currency_id',
        compute='_compute_amounts',
    )
    allocation_line_ids = fields.One2many(
        comodel_name='account.auto.partial.reconcile.wizard.line',
        inverse_name='wizard_id',
        string='Lignes d allocation',
    )
    total_allocated_amount = fields.Monetary(
        string='Total alloue',
        currency_field='company_currency_id',
        compute='_compute_amounts',
    )
    remaining_amount = fields.Monetary(
        string='Montant restant',
        currency_field='company_currency_id',
        compute='_compute_amounts',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        domain = self.env.context.get('domain')
        if not domain:
            return res

        source_lines = self.env['account.move.line'].search(domain).filtered(self._is_reconcilable_line)
        if source_lines:
            res['source_line_ids'] = [Command.set(source_lines.ids)]
            if len(source_lines) == 1:
                res['payment_line_id'] = source_lines.id
        return res

    @api.depends('payment_line_id', 'allocation_line_ids.amount')
    def _compute_amounts(self):
        for wizard in self:
            wizard.payment_residual = abs(wizard.payment_line_id.amount_residual) if wizard.payment_line_id else 0.0
            wizard.total_allocated_amount = sum(wizard.allocation_line_ids.mapped('amount'))
            wizard.remaining_amount = wizard.payment_residual - wizard.total_allocated_amount

    @api.depends('source_line_ids', 'company_id')
    def _compute_available_payment_line_ids(self):
        aml_model = self.env['account.move.line']
        for wizard in self:
            if wizard.source_line_ids:
                wizard.available_payment_line_ids = wizard.source_line_ids.filtered(wizard._is_reconcilable_line)
                continue

            wizard.available_payment_line_ids = aml_model.search([
                ('company_id', '=', wizard.company_id.id),
                ('parent_state', '=', 'posted'),
                ('display_type', 'not in', ('line_section', 'line_subsection', 'line_note')),
                ('reconciled', '=', False),
                ('account_id.reconcile', '=', True),
                ('amount_residual', '!=', 0.0),
            ])

    @api.depends('payment_line_id', 'source_line_ids')
    def _compute_available_counterpart_line_ids(self):
        aml_model = self.env['account.move.line']
        for wizard in self:
            if not wizard.payment_line_id:
                wizard.available_counterpart_line_ids = aml_model
                continue

            domain = wizard._get_counterpart_domain(wizard.payment_line_id)
            if wizard.source_line_ids:
                domain.append(('id', 'in', wizard.source_line_ids.ids))
            wizard.available_counterpart_line_ids = aml_model.search(domain, order='date, id')

    @api.onchange('payment_line_id')
    def _onchange_payment_line_id(self):
        self.allocation_line_ids = [Command.clear()]

    def _is_reconcilable_line(self, line):
        return (
            line.parent_state == 'posted'
            and not line.reconciled
            and line.display_type not in ('line_section', 'line_subsection', 'line_note')
            and line.account_id.reconcile
            and not line.company_currency_id.is_zero(line.amount_residual)
        )

    def _get_counterpart_domain(self, payment_line):
        sign_operator = '<' if payment_line.balance > 0 else '>'
        domain = [
            ('company_id', '=', payment_line.company_id.id),
            ('parent_state', '=', 'posted'),
            ('display_type', 'not in', ('line_section', 'line_subsection', 'line_note')),
            ('reconciled', '=', False),
            ('account_id', '=', payment_line.account_id.id),
            ('id', '!=', payment_line.id),
            ('balance', sign_operator, 0.0),
            ('amount_residual', '!=', 0.0),
        ]
        if payment_line.partner_id:
            domain.append(('partner_id', '=', payment_line.partner_id.id))
        return domain

    def _compute_currency_amount_for_line(self, line, amount_company):
        line_currency = line.currency_id or line.company_currency_id
        if line_currency == line.company_currency_id:
            return amount_company

        residual_company = abs(line.amount_residual)
        residual_currency = abs(line.amount_residual_currency)
        if line.company_currency_id.is_zero(residual_company):
            return 0.0

        return line_currency.round(amount_company * residual_currency / residual_company)

    def _create_one_partial(self, payment_line, counterpart_line, amount_company):
        lines = payment_line + counterpart_line
        lines._check_amls_exigibility_for_reconciliation()

        debit_line = payment_line if payment_line.balance > 0 else counterpart_line
        credit_line = counterpart_line if payment_line.balance > 0 else payment_line

        debit_amount_currency = self._compute_currency_amount_for_line(debit_line, amount_company)
        credit_amount_currency = self._compute_currency_amount_for_line(credit_line, amount_company)
        aml_model = self.env['account.move.line']
        partial_model = self.env['account.partial.reconcile']

        if hasattr(aml_model, '_prepare_reconciliation_single_partial'):
            result = aml_model._prepare_reconciliation_single_partial(
                {
                    'aml': debit_line,
                    'amount_residual': amount_company,
                    'amount_residual_currency': debit_amount_currency,
                },
                {
                    'aml': credit_line,
                    'amount_residual': -amount_company,
                    'amount_residual_currency': -credit_amount_currency,
                },
            )
            partial_vals = result.get('partial_values')
            if not partial_vals:
                raise UserError(_('A partial reconciliation could not be generated for this selection.'))
            partials = partial_model.create([partial_vals])
            exchange_values = result.get('exchange_values')
            if exchange_values:
                if hasattr(aml_model, '_create_exchange_difference_moves'):
                    exchange_moves = aml_model._create_exchange_difference_moves([exchange_values])
                    partials.exchange_move_id = exchange_moves[:1].id
                elif hasattr(aml_model, '_create_exchange_difference_move'):
                    partials.exchange_move_id = aml_model._create_exchange_difference_move(exchange_values)
        elif hasattr(aml_model, '_prepare_reconciliation_partials'):
            partials_vals_list, exchange_data = aml_model._prepare_reconciliation_partials([
                {
                    'aml': debit_line,
                    'amount_residual': amount_company,
                    'amount_residual_currency': debit_amount_currency,
                },
                {
                    'aml': credit_line,
                    'amount_residual': -amount_company,
                    'amount_residual_currency': -credit_amount_currency,
                },
            ])
            if not partials_vals_list:
                raise UserError(_('A partial reconciliation could not be generated for this selection.'))
            partials = partial_model.create(partials_vals_list)
            if hasattr(aml_model, '_create_exchange_difference_move'):
                for index, exchange_values in exchange_data.items():
                    partials[index].exchange_move_id = aml_model._create_exchange_difference_move(exchange_values)
        else:
            partials = partial_model.create([{
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
                'amount': amount_company,
                'debit_amount_currency': debit_amount_currency,
                'credit_amount_currency': credit_amount_currency,
            }])

        if (
            payment_line.account_id.company_id.tax_exigibility
            and payment_line.account_id.account_type in ('asset_receivable', 'liability_payable')
            and not self._context.get('no_cash_basis')
        ):
            partials._create_tax_cash_basis_moves()

        return payment_line + counterpart_line

    def _create_full_reconcile_for_completed_groups(self, touched_lines):
        all_amls = touched_lines._all_reconciled_lines()
        if not all_amls:
            return

        mapping = all_amls._reconciled_by_number()
        done_matching_numbers = set()
        for aml in all_amls:
            if not aml.matching_number or aml.matching_number in done_matching_numbers:
                continue

            grouped_amls = aml._filter_reconciled_by_number(mapping)
            done_matching_numbers.add(aml.matching_number)
            if not grouped_amls or not all(grouped_amls.mapped('reconciled')) or grouped_amls.full_reconcile_id:
                continue

            involved_partials = grouped_amls.matched_debit_ids + grouped_amls.matched_credit_ids
            self.env['account.full.reconcile'].create({
                'exchange_move_id': involved_partials.filtered('exchange_move_id')[:1].exchange_move_id.id,
                'partial_reconcile_ids': [Command.link(partial.id) for partial in involved_partials],
                'reconciled_line_ids': [Command.link(rec_aml.id) for rec_aml in grouped_amls],
            })

    def action_partial_reconcile(self):
        self.ensure_one()

        if not self.payment_line_id:
            raise UserError(_('Please select a payment line first.'))

        allocation_lines = self.allocation_line_ids.filtered(
            lambda line: line.counterpart_line_id and line.amount > 0
        )
        if not allocation_lines:
            raise ValidationError(_('Add at least one allocation line with a positive amount.'))

        payment_line = self.payment_line_id._origin
        total_to_allocate = sum(allocation_lines.mapped('amount'))
        payment_open_amount = abs(payment_line.amount_residual)
        if self.company_currency_id.compare_amounts(total_to_allocate, payment_open_amount) > 0:
            raise ValidationError(
                _('The allocated amount %(allocated)s exceeds the payment residual %(residual)s.',
                  allocated=total_to_allocate, residual=payment_open_amount)
            )

        touched_lines = payment_line
        for allocation in allocation_lines:
            counterpart_line = allocation.counterpart_line_id._origin
            if payment_line.company_id != counterpart_line.company_id:
                raise ValidationError(_('All allocated lines must belong to the same company as the payment line.'))
            if payment_line.account_id != counterpart_line.account_id:
                raise ValidationError(_('All allocated lines must use the same account as the payment line.'))
            if payment_line.balance * counterpart_line.balance >= 0:
                raise ValidationError(
                    _('The journal item %(line)s must have the opposite sign of the payment line.',
                      line=counterpart_line.display_name)
                )

            current_payment_residual = abs(payment_line.amount_residual)
            current_counterpart_residual = abs(counterpart_line.amount_residual)
            max_current_amount = min(current_payment_residual, current_counterpart_residual)
            if self.company_currency_id.compare_amounts(allocation.amount, max_current_amount) > 0:
                raise ValidationError(
                    _('The allocated amount %(amount)s exceeds the currently reconcilable amount %(max)s for line %(line)s.',
                      amount=allocation.amount, max=max_current_amount, line=counterpart_line.display_name)
                )

            touched_lines |= self._create_one_partial(
                payment_line=payment_line,
                counterpart_line=counterpart_line,
                amount_company=self.company_currency_id.round(allocation.amount),
            )

        self._create_full_reconcile_for_completed_groups(touched_lines)
        involved_amls = touched_lines._all_reconciled_lines()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items to Reconcile'),
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', involved_amls.ids)],
            'context': {
                'search_default_group_by_account': True,
                'search_default_group_by_partner': True,
            },
        }


class AccountAutoPartialReconcileWizardLine(models.TransientModel):
    _name = 'account.auto.partial.reconcile.wizard.line'
    _description = 'Ligne d assistant de rapprochement partiel'
    _sql_constraints = [
        (
            'wizard_line_unique_counterpart',
            'unique(wizard_id, counterpart_line_id)',
            'Each journal item can only be allocated once.',
        ),
    ]

    wizard_id = fields.Many2one(
        comodel_name='account.auto.partial.reconcile.wizard',
        required=True,
        ondelete='cascade',
    )
    counterpart_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Piece comptable',
        required=True,
    )
    amount = fields.Monetary(
        string='Montant',
        currency_field='company_currency_id',
        required=True,
    )
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='wizard_id.company_currency_id',
        readonly=True,
    )
    max_amount = fields.Monetary(
        string='Montant ouvert',
        currency_field='company_currency_id',
        compute='_compute_max_amount',
    )

    @api.depends('counterpart_line_id')
    def _compute_max_amount(self):
        for line in self:
            line.max_amount = abs(line.counterpart_line_id.amount_residual) if line.counterpart_line_id else 0.0

    @api.onchange('counterpart_line_id')
    def _onchange_counterpart_line_id(self):
        if self.counterpart_line_id:
            self.amount = abs(self.counterpart_line_id.amount_residual)

    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount <= 0:
                raise ValidationError(_('The allocated amount must be strictly positive.'))
            if line.company_currency_id.compare_amounts(line.amount, line.max_amount) > 0:
                raise ValidationError(
                    _('The allocated amount %(amount)s cannot exceed the open amount %(max)s.',
                      amount=line.amount, max=line.max_amount)
                )

    @api.constrains('counterpart_line_id', 'wizard_id')
    def _check_unique_counterpart(self):
        for line in self:
            if not line.counterpart_line_id or not line.wizard_id:
                continue
            duplicates = line.wizard_id.allocation_line_ids.filtered(
                lambda current: current.id != line.id and current.counterpart_line_id == line.counterpart_line_id
            )
            if duplicates:
                raise ValidationError(_('Each journal item can only be allocated once.'))
