{
    'name': 'ERP Customization - EEDC',
    'version': '16.0.1',
    'author': "Maduka Sopulu",
    'category': 'ERP',
    'summary': 'ODOO Base Extension to customize base modules',
    'depends': ['base', 'hr', 'hr_pms', 'company_memo', 'stock_no_negative', 'purchase', 'hr_holidays'],
    'description': "ODOO Base Extension to customize base modules ",
    "data": [
        'security/ir.model.access.csv',
        'views/base_view.xml',
        'views/hr_employee_inherit.xml',
        'views/res_state_inherit_view.xml',
        'data/state_data.xml',
        'data/lga_data.xml',
        'views/hr_employee_transfer_view.xml',
        'views/hr_memo_view.xml',
        'views/res_users_view.xml'
        # 'security/security_view.xml',
        # 'data/eha_base_extension_data.xml',
        # 'data/email_template.xml',
        # 'wizard/oeh_reason_wizard.xml',
    ],
    # 'assets': {'web.assets_backend': [
    #     '/eha_website_sale/static/js/membership_subscription.js',
        
    # ]},
}
