from odoo import models, api


class AccountReportExtension(models.AbstractModel):
    _inherit = 'account.report'

    filter_branches = None

    def _build_options(self, previous_options=None):
        options = super(AccountReportExtension, self) # ._build_options(previous_options=previous_options)

        options['branches'] = []
        previous_company = False
        branches_read = self.env['multi.branch'].search([('company_id', 'in', self.env.user.company_ids.ids or [self.env.user.company_id.id])], order="company_id, name")
        for b in branches_read:
            if b.company_id != previous_company:
                options['branches'].append({'id': 'divider', 'name': b.company_id.name})
                previous_company = b.company_id
            options['branches'].append({'id': b.id,'name': b.name,'code': b.code,'selected': False})
        return options


    # def get_report_informations(self, options):
    #     opts = super(AccountReportExtension, self).get_report_informations(options=options)
    #     branches = self._get_branches()
    #     opts.update({'branches':branches})

    #     return opts

    # @api.model
    # def _get_options(self, previous_options=None):
    #     options = super(AccountReportExtension, self)._get_options(previous_options=previous_options)

    #     if self.env.context.get('branches'):
    #         options['branches'] = self.env.context['branches']

    #     return options

    # def _set_context(self, options):
    #     ctx = super(AccountReportExtension, self)._set_context(options=options)
    #     if options.get('branches'):
    #         branch_ids = [b.get('id') for b in options.get('branches') if b.get('selected')]
    #         ctx.update({'branch_ids':branch_ids})
    #     return ctx


    def _get_branches(self):
        branches_read = self.env['multi.branch'].search([], order="id, name")
        branches = []
        previous_company = False
        for b in branches_read:
            if b.company_id != previous_company:
                branches.append({'id': 'divider', 'name': b.company_id.name})
                previous_company = b.company_id
            branches.append({'id': b.id,'name': b.name,'code': b.code,'selected': True})
        return branches
