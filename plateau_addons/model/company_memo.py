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
    request_mda_from = fields.Many2one('multi.branch', string='MDA Sector')
    partner_id = fields.Many2one('res.partner', string='Partner',
                                default=lambda self: self.env.user.partner_id.id)
    
    external_memo_request = fields.Boolean(string='Is External request')
    is_contract_memo_request = fields.Boolean(string='Is Contract request')
    is_top_account_user = fields.Boolean('Is top account user?', compute="compute_top_account_user")
    bank_partner_id = fields.Many2one('res.partner', string='Bank', help="Select the bank to send payment schedule")

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

    def generate_bank_schedule(self):
        # will be used to generate bank schedule and send to bank
        for rec in self:
            if not self.bank_partner_id:
                raise ValidationError("Please select bank to send Bank schedule to")
            if not self.bank_partner_id.email:
                raise ValidationError(f"Selected bank must also have a bank partner: Record id {rec.id}")
     