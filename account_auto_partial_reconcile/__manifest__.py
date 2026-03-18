# -*- coding: utf-8 -*-
{
    'name': 'Rapprochement Partiel Automatique',
    'version': '19.0.1.0.0',
    'summary': 'Etend le rapprochement auto avec allocation manuelle des montants',
    'category': 'Accounting',
    'author': 'Imad chaikhi',
    'license': 'LGPL-3',
    'depends': ['account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_auto_reconcile_wizard_inherit_views.xml',
        'wizard/account_auto_partial_reconcile_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
