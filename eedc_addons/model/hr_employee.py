from odoo import models, fields, api, _
import random
import logging
from odoo.osv import expression

_logger = logging.getLogger(__name__)



# class HREmployeePublic(models.Model):
#     _inherit = "hr.employee.public"
class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"
    
    first_name = fields.Char(string="First name", required=True, copy=False)
    middle_name = fields.Char(string="Middle name", copy=False)
    last_name = fields.Char("Surname", required=True, copy=False)
    house_address = fields.Char(string='House Address', groups="base.group_user")
    age = fields.Char(string='Age', groups="base.group_user")
    local_government = fields.Many2one('res.lga', string='LGA')
    state_id = fields.Many2one('res.country.state', string='State')
    state_of_origin = fields.Char(string='State of Origin')
    lga = fields.Char(string='Local Goovernment') 
    rank_id = fields.Many2one('hr.rank', string='Rank')
    is_external_staff = fields.Boolean(string='Is External')
    external_company_id = fields.Many2one('res.partner', string='External Company')
    next_of_kin_ids = fields.Many2many('res.partner', 'nok_partner_public_rel', 'nok_partner_public_id', string='Next of Kin(s)')

    spouse_name = fields.Char(string='Spouse Name')
    spouse_telephone = fields.Char(string='Spouse Telephone')
    father_name = fields.Char(string="Father's Name")
    father_phone = fields.Char(string="Father's Phone")
    mother_name = fields.Char(string="Mother's Name")
    mother_phone = fields.Char(string="Mother's Phone")
    manager = fields.Boolean(string="Is a Manager")


class HREmployee(models.Model):
    _inherit = "hr.employee"

    # name = fields.Char(string="Name", compute='_compute_full_name', store=True, required=False)
    first_name = fields.Char(string="First name", required=True, copy=False)
    middle_name = fields.Char(string="Middle name", copy=False)
    last_name = fields.Char("Surname", required=True, copy=False)
    house_address = fields.Char(string='House Address', groups="base.group_user")
    age = fields.Char(string='Age')
    local_government = fields.Many2one('res.lga', string='LGA')
    state_id = fields.Many2one('res.country.state', string='State')
    state_of_origin = fields.Char(string='State of Origin')
    lga = fields.Char(string='Local Goovernment') 
    rank_id = fields.Many2one('hr.rank', string='Rank')
    is_external_staff = fields.Boolean(string='Is External')
    external_company_id = fields.Many2one('res.partner', string='External Company')
    next_of_kin_ids = fields.Many2many('res.partner', 'nok_partner_rel', 'nok_partner_id', string='Next of Kin(s)')

    spouse_name = fields.Char(string='Spouse Name')
    spouse_telephone = fields.Char(string='Spouse Telephone')
    father_name = fields.Char(string="Father's Name")
    father_phone = fields.Char(string="Father's Phone")
    mother_name = fields.Char(string="Mother's Name")
    mother_phone = fields.Char(string="Mother's Phone")
    manager = fields.Boolean(string="Is a Manager")

    def transfer_employee_action(self):
        rec_ids = self.env.context.get('active_ids', [])
        return {
              'name': 'Employee Transfer',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'hr.employee.transfer',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_employee_ids': rec_ids,
              },
        }
    
    employee_transfer_history = fields.One2many( 
        'hr.employee.transfer.line', 
        'employee_id', 
        string='Transfer History'
        )
    
    # @api.onchange('first_name', 'middle_name', 'last_name')
    # def onchange_update_full_name(self):
    #     self.name = " ".join(filter(None, [self.first_name, self.middle_name, self.last_name]))
    #     # self.name = " ".join([name for name in [self.first_name, self.middle_name, self.last_name] if name])

    @api.onchange(
        'first_name','middle_name', 'last_name'
        )
    def onchange_of_applicants_name(self):
        fn, mm, ln = "", "", ""
        if self.first_name:
            fn = self.first_name
        if self.middle_name:
            mm = self.middle_name
        if self.last_name:
            ln = self.last_name
        self.name = f'{fn} {mm} {ln}'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                name = " ".join(filter(None, [vals.get('first_name', ''), vals.get('middle_name', ''), vals.get('last_name', '')]))
                vals['name'] = name
        return super().create(vals_list)
    
    # @api.depends('first_name', 'middle_name', 'last_name')
    # def _compute_full_name(self):
    #     for record in self:
    #         current_fullname = record.name
    #         if record.first_name:
    #             non_empty_names = filter(None, [record.first_name, record.middle_name, record.last_name])
    #             full_name = " ".join(non_empty_names)
    #             record.name = full_name
    #         else:
    #             self.name = current_fullname

    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        employee_ids = []
        if operator not in expression.NEGATIVE_TERM_OPERATORS:
            if operator == 'ilike' and not (name or '').strip():
                domain = []
            else:
                domain = ['|', ('name', '=', name), ('employee_number', '=', name)]
            employee_ids = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        if not employee_ids:
            employee_ids = self._search(expression.AND([['|',('name', operator, name), ('employee_number', operator, name)], args]), limit=limit, access_rights_uid=name_get_uid)
        return employee_ids
    


    
