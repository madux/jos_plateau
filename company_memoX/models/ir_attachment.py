# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models,fields, _
from collections import defaultdict
from odoo.exceptions import AccessError, ValidationError, UserError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"
    
    stage_document_name = fields.Char(
        string="Stage document name", 
        store=True,
        help="Used to track if document is from the stage configuration",
        )
    
    stage_document_required = fields.Boolean(string="Stage document required?", store=True,
        help="Used to track if document is required based on the stage configuration")
    
    code = fields.Char(
        string="Code", 
        store=True,
        )
    is_locked = fields.Boolean(string="Is locked", default=False)
    memo_id = fields.Many2one('memo.model', string="Memo Reference")
