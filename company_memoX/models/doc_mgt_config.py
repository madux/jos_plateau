from odoo import models, fields, api
from odoo.exceptions import ValidationError

class DocMgtConfig(models.Model):
    _name = "doc.mgt.config"
    _description = "Document Management Configuration Stored Data"
    
    memo_type_id = fields.Many2one("memo.type")
