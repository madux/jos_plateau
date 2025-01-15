from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    code = fields.Char(string='Source')
    origin = fields.Char(string='Source')
    memo_id = fields.Many2one('memo.model', string='Memo Reference')
    memo_state = fields.Char(string='Memo state')
    memo_type = fields.Many2one(
        'memo.type',
        string='Memo type',
        required=False,
        copy=False
        )
    memo_type_key = fields.Char('Memo type key', readonly=True)
    
    def action_confirm(self):
        # is request completed is view_view_form used to determine if the entire process is done
        if self.memo_id:
            if self.memo_id.stage_id.approver_ids and \
                self.env.user.id not in [r.user_id.id for r in self.memo_id.stage_id.approver_ids]:
                raise ValidationError("You are not allowed to confirm this Purchase Order")
            # self.memo_id.is_request_completed = True
            # self.sudo().memo_id.update_final_state_and_approver()
        res = super(SaleOrder, self).action_confirm()
        return res

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if self.memo_id:
            # raise ValidationError('gjhjhgjg')
            self.memo_id.update_dashboard_finances()
        return res
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            number_code, code= '', ''
            if vals.get('name', _("New")) == _("New"):
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals['date_order'])
                ) if 'date_order' in vals else None
                number_code = self.env['ir.sequence'].next_by_code(
                    'sale.order', sequence_date=seq_date) or _("New")
            if 'memo_id' in vals and vals['memo_id']:
                memo_id = self.env['memo.model'].browse([vals['memo_id']])
                code = memo_id.code + '-' if memo_id else ''
            vals['name'] = f"{code}{number_code.replace('S', '')}"
        return super().create(vals_list)
  
    def action_populate_all_project_pos(self):
        if self.memo_id:
            if self.memo_id.po_ids or self.invoice_ids:
                if self.env.user.id not in [r.user_id.id for r in self.memo_id.stage_id.approver_ids]:
                    raise ValidationError("You are not allowed to perform this transaction")
                if self.state == "draft": 
                    self.order_line = [(3, inv.id) for inv in self.order_line]
                    line_ids = self._prepare_so_line_vals()
                    self.order_line = [(0, 0, invoice_dict) for invoice_dict in line_ids]

            else:
                raise ValidationError('There is no PO / Invoice line added ')
        else:
            raise ValidationError('There is no PO tied to the selected Project. Kindly check the PO lines or invoice of the Project')
    
    def _prepare_so_line_vals(self):
        invoice_lines = []
        # journal_id = self.env['account.journal'].search(
        #     [('type', '=', 'sale'),
        #      ('code', '=', 'INV')
        #      ], limit=1)
        for po in self.memo_id.po_ids:
            if po.order_line:
                for line in po.order_line:
                    invoice_lines.append(
                        {
                            'name': line.product_id.name if line.product_id else line.name,
                            # 'account_id': line.product_id.property_account_income_id.id or line.product_id.categ_id.property_account_income_categ_id.id if line.product_id else journal_id.default_account_id.id,
                            'price_unit': line.price_unit, 
                            'price_total': line.price_total, 
                            'product_uom_qty': line.qty_invoiced if line.qty_invoiced > 0 else line.product_qty,
                            'tax_id': line.taxes_id.ids,
                            'order_id': self.id,
                            'discount': 0.0,
                            'product_uom': line.product_id.uom_id.id if line.product_id else None,
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
                            'price_unit': line.price_unit, 
                            'price_total': line.price_total,  
                            'product_uom_qty': line.quantity,
                            'tax_id': line.tax_ids.ids,
                            'order_id': self.id,
                            'discount': 0.0,
                            'product_uom': line.product_id.uom_id.id if line.product_id else None,
                            'product_id': line.product_id.id if line.product_id else None,
                        }
                        )
                    
        return invoice_lines # [{}, {}, {}]
    