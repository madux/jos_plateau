from odoo import models, fields, api
from odoo import Command
from odoo.exceptions import ValidationError

class MemoConfigDuplicationWizard(models.TransientModel):
    _name = 'memo.config.duplication.wizard'

    name = fields.Char(string="Name")
    dept_ids = fields.Many2many('hr.department', string="Departments")
    dummy_memo_stage_ids = fields.Many2many('dummy.memo.stage', 'duplication_wizard_id')
    employees_follow_up_ids = fields.Many2many('hr.employee',
                                               'hr_employee_wizard_rel',
                                                'approvers_id',
                                                'config_wizard_id',
                                                string='Employees to Follow up')
    allowed_companies_ids = fields.Many2many('res.partner',
                                         'res_partner_wizard_rel'
                                         'allowed_companies_id',
                                         'res_partner_wizard_id', 
                                         string='Allowed Companies')

    @api.model
    def default_get(self, fields):
        res = super(MemoConfigDuplicationWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            memo_config = self.env['memo.config'].browse(active_id)
            dummy_memo_stage_ids = []
            for stage in memo_config.stage_ids:
                dummy_memo_stage = self.env['dummy.memo.stage'].create({
                    'name': stage.name,
                    'sequence': stage.sequence,
                    'active': stage.active,
                    'approver_ids': stage.approver_ids,
                    'is_approved_stage': stage.is_approved_stage,
                    'main_stage_id': stage.id,
                })
                dummy_memo_stage_ids.append(dummy_memo_stage.id)
            res.update({'dummy_memo_stage_ids': [(6, 0, dummy_memo_stage_ids)]})
        return res
      
    def duplicate_memo_config(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            memo_config = self.env['memo.config'].browse(active_id)
            memo_type = self.env['memo.type'].search([('name', '=', self.name)], limit=1)
            if memo_type:
                raise ValidationError('Memo type with name already exist. Kindly change the name')
            else:
                memo_type = self.env['memo.type'].create({
                    'name': self.name,
                    'active': True,
                    'memo_key': memo_config.memo_type.memo_key
            })
            for dept in self.dept_ids:
                stage_ids = []
                new_config = self.env['memo.config'].create({
                'department_id': dept.id,
                'memo_type': memo_type.id,
                'approver_ids': [(6, 0, self.employees_follow_up_ids.ids)],
                'allowed_for_company_ids': self.allowed_companies_ids,
                
                })
                if self.dummy_memo_stage_ids:
                    for sequence, stage in enumerate(self.dummy_memo_stage_ids, 900): 
                        # original_stage_obj = self.env['memo.stage'].browse(stage.main_stage_id)
                        new_stage = self.env['memo.stage'].create({
                            'name': stage.name,
                            'sequence': sequence,
                            'active': True,
                            'loaded_from_data': True,
                            'approver_ids': [(6, 0, stage.approver_ids.ids)],
                            'is_approved_stage': stage.is_approved_stage,
                            'memo_config_id': new_config.id,
                            # new implementation for stage duplication
                            'sub_stage_ids': [(4, stg.copy().id) for stg in stage.main_stage_id.sub_stage_ids],
                            'required_invoice_line': [(4, rinv.copy().id) for rinv in stage.main_stage_id.required_invoice_line],
                            'required_document_line': [(4, rdoc.copy().id) for rdoc in stage.main_stage_id.required_document_line],
                            'no_conditional_stage_id': stage.main_stage_id.no_conditional_stage_id.id,
                            'yes_conditional_stage_id': stage.main_stage_id.yes_conditional_stage_id.id,
                            'memo_has_condition': stage.main_stage_id.memo_has_condition,
                            'no_condition': stage.main_stage_id.no_condition,
                            'yes_condition': stage.main_stage_id.yes_condition,

                        })
                        stage_ids.append(new_stage.id)
                    new_config.update({'stage_ids': stage_ids})
            # return {
            #     'name': 'New Memo Config',
            #     'view_mode': 'form',
            #     'res_id': new_config.id, 
            #     'res_model': 'memo.config',
            #     'view_type': 'form',
            #     'type': 'ir.actions.act_window',
            #     'target': 'current',
            # }


class DummyMemoStage(models.TransientModel):
    _name = 'dummy.memo.stage'

    duplication_wizard_id = fields.Many2one('memo.config.duplication.wizard', string='Duplication Wizard')
    name = fields.Char(string="Stage Name")
    main_stage_id = fields.Many2one('memo.stage',string="Original Stage ID")
    sequence = fields.Integer(string="Sequence")
    active = fields.Boolean(string="Active")
    approver_ids = fields.Many2many('hr.employee', 'employee_wizard_rel', 'employee_id', 'employee_wizard_id', string="Approvers")
    is_approved_stage = fields.Boolean(string="Is Approved Stage")



