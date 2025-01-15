# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
 

class PaymentSchedule(models.Model):
    _inherit = "account.move"
    _description = 'Account move'

      
    schedule_date = fields.Date(
        'Schedule Date',  
        ) 
    schedule_for_payment_date = fields.Boolean(
        string="Scheduled for Payment"
        )  