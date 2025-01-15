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

    @api.depends('partner_id', 'journal_id', 'destination_journal_id')
    def _compute_is_internal_transfer(self):
        for payment in self:
            if not payment.external_memo_request:
                payment.is_internal_transfer = payment.partner_id \
                                           and payment.partner_id == payment.journal_id.company_id.partner_id \
                                           and payment.destination_journal_id
            else:
                payment.is_internal_transfer = True

    # def action_post(self):
    #     res = super(AccountPayment, self).action_post()
    #     if self.memo_reference:
    #         # self.memo_reference.is_request_completed = True
    #         # self.sudo().memo_reference.finalize_payment()
    #     return res
 


 