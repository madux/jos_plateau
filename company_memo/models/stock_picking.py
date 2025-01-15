from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    memo_id = fields.Many2one('memo.model', string='Memo Reference')

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        # self.update_memo_status('Done')
        # if self.memo_id and self.memo_id.memo_project_type != 'procurement':
        #     self.memo_id.is_request_completed = True
        #     self.sudo().memo_id.update_final_state_and_approver()
        return res

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        # self.update_memo_status('Done')
        # if self.memo_id and self.memo_id.memo_project_type != 'procurement':
        #     self.memo_id.is_request_completed = True
        #     self.sudo().memo_id.update_final_state_and_approver()
        return res
    

    # def update_memo_status(self, status):
    #     # not currently in use
    #     record = self.env['memo.model'].search([
    #         ('code', '=', self.origin)
    #         ], limit=1)
    #     if record:
    #         record.sudo().write({
    #             'state': status
    #             })
    

# class StockImmediateTransfer(models.TransientModel):
#     _inherit = 'stock.immediate.transfer'
#     _description = 'Immediate Transfer'

#     def process(self):
#         res = super(StockImmediateTransfer, self).process()
#         for transfer in self.immediate_transfer_line_ids:
#             transfer.picking_id.memo_id.is_request_completed = True
#         return res

