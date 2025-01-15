from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# class PurchaseOrder(models.Model):
#     _inherit = "purchase.order"

    # origin = fields.Char(string='Source')
    # memo_id = fields.Many2one('memo.model', string='Memo Reference')

    # def update_memo_status(self, status):
    #     if self.memo_id:
    #         self.memo_id.state = status
    #     else: 
    #         if self.origin:
    #             memo = self.env['memo.model'].browse([
    #                 ('code', '=', self.origin)
    #                 ])
    #             if memo:
    #                 memo.state = status
    
    # def button_confirm(self):
    #     res = super(PurchaseOrder, self).button_confirm()
    #     self.update_memo_status('Done')
    #     return res
    
    # def button_cancel(self):
    #     res = super(PurchaseOrder, self).button_cancel()
    #     self.update_memo_status('Refuse') 
    #     return res
     