from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http


class AccountMoveMemo(models.Model):
    _inherit = 'account.move'

    memo_id = fields.Many2one('memo.model', string="Memo Reference")
    # district_id = fields.Many2one('hr.district', string="District")
    origin = fields.Char(string="Source")
    stage_invoice_name = fields.Char(
        string="Stage invoice name", 
        store=True,
        help="Used to track if invoice is from the stage configuration",
        )
    stage_invoice_required = fields.Boolean(string="Stage invoice required?", store=True,
        help="Used to track if invoice is required based on the stage configuration")
    is_locked = fields.Boolean(string="Is locked", default=False)
    memo_state = fields.Char(string="Memo state", compute="compute_memo_state")
    payment_journal_id = fields.Many2one(
        'account.journal', 
        string="Payment Journal", 
        required=False,
        domain="[('id', 'in', suitable_journal_ids)]"
        )
    example_amount = fields.Float(store=False, compute='_compute_payment_term_example')
    example_date = fields.Date(store=False, compute='_compute_payment_term_example')
    example_invalid = fields.Boolean(compute='_compute_payment_term_example')
    example_preview = fields.Html(compute='_compute_payment_term_example')

    @api.depends('memo_id')
    def _compute_payment_term_example(self):
        for rec in self:
            if rec.invoice_payment_term_id:
                rec.example_amount = rec.invoice_payment_term_id.example_amount
                rec.example_date = rec.invoice_payment_term_id.example_date
                rec.example_invalid = rec.invoice_payment_term_id.example_invalid
                rec.example_preview = rec.invoice_payment_term_id.example_preview
            else:
                rec.example_amount =False
                rec.example_date = False
                rec.example_invalid = False
                rec.example_preview = False

    @api.depends('memo_id')
    def compute_memo_state(self):
        for rec in self:
            if rec.memo_id:
                rec.memo_state = rec.memo_id.state
            else:
                rec.memo_state = rec.memo_id.state

    def action_post(self):
        if self.memo_id:
            if self.memo_id.memo_type.memo_key == "soe":
                '''This is added to help send the soe reference to the related cash advance'''
                self.sudo().memo_id.cash_advance_reference.soe_advance_reference = self.memo_id.id
            self.memo_id.is_request_completed = True
            self.sudo().memo_id.update_final_state_and_approver()
            # self.memo_id.state = "Done"
        return super(AccountMoveMemo, self).action_post()
    
class AccountMove(models.Model):
    _inherit = 'account.move.line'

    code = fields.Char(string="Code")
    

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    memo_id = fields.Many2one('memo.model', string="Memo Reference")
    # district_id = fields.Many2one('hr.district', string="District")

    def reverse_moves(self):
        res = super(AccountMoveReversal, self).post()
        for rec in self.move_ids:
            if rec.memo_id:
                rec.memo_id.state = "Approve" # waiting for payment and confirmation
        return res

     