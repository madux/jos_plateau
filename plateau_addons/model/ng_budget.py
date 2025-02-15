from odoo import fields, models ,api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta as rd

_logger = logging.getLogger(__name__)

class NgAccountMove(models.Model):
    _inherit = "account.move"
    _description = "To hold the budget allocation lines"
     
    budget_allocation_date = fields.Datetime(string="Allocation Date")
    ng_budget_id = fields.Many2one('ng.account.budget', string='Budget Head',required=False)
    

class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    ng_budget_id = fields.Many2one('ng.account.budget', string='Budget Head',required=False)
    
    
class NgAccountBudgetLine(models.Model):
    _name = "ng.account.budget.line"
    _description = "To hold the budget allocation lines"
     
    approved_date = fields.Datetime(string="Approved Date")
    budget_allocation_date = fields.Datetime(string="Allocation Date")
    ng_budget_id = fields.Many2one('ng.account.budget', string='Budget Head')
    approver_id = fields.Many2one('res.users', string='Approved By')
    reviewer_id = fields.Many2one('res.users', string='Reviewed By')
    allocated_amount = fields.Float(string='Allocated Amount')
    
    
class ngAccountBudget(models.Model):
    _name = "ng.account.budget"
    _rec_name = "name"
    _description = "To hold the budget of accounts and journal"
    
    is_migrated = fields.Boolean(string="Is migrated")
    name = fields.Char(string="Name", store=True, readonly="0")
    code = fields.Char(string="Code", store=True, readonly="0")
    general_journal_id = fields.Many2one('account.journal', string='Journal')
    general_account_id = fields.Many2one('account.account', string='Account')
    budget_id = fields.Many2one('account.budget.post', string='Budget')
    budget_amount = fields.Float(string="Budget Amount",
                                 compute="compute_budget_amount", 
                                 store=True)
    budget_used_amount = fields.Float(string="Utilized Amount")
    budget_variance = fields.Float(string="Budget Variance", compute="compute_variance", store=True)
    active = fields.Boolean(string="Active", default=1)
    date_from = fields.Date(string="Date from")
    date_to = fields.Date(string="Date To")
    paid_date = fields.Date(string="Paid Date")
    branch_id = fields.Many2one('multi.branch', string='MDA Sector',required=False)
    move_id = fields.Many2one('account.move', string='Move') 
    budget_allocation_line = fields.One2many(
        'account.move', 
        'ng_budget_id',
        string='Budget Move line') 
    ng_account_budget_line = fields.One2many(
        'ng.account.budget.line', 
        'ng_budget_id',
        string='Budget Allocation line') 

    @api.depends('budget_amount', 'budget_used_amount')
    def compute_variance(self):
        for rec in self:
            if rec.budget_amount or rec.budget_used_amount:
                rec.budget_variance = rec.budget_amount - rec.budget_used_amount
            else:
                rec.budget_variance = 0
    
    @api.depends('budget_allocation_line.amount_total')
    def compute_budget_amount(self):
        rec= self
        if rec.budget_allocation_line:
            amount_total = sum([r.amount_total for r in rec.budget_allocation_line if r.state in ['posted']])
            rec.budget_amount = amount_total
        else:
            rec.budget_amount = 0

    @api.model
    def create(self, vals):
        result = super(ngAccountBudget, self).create(vals)
        name = vals.get('name', '-') or vals['name']
        res = f"{self.name} - ({self.general_journal_id.name} {self.general_account_id.name})"
        # raise ValidationError(res)
        
        self.update({'name': res})
        return result