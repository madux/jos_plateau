# Copyright 2024 MAACH SOFTWARE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = "stock.location"

    code = fields.Char(
        help="Unique code for every stock.location",
    )

    @api.constrains('code', 'name')
    def _validate_code(self):
        if not self.code:
            StockLocation = self.env['stock.location'].search([
                '|',('code', '=', self.code),
                ('name', '=', self.name),
                ])
            if StockLocation and len(StockLocation.ids) > 1:
                raise ValidationError("You have already created a stage with the same name or code")

