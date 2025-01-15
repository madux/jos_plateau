from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CompanyMemo(models.Model):
    _inherit = "memo.model"

    company_id = fields.Many2one(
        'res.company', 
        default=lambda s: s.env.user.company_id.id,
        string='Company'
        )
    
    branch_id = fields.Many2one('multi.branch', string='MDA Sector',
                                default=lambda self: self.env.user.branch_id.id, required=False)
    partner_id = fields.Many2one('res.partner', string='Partner',
                                default=lambda self: self.env.user.partner_id.id)
    
    external_memo_request = fields.Boolean(string='External request')
    is_top_account_user = fields.Boolean('Is top account user?', compute="compute_top_account_user")

    @api.depends('external_memo_request', 'is_internal_transfer')
    def compute_top_account_user(self):
        for rec in self:
            account_major_user = (self.env.is_admin() or self.env.user.has_group('ik_multi_branch.account_major_user'))
            if (self.is_internal_transfer or self.external_memo_request):
                if account_major_user:
                    rec.is_top_account_user = True
                else:
                    rec.is_top_account_user = False
            else:
                rec.is_top_account_user = False

    
    
     