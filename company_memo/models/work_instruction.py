# Copyright 2024 MAACH SOFTWARE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class MemoWorkInstruction(models.Model):
    _name = "memo.work.instruction"

    
    memo_id = fields.Many2one(
        'memo.model',
    )
    description = fields.Text(string="Description")
    work_order_code = fields.Char(
        string="Work Order Code", 
        store=True,
        help="Used to store work order number"
        )
    
    def print_work_instruction(self):
        if not self.work_order_code:
            self.work_order_code = self.env['ir.sequence'].next_by_code('work-instruction')
        if not self.memo_id.qr_code_commonpass:
            self.memo_id.qr_code()
        report = self.env["ir.actions.report"].search(
            [('report_name', '=', 'company_memo.work_instruction_print_item_report_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env.ref('company_memo.print_work_instruction_item_report').report_action(self)

    