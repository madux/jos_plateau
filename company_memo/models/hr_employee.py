from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    administrative_supervisor_id = fields.Many2one('hr.employee', string="Administrative Supervisor")


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    code = fields.Char(string="Code Prefix")

