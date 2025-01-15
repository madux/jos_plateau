from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)
_BRANCH_KAFKA_KEY = "branch"

class EhaBranch(models.Model):
    _name = 'multi.branch'
    _description = 'Branch'

    name = fields.Char('Name', required=False)
    code = fields.Char('Code', readonly=False, default= lambda self :'XXXXXXXX')
     
    telephone_no = fields.Char("Telephone No")
    company_id = fields.Many2one('res.company', string='Company', required=False, readonly=True, default=lambda self: self.env['res.company']._company_default_get())
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char(required=False)
    state_id = fields.Many2one("res.country.state", string='State', domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country')
    is_testcenter = fields.Boolean('Is Test Center?')
    is_online_store = fields.Boolean('Is Online store?')
    alias_display = fields.Char(string="Alias", 
    help="This will be the name to display on the dropdown for shop")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    parent_id = fields.Many2one('multi.branch', 'Parent Branch')
    simplybook_location_id = fields.Char(string="Simplybook ID")
    active = fields.Boolean(default=True)

    @api.model
    @api.returns('self', lambda value: value.id)
    def _branch_default_get(self):
        return self.env['res.users']._get_default_branch()

    @api.model
    def create(self,vals):
        res = super(EhaBranch, self).create(vals)
        res._update_branch_code()
        return res

    def _update_branch_code(self):
        if self.city:
            code = self.city[0:4].upper() + ('%04d' % self.id)
            self.write({'code':code})

    @api.model
    def data_migration(self):
        pass
        # _logger.info('*** Starting Branch Migration **** ')
        # company = self.env.company #self.env['res.users']._get_company()
        # _logger.info('*** Company **** %s ', company)
        # branch = self.env['multi.branch'].create({
        #     'name':company.name,
        #     'company_id':company.id,
        #     'telephone_no': company.phone,
        #     'street': company.street,
        #     'street2': company.street2,
        #     'zip': company.zip,
        #     'city': company.city,
        #     'state_id': company.state_id.id,
        #     'country_id': company.country_id.id,
        #     })
        # _logger.info('*** Branch **** %s', branch)
        # self.env['res.users'].search([]).write({'branch_ids':[(6, 0, branch.ids)]})
        # models = [
        #     'res.partner',
        #     'account.reconcile.model',
        #     'account.account',
        #     'account.move',
        #     'account.move.line',
        #     # "account.move.tax",
        #     "account.move",
        #     "account.move.line",
        #     "account.partial.reconcile",
        #     "account.journal",
        #     "account.analytic.line",
        #     # "account.analytic.default",
        #     # "account.asset.asset",
        #     # "account.voucher",
        #     "account.payment",
        #     # 'account.move.refund',
        #     'account.bank.statement',
        #     'account.bank.statement.line',
        #     'account.analytic.account',
        # 'account.analytic.line','purchase.order', 'purchase.order.line', 'sale.order.line', "sale.order", 
        # "crm.team", "helpdesk.sla", "helpdesk.ticket"]
        # for model in models:
        #     self.env[model].search([]).write({'branch_id':branch.id})