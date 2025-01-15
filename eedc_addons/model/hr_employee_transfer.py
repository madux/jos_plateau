from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

class HREMployeeTransfer(models.Model):
    _name = 'hr.employee.transfer'

    employee_ids = fields.Many2many('hr.employee')
    employee_transfer_lines = fields.One2many( 
        'hr.employee.transfer.line', 
        'employee_transfer_id', 
        string='Transfer Details'
        )
    memo_id = fields.Many2one('memo.model', string='Memo Id')
    

    
    def update_transfer_details(self):
        for transfer in self:
            transfer.employee_ids.write({
                'department_id': transfer.transfer_dept.id,
                'job_id': transfer.new_role.id,
            })


class HREmployeeTransferLine(models.Model):
    _name = 'hr.employee.transfer.line'

    memo_id = fields.Many2one('memo.model', string='Memo ref')
    employee_transfer_id = fields.Many2one('hr.employee.transfer', string='Employee Transfer')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    current_dept_id = fields.Many2one('hr.department', string='Current Department')
    transfer_dept = fields.Many2one('hr.department', string='Transfer Department')
    new_role = fields.Many2one('hr.job', string='New Role')
    new_district = fields.Many2one('hr.district', string='New District')


