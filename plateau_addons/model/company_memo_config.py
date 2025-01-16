from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CompanyMemoConfig(models.Model):
    _inherit = "memo.config"

    branch_ids = fields.Many2many('multi.branch', string='MDA Sectors', required=False)
    