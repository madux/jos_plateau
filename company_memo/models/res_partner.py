from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    bank_id = fields.Many2one(
        'res.partner', 
        string='Bank Account'
        )
    is_bank = fields.Boolean('Is Bank?', help="used to indentify banks")
    
    