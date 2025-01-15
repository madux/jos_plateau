# -*- coding: utf-8 -*-
{
    'name': "Multi Branch - OdooERP",

    'summary': """Multi Branch""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Maduka Sopulu",
    'website': "http://www.ng",

    # for the full list
    'category': 'Uncategorized',
    'version': '17.0',

    # any module necessary for this one to work correctly
    'depends': [
        'base', 
        'helpdesk', 
        'website_payment',
        'sale', 
        'product', 
        'stock', 
        'account',
        'analytic',
        'account_reports',
        'purchase',
        'sale_analysis_report',
        'account_batch_payment',
        # 'inventory_extension',
        'sale_stock', 
        # 'eha_product_restriction', 

    ],
    'license': 'LGPL-3',
    'data': [
        'branch/data/branch.xml',
        'branch/security/ir.model.access.csv',
        'account/security/security_view.xml',
        'branch/views/eha_branch_view.xml',
        'branch/views/base_view.xml',
        'stock/views/stock_view.xml',
        'stock/views/delivery_order_report.xml',
        # 'oehealth/security/ir.rule.xml',
        'purchase/views/purchase_view.xml',
        'sales/views/sale_view.xml',
        'sales/views/account_payment_views.xml',
        # 'auth/views/assets.xml',
        # 'auth/data/ir_config_parameter_data.xml',
        # 'account/views/search_template_view.xml',
        'account/views/account_view.xml',
        # 'account/data/data.xml',
        # 'account/data/account_financial_report_data.xml',
        # 'account/data/mail_template_data.xml',
        # 'account/views/search_template_view.xml',
        'helpdesk/security/helpdesk_security.xml',
        'helpdesk/views/helpdesk_view.xml',
        # 'covid_consumables/oeha_covid_consumables_views.xml',
        'pricelist/product_pricelist_views.xml',
        'account/security/ir_rule.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #     '/eha_multi_branch/static/src/js/account_reports.js',
    # ]},
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}