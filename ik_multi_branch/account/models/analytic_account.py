# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    branch_id = fields.Many2one('multi.branch', string='MDA Sector', required=False, default=lambda self: self.env.user.partner_id.branch_id)


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    branch_id = fields.Many2one('multi.branch', string='MDA Sector',required=False, readonly=True, default=lambda self: self.env.user.partner_id.branch_id)

    
    @api.constrains('branch_id', 'account_id')
    def _check_company_id(self):
        for line in self:
            if line.account_id.branch_id.company_id and line.branch_id.company_id.id != line.account_id.branch_id.company_id.id:
                raise ValidationError(_('The selected account belongs to another company than the one you\'re trying to create an analytic item for'))
