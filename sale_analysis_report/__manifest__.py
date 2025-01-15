# -*- coding: utf-8 -*-
{
    'name': "Sale Order Report Analysis",

    'summary': """
        Sales report based on department""",
    'version': '17.0',
    'description': """
        This module helps user to report Sales report based on department
    """,

    'author': "Maduka Sopulu.",

    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'AGPL-3',
    'depends': [
        'sale',
        'hr',
    ],

    'data': [
        # 'security/ir.model.access.csv',
        'views/sale.xml',
    ],
    'demo': [
    ],
}
