# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
import csv 
import io
import xlwt
from datetime import datetime, timedelta
import base64
import random
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.parser import parse
import ast 
import logging
_logger = logging.getLogger(__name__)


class PaymentSchedule(models.Model):
    _name = "ma.payment.schedule"
    _description = 'Move payment schedule'

    def _get_move_for_schedule(self):
        '''Show only payment that are not for schedule'''
        moves_not_paid = self.env['account.move'].search([
           ('payment_state', 'not in', ['paid', 'in_payment']),
           ('schedule_for_payment_date', '=', False),
        ])
        return [('id', 'in', [rec.id for rec in moves_not_paid])]
    
    name = fields.Char(string="Title")
    account_move_ids = fields.Many2many(
        'account.move',
        'payment_schedule_move_rel', 
        'payment_schedule_move_id', 
        'patyment_move_id',
        string="Invoices",
        domain=lambda self: self._get_move_for_schedule(),
        )
    schedule_date = fields.Date(
        'Schedule Date', 
        default=fields.Date.today()
        )
    due_date = fields.Date(
        'Due Date', 
        )
    bank_id = fields.Many2one(
        'res.bank', 
        string="Bank"
        )
    memo_id = fields.Many2one(
        'memo.model', 
        string="Memo Id"
        )
    activate_cron = fields.Boolean(
        string="Activate Cron"
        )
    active = fields.Boolean(
        string="Active",
        default=True
        )
    excel_file = fields.Binary('Download Excel file', readonly=True)
    filename = fields.Char('Excel File')
    
    def generate_and_send_schedule(self):
        """This forwards the schedule to the respective bank"""
        account_move_ids = self.account_move_ids
        if account_move_ids:
            headers = [
                'Invoice Ref', 
                'Partner/Beneficiary', 
                'Beneficiary Phone', 
                'Beneficiary Email', 
                'Beneficiary Account Number', 
                'Beneficiary Bank', 
                'Scheduled Bank'
                ]
            style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
                    num_format_str='#,##0.00')
            wb = xlwt.Workbook()
            ws = wb.add_sheet(self.name, cell_overwrite_ok=True)
            colh = 0
            # ws.write(0, 6, 'RECORDS GENERATED: %s - On %s' %(self.name, datetime.strftime(fields.Date.today(), '%Y-%m-%d')), style0)
            for head in headers:
                ws.write(0, colh, head)
                colh += 1
            rowh = 1
            for move in account_move_ids:
                dynamic_column = 0
                partnerbank_ids = move.partner_id.mapped('bank_ids').filtered(lambda s: s.allow_out_payment == True) 
                partnerbank_id = partnerbank_ids[0]
                ws.write(rowh, dynamic_column, move.name)
                ws.write(rowh, dynamic_column + 1, move.partner_id.name)
                ws.write(rowh, dynamic_column + 2,  move.partner_id.phone)
                ws.write(rowh, dynamic_column + 3,  move.partner_id.email)
                ws.write(rowh, dynamic_column + 4,  partnerbank_id.acc_number)
                ws.write(rowh, dynamic_column + 5,  partnerbank_id.bank_id.name)
                ws.write(rowh, dynamic_column + 6, self.bank_id.name)
                rowh += 1
            fp = io.BytesIO()
            wb.save(fp)
            filename = "{} ON {}.xls".format(
                self.name, datetime.strftime(fields.Date.today(), '%Y-%m-%d'), style0)
            self.excel_file = base64.encodestring(fp.getvalue())
            attachementObj = self.attachment_render(self.name, base64.encodestring(fp.getvalue()), 'application/vnd.ms-excel')
            self.send_mail([attachementObj])
            self.filename = filename
            fp.close()
            return { 
                    'type': 'ir.actions.act_url',
                    'url': '/web/content/?model=ma.payment.schedule&download=true&field=excel_file&id={}&filename={}'.format(self.id, self.filename),
                    'target': 'current',
                    'nodestroy': False,
            }
        else:
            raise ValidationError('No invoice selected')
    
    def attachment_render(self, attachment_name, report_binary, mimetype):
        attachmentObj = self.env['ir.attachment'].create({
            'name': attachment_name,
            'type': 'binary',
            'datas': report_binary,
            'store_fname': attachment_name,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': mimetype
        })
        return attachmentObj.id
    
    def send_mail(self, attachments):
        if not self.bank_id.email:
            raise ValidationError('Selected bank must have email address')
        body_msg = f"""Dear {self.bank_id.name}, <br/>
        I wish to notify you that a payment schedule with description, '{self.name}',\
         have been forwared to you for proper vetting and paymnent <br/>\
        Yours Faithfully<br/>{self.env.user.company_id.name}"""
        mail_data = {
                'email_from': self.env.user.company_id.email,
                'subject': self.name,
                'email_to': self.bank_id.email,
                'reply_to': self.env.user.company_id.email,
                # 'email_cc': ,
                'body_html': body_msg,
                'attachment_ids': [(6, 0, attachments)]
            }
        mail_id = self.env['mail.mail'].sudo().create(mail_data)
        self.env['mail.mail'].sudo().send(mail_id)
    
    
    

    