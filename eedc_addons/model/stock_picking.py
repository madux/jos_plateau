from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def update_memo_status(self, status):
        record = self.env['memo.model'].search([
            ('code', '=', self.origin)
            ], limit=1)
        if record:
            record.sudo().write({'state': status})
    
    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        self.update_memo_status('Done')
        return res
    
    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        self.update_memo_status('Done')
        return res
    
     