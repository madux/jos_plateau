from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import misc, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil.relativedelta import relativedelta
import time
from datetime import datetime, timedelta 
from odoo import http


class AccountMoveMemo(models.Model):
    _inherit = 'account.move'

    memo_id = fields.Many2one('memo.model', string="Memo Reference")
    # district_id = fields.Many2one('hr.district', string="District")
    origin = fields.Char(string="Source")
    stage_invoice_name = fields.Char(
        string="Stage invoice name", 
        store=True,
        help="Used to track if invoice is from the stage configuration",
        )
    stage_invoice_required = fields.Boolean(string="Stage invoice required?", store=True,
        help="Used to track if invoice is required based on the stage configuration")
    is_locked = fields.Boolean(string="Is locked", default=False)
    memo_state = fields.Char(string="Memo state", compute="compute_memo_state")
    payment_journal_id = fields.Many2one(
        'account.journal', 
        string="Payment Journal", 
        required=False,
        domain="[('id', 'in', suitable_journal_ids)]"
        )
    example_amount = fields.Float(store=False, compute='_compute_payment_term_example')
    example_date = fields.Date(store=False, compute='_compute_payment_term_example')
    example_invalid = fields.Boolean(compute='_compute_payment_term_example')
    example_preview = fields.Html(compute='_compute_payment_term_example')
    # project_id = fields.Many2one('account.analytic.account', 'Project')

    @api.depends('memo_id')
    def _compute_payment_term_example(self):
        for rec in self:
            if rec.invoice_payment_term_id:
                rec.example_amount = rec.invoice_payment_term_id.example_amount
                rec.example_date = rec.invoice_payment_term_id.example_date
                rec.example_invalid = rec.invoice_payment_term_id.example_invalid
                rec.example_preview = rec.invoice_payment_term_id.example_preview
            else:
                rec.example_amount =False
                rec.example_date = False
                rec.example_invalid = False
                rec.example_preview = False

    @api.depends('memo_id')
    def compute_memo_state(self):
        for rec in self:
            if rec.memo_id:
                rec.memo_state = rec.memo_id.state
            else:
                rec.memo_state = rec.memo_id.state

    def validate_invoice_lines(self):
        pass
        # invline_without_price = self.mapped('invoice_line_ids').filtered(
        #                 lambda s: s.quantity >= 0 and s.price_unit <= 0
        #                 )
        # if invline_without_price:
        #     raise ValidationError(f"All invoice line must have a unit price amount greater than 0 {[rec.product_id.name for rec in self.invoice_line_ids]} ")
        
    def action_post(self):
        if self.memo_id:
            self.validate_invoice_lines()
            if self.memo_id.memo_type.memo_key == "soe":
                '''This is added to help send the soe reference to the related cash advance'''
                self.sudo().memo_id.cash_advance_reference.soe_advance_reference = self.memo_id.id
                # self.memo_id.is_request_completed = True
            # self.memo_id.state = "Done"
        return super(AccountMoveMemo, self).action_post()
    
    def _prepare_po_vals(self):
        invoice_lines = []
        journal_id = self.env['account.journal'].search(
            [('type', '=', 'sale'),
             ('code', '=', 'INV')
             ], limit=1)
        for po in self.memo_id.po_ids:
            if po.order_line:
                for line in po.order_line:
                    invoice_lines.append(
                        {
                            'name': line.product_id.name if line.product_id else line.name,
                            'ref': f'{line.order_id.name}',
                            'account_id': line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id if line.product_id else journal_id.default_account_id.id,
                            'price_unit': line.price_unit, 
                            'price_total': line.price_total, 
                            'quantity': line.qty_invoiced if line.qty_invoiced > 0 else line.product_qty,
                            'invoice_origin': line.order_id.name,
                            'tax_ids': line.taxes_id.ids,
                            'move_id': self.id,
                            'discount': 0.0,
                            'product_uom_id': line.product_id.uom_id.id if line.product_id else None,
                            'product_id': line.product_id.id if line.product_id else None,
                        }
                        )
        paid_vendor_invoice_lines = self.memo_id.mapped('invoice_ids').filtered(
            lambda bills: bills.move_type in ["in_invoice", "in_receipt"] and \
                bills.payment_state not in ['paid', 'partial', 'in_payment'])
        if paid_vendor_invoice_lines:
            for invoice in paid_vendor_invoice_lines:
                for line in invoice.invoice_line_ids:
                    invoice_lines.append(
                        {
                            'name': line.product_id.name if line.product_id else line.name,
                            'ref': f'{line.name}',
                            'account_id': line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id if line.product_id else journal_id.default_account_id.id,
                            'price_unit': line.price_unit, # pr.used_total,
                            'price_total': line.price_total, # pr.used_total,
                            'quantity': line.quantity,
                            'invoice_origin': line.name,
                            'tax_ids': line.tax_ids.ids,
                            'move_id': self.id,
                            'discount': 0.0,
                            'product_uom_id': line.product_id.uom_id.id if line.product_id else None,
                            'product_id': line.product_id.id if line.product_id else None,
                        }
                        )
                    
        return invoice_lines # [{}, {}, {}]

    def action_populate_all_project_pos(self):
        if self.memo_id:
            if self.env.user.id not in [r.user_id.id for r in self.memo_id.stage_id.approver_ids]:
                raise ValidationError("You are not allowed to perform this transaction")
            if self.state == "draft": 
                self.invoice_line_ids = [(3, inv.id) for inv in self.invoice_line_ids]
                invoice_line_ids = self._prepare_po_vals()
                self.invoice_line_ids = [(0, 0, invoice_dict) for invoice_dict in invoice_line_ids]
        else:
            raise ValidationError('There is no PO tied to the selected Project. Kindly check the PO lines or invoice of the Project')
    
class AccountMove(models.Model):
    _inherit = 'account.move.line'

    code = fields.Char(string="Code")
    

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    memo_id = fields.Many2one('memo.model', string="Memo Reference")
    # district_id = fields.Many2one('hr.district', string="District")

    def reverse_moves(self):
        res = super(AccountMoveReversal, self).post()
        for rec in self.move_ids:
            if rec.memo_id:
                rec.memo_id.state = "Approve" # waiting for payment and confirmation
        return res

     