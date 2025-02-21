from odoo import fields, models ,api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta as rd

class AccountEconomic(models.Model):
    _name = "account.economic"
    
    name = fields.Char(string="Economic")
    code = fields.Char(string="Economic Code")
    account_id = fields.Many2one('account.account', string='Account')
    ng_budget_line_ids = fields.One2many(
        'ng.account.budget.line', 
        'economic_id',
        string='Budget lines',
        )
    branch_ids = fields.Many2many(
        'multi.branch', 
        string='MDA')
    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Other Recurrent"),
            ("asset_current", "Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Liability"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "REVENUE"),
            ("income_other", "Other Income"),
            ("expense", "Expenditure"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string='Economic Type',
        tracking=True,
        required=False,
        store=True,
        compute="compute_account_id"
    )
    
    @api.depends("account_id")
    def compute_account_id(self):
        for rec in self:
            if rec.account_id:
                rec.account_type = rec.account_id.account_type
                
    @api.model_create_multi
    def create(self, vals_list):
        economic = self.browse()
        for vals in vals_list:
            code = vals.get('code', '')
            name = vals.get('name', '')
            economic = self.env['account.economic'].sudo().search([('name', '=', name), ('code', '=', code)], limit=1)
            structure_type = 'income' if code.startswith('12') else 'expense' if code.startswith('22') or  code.startswith('21') else 'asset_current' \
                    if code.startswith('31') else 'liability_current' if code.startswith('41') else 'asset_cash'
            vals['account_type'] = structure_type
            if not economic:
                economic = super(AccountEconomic, self).create(vals)
            else:
                economic.write({
                                'code': code
                                })
        return economic
    