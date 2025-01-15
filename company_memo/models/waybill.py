# Copyright 2024 MAACH SOFTWARE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class MemoTransportWaybill(models.Model):
    _name = "memo.transport.waybill"

    product_id = fields.Many2one(
        'product.product',
    )
    memo_id = fields.Many2one(
        'memo.model',
    )
    item = fields.Char(string="Item")
    current_location = fields.Char(string='Current Location?')
    quantity = fields.Integer(string='Qty to move', default=1)
    waybill_number = fields.Char(string='Waybill No.')
    waybill_desc = fields.Text(string='Waybill Description.')
    loaded_by = fields.Char(string='Loaded By')
    loaded_date = fields.Datetime(string='Load Date')
    uom = fields.Char(string='UOM')


    