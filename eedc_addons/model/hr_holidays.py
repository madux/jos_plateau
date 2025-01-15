from odoo import models, fields, api, _


class HRLeave(models.Model):
    _inherit = "hr.leave"

    origin = fields.Char(string='Source')
    memo_id = fields.Many2one('memo.model', string='Memo Reference')

    def action_approve(self):
        res = super(HRLeave, self).action_approve()
        if self.memo_id:
            self.memo_id.state = "Done"
        return res
    
    def action_validate(self):
        res = super(HRLeave, self).action_validate()
        if self.memo_id:
            self.memo_id.state = "Done"
        return res
    
    def action_refuse(self):
        res = super(HRLeave, self).action_refuse()
        if self.memo_id:
            self.memo_id.state = "Refuse"
        return res
