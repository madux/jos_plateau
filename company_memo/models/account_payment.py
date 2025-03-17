from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    memo_reference = fields.Many2one('memo.model', string="Memo Reference")
    external_memo_request = fields.Boolean(string="External memo request")
    is_contract_memo_request = fields.Boolean(string="Is contract request")
    is_saved = fields.Boolean(string='Is Saved')
    allow_bypass = fields.Boolean(string='Allow Bypass', 
                                  default=True,
                                   help="Used to bypass validations of outstanding/payment reciepts account")
    
    memo_state = fields.Char(string="Memo state", compute="compute_memo_state")
    
    @api.depends('memo_reference')
    def compute_memo_state(self):
        for rec in self:
            if rec.memo_reference:
                rec.memo_state = rec.memo_reference.state
            else:
                rec.memo_state = False
    
    @api.depends('partner_id', 'journal_id', 'destination_journal_id')
    def _compute_is_internal_transfer(self):
        for payment in self:
            if not payment.external_memo_request:
                payment.is_internal_transfer = payment.partner_id \
                                           and payment.partner_id == payment.journal_id.company_id.partner_id \
                                           and payment.destination_journal_id
            else:
                payment.is_internal_transfer = True

    def action_post(self):
        if self.move_id and self.move_id.memo_id and not self.is_saved:
            raise ValidationError("Please check your transactions properly and tick the confirm option before confirming")
        res = super(AccountPayment, self).action_post()
        # if self.memo_reference:
        # self.memo_reference.is_request_completed = True
        # self.sudo().memo_reference.finalize_payment()
        return res
    
    
    def _synchronize_from_moves(self, changed_fields):
        # EXTENDS account
        for rec in self:
            if rec.allow_bypass:
                # Constraints bypass when entry is linked to an customized modules like easypay, eedc, 
                # jos_plateau.
                # Context is not enough, as we want to be able to delete
                # and update those entries later on.
                return
        return super()._synchronize_from_moves(changed_fields)
    
    # @api.model
    # def create(self, vals):
    #     if 'is_saved' in vals:
    #         vals['is_saved'] = True 
    #     res = super(AccountPayment, self).create(vals)
    #     return res
    
    
    # def write(self, vals):
    #     'is saved is used to determine if the cashier has properly entered his account lines correctly'
    #     if 'is_saved' in vals:
    #         vals['is_saved'] = True 
    #     res = super(AccountPayment, self).write(vals)
    #     return res
    
 


 