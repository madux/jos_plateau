from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

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
    po_attachment_ids = fields.Many2many(
        'ir.attachment',
        'purchase_order_attachment_rel',
        'purchase_order_id',
        'attachment_id',
        string='Attachment File')
    
    def update_memo_status(self, status):
        if self.memo_id:
            self.memo_id.state = status
        else: 
            if self.origin:
                memo = self.env['memo.model'].browse([
                    ('code', '=', self.origin)
                    ])
                if memo:
                    memo.state = status
    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        if self.memo_id.to_unfreezed_budget and self.memo_id.project_memo_id:
            self.memo_id.project_memo_id.update_dashboard_finances()
        else:
            if self.memo_id:
                self.memo_id.update_dashboard_finances()
        return res
    
    def button_confirm(self):
        # is request completed is used to determine if the entire process is done
        if self.memo_id:
            if self.memo_id.stage_id.approver_ids and \
                self.env.user.id not in [r.user_id.id for r in self.memo_id.stage_id.approver_ids]:
                raise ValidationError("You are not allowed to confirm this Purchase Order")
            # self.memo_id.is_request_completed = True
            # self.sudo().memo_id.update_final_state_and_approver()
        # if self.memo_id.to_unfreezed_budget and self.memo_id.project_memo_id:
        if self.memo_id.project_memo_id:
            self.memo_id.project_memo_id.update_dashboard_finances()
        else: 
            if self.memo_id:
                self.memo_id.update_dashboard_finances()
        res = super(PurchaseOrder, self).button_confirm()
        return res
    
    def button_view_po(self):
        view_id = self.env.ref('company_memo.company_memo_purchase_order_form_view').id
        ret = {
            'name': "Project Purchase Order",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'purchase.order',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            # 'domain': [],
            'target': 'current'
            }
        return ret

    def action_view_picking(self):
        if self.memo_id:
            appr1 = [r.user_id.id for r in self.memo_id.stage_id.approver_ids]
            appr2 = [r.user_id.id for r in self.memo_id.project_memo_id.stage_id.approver_ids]
            approver_ids = appr1 + appr2
            if self.env.user.id not in approver_ids:
                # [r.user_id.id for r in self.memo_id.stage_id.approver_ids]:
                raise ValidationError("You are not allowed to confirm this product receipts")
        result = super(PurchaseOrder, self).action_view_picking()
        return result
    
    ## dont cancel the memo because it might affect memo record
    # def button_cancel(self):
    #     res = super(PurchaseOrder, self).button_cancel()
    #     # self.update_memo_status('Done') 
    #     return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.browse()
        partner_vals_list = []
        for vals in vals_list:
            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            # Ensures default picking type and currency are taken from the right company.
            self_comp = self.with_company(company_id)
            if vals.get('name', 'New') == 'New':
                seq_date = None
                if 'date_order' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
                memo_id = False
                if 'memo_id' in vals or vals.get('memo_id'):
                    memoid = vals['memo_id'] or vals.get('memo_id')
                    memo_id = self.env['memo.model'].browse([memoid]).project_memo_id.code or ''
                po_code = self_comp.env['ir.sequence'].next_by_code('purchase.order', sequence_date=seq_date) or '/'
                vals['name'] = f"{memo_id or ''}{po_code.replace('P', '')}" if memo_id else f'{po_code}' # self_comp.env['ir.sequence'].next_by_code('purchase.order', sequence_date=seq_date) or '/'
            vals, partner_vals = self._write_partner_values(vals)
            partner_vals_list.append(partner_vals)
            orders |= super(PurchaseOrder, self_comp).create(vals)
        for order, partner_vals in zip(orders, partner_vals_list):
            if partner_vals:
                order.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
        return orders