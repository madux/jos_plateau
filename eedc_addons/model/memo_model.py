from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

class MemoModel(models.Model):
    _inherit = 'memo.model'

    employee_transfer_line_ids = fields.One2many( 
        'hr.employee.transfer.line', 
        'memo_id', 
        string='Employee Transfer Lines'
        )
    
    district_id = fields.Many2one("hr.district", string="District ID")


class Requestline(models.Model):
    _inherit = 'request.line'

    district_id = fields.Many2one("hr.district", string="District ID")


class AccountAccount(models.Model):
    _inherit = 'account.account'

    district_id = fields.Many2one('hr.district', string="District")

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    district_id = fields.Many2one('hr.district', string="District")