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
    _rec_name = "account_id"
    _description = "To hold the budget allocation lines"
    
    '''Go through the overview budget 
    If branch does not have xmlid,
    Find the branch that has same name and xmlid
    if budget head not linked, find budget head where budget type is equal to budget type and Branch equal to the current created branch,
    Append budget head to the record, append branch and on the branch to the budget head
    then delete the created branch .'''
    
    def update_budget_overview(self):
        all_budget_line_ids = self.env['ng.account.budget.line'].search([])[4000:4500]
        ir_model_data = self.env['ir.model.data'].sudo()
        branch_obj = self.env['multi.branch'].sudo()
        budget_obj = self.env['ng.account.budget'].sudo()
        branches_to_delete = []
        for ln in all_budget_line_ids:
            _logger.info(f"THIS IS BUDGET LINE {ln.id}")
            branch = None
            branch_xmlid = ir_model_data.search([
                ('model', '=', 'multi.branch'),  # Replace with the model name
                ('res_id', '=', ln.branch_id.id)  # Replace with the record ID you want to check
            ])
            if branch_xmlid:
                branch = ln.branch_id.id
            else:
                branches_to_delete.append(ln.branch_id.id)
                
                branches = branch_obj.search([
                ('name', 'ilike', ln.branch_id.name) 
                ])
                for br in branches:
                    brn = ir_model_data.search([
                        ('model', '=', 'multi.branch'), 
                        ('res_id', '=', br.id) 
                    ])
                    if brn:
                        for jrl in self.env['account.journal'].search([('branch_id.name', '=', br.name)]):
                            jrl.branch_id = br.id
                        branch = br.id
                        break
                    else:
                        ln.branch_id.active = False
            if not ln.ng_budget_id:
                budget = budget_obj.search([
                ('budget_type', '=', ln.budget_type),
                '|', ('branch_id.name', '=', ln.branch_id.name),
                ('branch_id', '=', ln.branch_id.id) 
                ])
                if budget:
                    for bb in budget:
                        bb.branch_id = branch 
                    ln.ng_budget_id = budget[0].id
            else:
                ln.ng_budget_id.branch_id = branch
            ln.branch_id = branch     
        for brd in branches_to_delete:
            branch_obj.browse([brd]).unlink()
                
     
    approved_date = fields.Datetime(string="Approved Date")
    budget_allocation_date = fields.Datetime(string="Allocation Date", default=fields.Date.today())
    ng_budget_id = fields.Many2one('ng.account.budget', string='Budget Head')
    approver_id = fields.Many2one('res.users', string='Approved By')
    branch_id = fields.Many2one('multi.branch', string='MDA')
    branch_segment_id = fields.Many2one(
        'account.public.segment', 
        string='Account Segment',
    )
    reviewer_id = fields.Many2one('res.users', string='Reviewed By')
    active = fields.Boolean(string='Active', default=True)
    account_id = fields.Many2one('account.account', string='Account')
    economic_id = fields.Many2one('account.economic', string='Economic')
    # account_type = fields.Char(
    #     string='Account Overview',
    #     compute="compute_account_id"
    #     # related="account_id.account_type"
    # )
    
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
        string='Account Overview',
        tracking=True,
        required=False,
        store=True,
        compute="compute_account_id"
    )
    budget_type = fields.Selection(
        [
        ("Revenue", "Revenue"), 
        ("Personnel", "Personnel"), 
        ("Overhead", "Overhead"), 
        ("Expenditure", "Expenditure"), 
        ("Capital", "Capital"),
        ("Other", "Others"),
        ], string="Budget Type", 
    )
    code = fields.Char(string="Fund Code", store=True, readonly="0")
    allocated_amount = fields.Float(string='Allocated Amount')
    utilized_amount = fields.Float(string='Utilized Amount')
    added_budget_amount = fields.Float(string='Added budget Amount')
    reduced_budget_amount = fields.Float(string='Reduced budget Amount')
    budget_balance = fields.Float(string='Balance Amount', compute="compute_variance")
    fiscal_year = fields.Char(
        string='Fiscal Year', 
        compute="compute_fiscal_year"
        )
    revise_previous_budget = fields.Float(string="Revise Bugdet (Previous Year)",
                                 store=True)
    previous_budget_amount = fields.Float(string="Previous Year Bugdet",
                                 store=True)
    previous_budget_performance = fields.Float(string="PY performance",
                                 store=True)
    budget_adjustment = fields.Float(string="Bugdet Adjustment",
                                 store=True)
    
    @api.depends("budget_allocation_date")
    def compute_fiscal_year(self):
        for rec in self:
            if rec.budget_allocation_date:
                rec.fiscal_year = rec.budget_allocation_date.year
            else:
                rec.fiscal_year = fields.Date.today().year
                
    @api.depends("account_id")
    def compute_account_id(self):
        for rec in self:
            if rec.account_id:
                rec.account_type = rec.account_id.account_type
    
    @api.depends('allocated_amount', 'utilized_amount')
    def compute_variance(self):
        for rec in self:
            if rec.allocated_amount or rec.utilized_amount:
                rec.budget_balance = rec.allocated_amount - rec.utilized_amount
            else:
                rec.budget_balance = 0
    
    
class ngAccountBudget(models.Model):
    _name = "ng.account.budget"
    _rec_name = "name"
    _description = "To hold the budget of accounts and journal"
    
    budget_type = fields.Selection(
        [
        ("Revenue", "Revenue"), 
        ("Personnel", "Personnel"),
        ("Overhead", "Overhead"), 
        ("Expenditure", "Expenditure"), 
        ("Capital", "Capital"),
        ("Other", "Others"),
        ], string="Budget Type", 
    )
    is_migrated = fields.Boolean(string="Is migrated")
    name = fields.Char(string="Name", store=True, readonly="0")
    code = fields.Char(string="Fund Code", store=True, readonly="0")
    general_journal_id = fields.Many2one('account.journal', string='Journal')
    general_account_id = fields.Many2one('account.account', string='Account')
    budget_id = fields.Many2one('account.budget.post', string='Budget')
    budget_amount = fields.Float(string="Budget Amount",
                                 compute="compute_budget_amount", 
                                 store=True)
    previous_budget_amount = fields.Float(string="Previous Year Bugdet",
                                 compute="compute_budget_amount", 
                                 store=True)
    previous_budget_performance = fields.Float(string="Previous Year Bugdet performance",
                                 store=True)
    revise_previous_budget = fields.Float(string="Revise Bugdet (Previous Year)",
                                        #   compute="compute_budget_line",
                                 store=True)
    budget_adjustment = fields.Float(string="Current Bugdet Adjustment",
                                    #  compute="compute_budget_line",
                                 store=True)
    fiscal_year = fields.Char(
        string='Fiscal Year', 
        compute="compute_fiscal_year"
        )
    
    
    @api.depends("create_date", "paid_date")
    def compute_fiscal_year(self):
        for rec in self:
            date = rec.paid_date or rec.create_date
            if date:
                rec.fiscal_year = date.year
            else:
                rec.fiscal_year = fields.Date.today().year
                
    current_budget_amount = fields.Float(string="Current Year Budget",
                                #  compute="compute_budget_amount", 
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
    
    # @api.depends('budget_allocation_line.amount_total')
    # def compute_budget_amount(self):
    #     rec= self
    #     if rec.budget_allocation_line:
    #         amount_total = sum([r.amount_total for r in rec.budget_allocation_line if r.state in ['posted']])
    #         rec.budget_amount = amount_total
    #     else:
    #         rec.budget_amount = 0
            
    @api.depends('ng_account_budget_line.allocated_amount')
    def compute_budget_amount(self):
        rec= self
        if rec.ng_account_budget_line:
            amount_total = sum([r.allocated_amount for r in rec.ng_account_budget_line])
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