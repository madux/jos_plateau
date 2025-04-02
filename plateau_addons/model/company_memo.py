from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64


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
    
    contractor_ids = fields.One2many('res.contractors', 'memo_id', string='Contractors')
    
    external_memo_request = fields.Boolean(string='Is External request')
    is_contract_memo_request = fields.Boolean(string='Is Contract request')
    is_top_account_user = fields.Boolean('Is top account user?', compute="compute_top_account_user")
    
    bank_partner_id = fields.Many2one('res.partner', string='Bank-', help="Select the bank to send payment schedule")
    bank_account_number = fields.Char(string='Bank Account')
    scheduled_pay_date = fields.Date(string='Scheduled Pay date')

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
        for rec in self.contractor_ids:
            if not rec.bank_id or not rec.contractor_id:
                raise ValidationError("Please select bank to send Bank schedule to")
            if not rec.bank_email or not rec.contractor_email:
                raise ValidationError(f"Selected contractor and bank must also have an email: Record id {rec.id}")
            payment_not_posted = rec.mapped('payment_ids')
            for pnp in payment_not_posted:
                if pnp.state not in ['posted']: #.filtered(lambda s: s.state not in ['posted'] and not s.destination_journal_id)
                    #if payment_not_posted:
                    raise ValidationError("Each contractor payment lines must be posted")
        
        # todo send mail 
        return self.env.ref('plateau_addons.print_payment_schedule_report').report_action(self)
    
    def generate_external_bank_payment_schedule(self):
        # will be used to generate bank schedule and send to bank
        for rec in self:
            if not rec.bank_partner_id or not rec.scheduled_pay_date:
                raise ValidationError("Please select bank to send Bank schedule to")
            if not rec.bank_partner_id.email:
                raise ValidationError(f"Selected bank must also have an email: Record id {rec.id}")
            if not rec.scheduled_pay_date:
                raise ValidationError("Please select schedule date")
            payment_not_posted = rec.mapped('payment_ids')
            for pnp in payment_not_posted:
                if pnp.state not in ['posted']: 
                    raise ValidationError("Each payment lines must be posted before generating bank schedule")
        # todo send mail 
        return self.env.ref('plateau_addons.print_external_payment_schedule_report').report_action(self)
            
    def print_payment_schedule_report(self):
        if not self.contractor_ids:
            raise ValidationError("Sorry !!! There is no contractor line to print mandate")
        return self.env.ref('company_memo.print_payment_schedule_report').report_action(self)
    
    def print_budget_certifcation(self):
        # create report 
        # generate the report as attachment
        # create attachment on the attachment line
        self.has_print_budget_certificate = True
        report_id = self.env.ref('plateau_addons.print_budget_certificate_report')
        pdf, report_format = report_id._render_qweb_pdf(report_id, self.id)
        pdf_content = base64.b64encode(pdf)
        attachment = self.generate_memo_attachment(f"Budget Certificate {self.id}.pdf", pdf_content)
        if attachment:
            self.attachment_ids = [(4, attachment.id)]
            return {
                'type': 'ir.actions.act_url',
                'name': 'Budget Certificate',
                'url': '/web/content/%s/%s?download=true' % (attachment.id, attachment.name),
            }