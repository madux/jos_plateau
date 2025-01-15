from odoo import fields, models ,api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta as rd

_logger = logging.getLogger(__name__)

class ngAccountBudget(models.Model):
    _name = "ng.account.budget"
    _rec_name = "general_journal_id"
    _description = "To hold the budget of accounts and journal"
    
    is_migrated = fields.Boolean(string="Is migrated")
    general_journal_id = fields.Many2one('account.journal', string='Journal')
    general_account_id = fields.Many2one('account.account', string='Account')
    budget_id = fields.Many2one('account.budget.post', string='Budget')
    budget_amount = fields.Float(string="Budget Amount")
    budget_used_amount = fields.Float(string="Utilized Amount")
    budget_variance = fields.Float(string="Budget Variance", compute="compute_variance")
    active = fields.Boolean(string="Active", default=True)
    date_from = fields.Date(string="Date from")
    date_to = fields.Date(string="Date To")
    paid_date = fields.Date(string="Paid Date")
    branch_id = fields.Many2one('multi.branch', string='MDA Sector',required=False)
    move_id = fields.Many2one('account.move', string='Move')

    @api.depends('budget_amount', 'budget_used_amount')
    def compute_variance(self):
        for rec in self:
            if rec.budget_amount and rec.budget_used_amount:
                rec.budget_variance = rec.budget_amount - rec.budget_used_amount
            else:
                rec.budget_variance = False

