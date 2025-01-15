# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import ValidationError, UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    branch_id = fields.Many2one(
        'multi.branch', 'MDA Sector', default=lambda self: self.env['res.partner']._branch_default_get())

    @api.model
    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res.update({'branch_id': self.branch_id.id})
        return res

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        # for rec in self:
        if self.branch_id:
            picking_type = self.env['stock.picking.type'].search(
                [('warehouse_id.branch_id', '=', self.branch_id.id), ('code', '=', 'incoming')], limit=1)
            if picking_type:
                self.picking_type_id = picking_type.id
            else:
                raise ValidationError(
                    'The Logged in User branch does not have any assigned Receipt Warehouse')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    branch_id = fields.Many2one(
        'multi.branch', 'MDA Sector', default=lambda self: self.env['res.partner']._branch_default_get())
