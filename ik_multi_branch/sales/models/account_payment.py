# -*- coding: utf-8 -*-

from odoo import api, models, fields, _

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order', copy=False)
    branch_id = fields.Many2one(
        'multi.branch', 'MDA Sector', default=lambda self: self.env['multi.branch']._branch_default_get(), required=False)

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        for rec in self:
            if rec.sale_order_id:
                rec.partner_id = rec.sale_order_id.partner_id
                rec.amount = rec.sale_order_id.amount_total
                rec.currency_id = rec.sale_order_id.currency_id
                rec.ref = rec.sale_order_id.name