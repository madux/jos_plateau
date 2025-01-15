from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class productTemplate(models.Model):
    _inherit = "product.template"

    is_vehicle_product = fields.Boolean("Is vehicle", default=False)
    vehicle_plate_number = fields.Char("Vehicle Plate Number")
    vehicle_reg_number = fields.Char("Vehicle Reg Number")
    
    vehicle_color = fields.Char("Vehicle Color")
    vehicle_model = fields.Char("Vehicle Model")
    vehicle_make = fields.Char("Vehicle Make")
    is_available = fields.Boolean("Is Available?")
    last_service_by = fields.Char("Last serviced by")
    last_driven_by = fields.Char("Last driven by")
    not_to_be_moved = fields.Boolean("No to be moved")
    vehicle_status = fields.Selection(
        [
            ("Active", "Active"),
            ("Faulty", "Faulty"),
            ("Salvaged", "Salvaged"),
            ("Long_used", "Long used"),
            ("Deprecated", "Deprecated"),
            ("Damaged", "Damaged"),
            
        ], 
        readonly=False,
        default="Active",
        store=True,
    )
    
     