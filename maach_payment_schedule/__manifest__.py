# -*- coding: utf-8 -*-
{
    'name': "Maach Payment Schedule",

    'summary': """
        Maach Payment Schedule""",

    'description': """
        This module helps users schedule payment
    """,

    'author': "Maduka Sopulu.",

    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'AGPL-3',
    'depends': [
        'account',
        'company_memo',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/payment_schedule.xml',
        'views/memo_view.xml',
    ],
    'demo': [
        # 'demo/demo.xml',
    ],
}
