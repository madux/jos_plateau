from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CRMLEAD(models.Model):
    _inherit = "crm.lead"

    memo_id = fields.Many2one('memo.model', string='Memo Reference')
    code = fields.Char(string='Code')
    
    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('crm.lead')
        vals['code'] = str(sequence)
        return super(CRMLEAD, self).create(vals)
