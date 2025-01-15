# -*- coding: utf-8 -*-
{
    'name': "Web Branch Extension",

    'summary': """Web Branch Extension""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Eha Clinics Ltd",
    'website': "http://www.eha.ng",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Web',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'eha_multi_branch'],

    # always loaded
    'data': [
        'views/assets.xml',
        'data/ir_config_parameter_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}