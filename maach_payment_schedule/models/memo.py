# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
import logging
_logger = logging.getLogger(__name__)


class Memo(models.Model):
    _inherit = "memo.model"
    
    def action_generate_payment_schedule(self): # Register Payment
        memo_id = self.env['ma.payment.schedule'].search([('memo_id', '=', self.id)], limit=1)
        view_id = self.env.ref('maach_payment_schedule.ma_payment_schedule_form')
        
        val = {
            'name':'Generate Payment schedule',
            'view_mode': 'form',
            'view_id': view_id.id,
            'view_type': 'form',
            'res_model': 'ma.payment.schedule',
            'type': 'ir.actions.act_window',
            'domain': [],
            'target': 'current'
            } 
        if memo_id:
            val.update({
                'res_id': memo_id.id
            })
        else:
            val.update({
                'context': {
                    'default_account_move_ids': self.invoice_ids.ids,
                    'default_partner_id':self.employee_id.user_id.partner_id.id,  
                    'default_memo_id':self.id,  
                    'default_name': f'PS/{self.code}',
                }
            })
            
        
        return val