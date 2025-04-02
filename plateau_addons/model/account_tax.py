from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class accountTax(models.Model):
    _inherit = "account.tax"
    
    contact_tax_type = fields.Selection(
        [
        ("none", "Zero / None Tax"), 
        ("Consultant", "Consultant"), 
        ("Individual", "Individual"),
        ("Contractor", "Contractor"),
        ], string="Contact Tax Type", 
        default="none",
        help="Contact tax type to help determine", 
    )
    