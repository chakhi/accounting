# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountAutoReconcileWizard(models.TransientModel):
    _inherit = 'account.auto.reconcile.wizard'

    use_partial_reconcile = fields.Boolean(
        string='Rapprochement partiel',
        help='Si active, le bouton Lancer ouvre l assistant de rapprochement partiel avec allocation manuelle des montants.',
    )

    def auto_reconcile(self):
        self.ensure_one()
        if self.use_partial_reconcile:
            action = self.env['ir.actions.act_window']._for_xml_id(
                'account_auto_partial_reconcile.action_open_auto_partial_reconcile_wizard'
            )
            ctx = dict(self.env.context or {})
            ctx['domain'] = self._get_amls_domain()
            action['context'] = ctx
            return action
        return super().auto_reconcile()
