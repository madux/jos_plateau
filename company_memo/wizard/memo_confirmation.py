
from odoo import fields, models ,api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
import logging
from datetime import date, datetime, timedelta


class MemoDialogModel(models.TransientModel):
    _name="memo.confirmation.dialog"
    
    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name = fields.Text(string="Message",readonly=True,default=get_default)

 