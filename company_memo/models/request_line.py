from odoo import models, fields, api, _


class RequestLine(models.Model):
    _name = "request.line"

    memo_id = fields.Many2one(
        "memo.model", 
        string="Memo ID"
        )
    product_id = fields.Many2one(
        "product.product", 
        string="Product ID"
        )
    code = fields.Char(
        string="Product code", 
        related="product_id.default_code"
        )
    description = fields.Char(
        string="Description"
        )
    # district_id = fields.Many2one("hr.district", string="District ID")
    quantity_available = fields.Float(string="Qty Requested")
    used_qty = fields.Float(string="Qty Used")
    amount_total = fields.Float(string="Unit Price")
    used_amount = fields.Float(string="Amount Used")
    note = fields.Char(string="Note")
    code = fields.Char(string="code")
    to_retire = fields.Boolean(string="To Retire", help="Used to select the ones to retire", default=False)
    retired = fields.Boolean(string="Retired", help="Used to select determined retired", default=False)
    state = fields.Char(string="State")
    source_location_id = fields.Many2one("stock.location", string="Source Location")
    dest_location_id = fields.Many2one("stock.location", string="Destination Location")
    # memo_type = fields.Selection(
    #     [
    #     ("Payment", "Payment"), 
    #     ("loan", "Loan"), 
    #     ("Internal", "Internal Memo"),
    #     ("employee_update", "Employee Update Request"),
    #     ("material_request", "Material request"),
    #     ("procurement_request", "Procurement Request"),
    #     ("vehicle_request", "Vehicle request"),
    #     ("leave_request", "Leave request"),
    #     ("server_access", "Server Access Request"),
    #     ("cash_advance", "Cash Advance"),
    #     ("soe", "Statement of Expense"),
    #     ("recruitment_request", "Recruitment Request"),
    #     ], string="Memo Type")
    memo_type = fields.Many2one(
        'memo.type',
        string='Memo type',
        required=True,
        copy=False
        )
    memo_type_key = fields.Char('Memo type key', readonly=True)#, related="memo_type.memo_key")
    
    