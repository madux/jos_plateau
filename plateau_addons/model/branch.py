from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


import logging

_logger = logging.getLogger(__name__)

class multiBranch(models.Model):
    _inherit = "multi.branch"
    
    account_branch_id = fields.Many2one('account.public.segment', string='MDA Economic Segment')

