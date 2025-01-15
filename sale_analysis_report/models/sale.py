# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
 

class SaleOrder(models.Model):
    _inherit = "sale.order"

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
    )

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
    )

    product_remaining_qty = fields.Integer(
        string="Remaining Qty at store",
        compute="compute_product_item"
    )

    @api.depends('product_id')
    def compute_product_item(self):
        for rec in self:
            if rec.product_id and rec.order_id:
                current_wh_physical_stock_location_id = rec.order_id.warehouse_id.lot_stock_id
                qty_on_hand = rec.product_id.with_context({'location' : current_wh_physical_stock_location_id.id}).qty_available
                rec.product_remaining_qty = qty_on_hand
            else:
                rec.product_remaining_qty = False

    
    sales_person = fields.Many2one(
        'res.users',
        string="SalesPerson",
        related="order_id.user_id"
    )

      
    