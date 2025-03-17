from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class accountTax(models.Model):
    _inherit = "account.tax"
    
    contact_tax_type = fields.Selection(
        [
        ("", ""), 
        ("Consultant", "Consultant"), 
        ("Individual", "Individual"),
        ("Contractor", "Contractor"),
        ], string="Contact Tax Type", 
        default="Individual",
        help="Contact tax type to help determine", 
    )
    