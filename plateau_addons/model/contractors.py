from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from num2words import num2words


class resContractors(models.Model):
    _name = "res.contractors"

    contractor_id = fields.Many2one(
        'res.partner', 
        string='Contractor'
        )
    
    bank_id = fields.Many2one(
        'res.partner', 
        string='Bank',
        domain="[('is_bank', '=', True)]"
        )
    memo_id = fields.Many2one(
        'memo.model', 
        string='memo', 
        )
    
    branch_id = fields.Many2one(
        'multi.branch', 
        string='MDA', 
        default=lambda self: self.env.user.branch_id
        )
    
    contact_tax_type = fields.Selection(
        [
        ("", ""), 
        ("Consultant", "Consultant"), 
        ("Individual", "Individual"),
        ("Contractor", "Contractor"),
        ], string="Contact Tax Type", 
        default="",
        help="Contact tax type to help determine", 
    )
    
    branch_account_id = fields.Many2one(
        'account.account', 
        string='Account to Debit', 
        default=lambda self: self.env.user.branch_id.default_account_id.id
        )
    debit_account_number = fields.Char(string='Debit Account')
    credit_account_number = fields.Char(string='Contractor Credit Account')
    contractor_phone = fields.Char(string='Phone',related="contractor_id.phone")
    contractor_email = fields.Char(string='Email',related="contractor_id.email")
    bank_phone = fields.Char(string='Bank Phone',related="bank_id.phone")
    bank_email = fields.Char(string='Bank email', related="bank_id.email")
    description = fields.Char(string='Bank Phone')
    scheduled_pay_date = fields.Date(string='Schedule Date')
    amount_total = fields.Char(string='Amount total', compute="_comput_total")
    payment_ids = fields.Many2many(
        "account.payment",
        string="Payment"
        )
    amount_in_words = fields.Char(compute="_compute_amount_in_words")

    def _compute_amount_in_words(self):
        for record in self:
            payment_amount = sum([r.amount_total for r in self.payment_ids])
            total = payment_amount if payment_amount > 0 else self.amountfig
            amount_in_words = num2words(total, lang='en')
            record.amount_in_words = amount_in_words.upper() if amount_in_words and total > 0 else ""
     
    
    def _comput_total(self):
        for rec in self:
            total = sum([r.amount_total for r in rec.payment_ids])
            rec.amount_total = total
        
    
    