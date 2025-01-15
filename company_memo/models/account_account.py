from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http


class AccountAccount(models.Model):
    _inherit = 'account.account'

    # district_id = fields.Many2one('hr.district', string="District")
    