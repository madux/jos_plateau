from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta


class Document(models.Model):
    _inherit = 'documents.document'

    memo_category_id = fields.Many2one('memo.category', string="Category") 
    submitted_date = fields.Date(
        string="submitted date")
    
    

class DocumentFolder(models.Model):
    _inherit = 'documents.folder'
    _description = 'Documents Workspace'
    _parent_name = 'parent_folder_id'
    _parent_store = True
    _order = 'sequence'

    department_ids = fields.Many2many(
        'hr.department', 
        string="Category")
    
    next_reoccurance_date = fields.Date(
        string="Next reoccurance date")# , compute="get_reoccurance_date")
    
    interval_period = fields.Integer(
        string="interval period", default=1)
    
    submission_maximum_range = fields.Integer(
        string="Maximum submission range", default=2)
    number_failed_submission = fields.Integer(
        string="Failed submission", 
        help='''update incrementally if the interval btw the current date and next 
        submission date exceeds the maximum date of submission''')
    number_successful_submission = fields.Integer(
        string="Successful submission", 
        compute="count_submitted_documents",
        help="Helps determine the number of submitted files")
    document_ids = fields.Many2many(
        'documents.document',
        string="Submitted documents")
    
    period_type = fields.Selection([
        ('months', 'Months'),
        ('days', 'Days'),
        ('years', 'Years'),
        # ('minutes', 'Minutes'),
        # ('hours', 'Hours'),
        ],
        string="Period type", default="months")
    
    success_rate = fields.Selection([
        ('100', '100 %'),
        ('70', '70 %'),
        ('40', '40 %'),
        ('10', '10 %'),
        ('0', '0 %'),
        ],
        string="Success rating")
    
    average_submission_rate = fields.Float(
        string="Average submission rate")
    
    number_of_awaiting = fields.Integer(
        string="Awaiting Submission",
          help='Identifies awaiting submission',
          compute="get_awaiting_submission")
    color = fields.Integer("Color Index", default=0)
    opened_documents = fields.Integer("Opened", default=0, compute="get_unapproved_submission")
    closed_documents = fields.Integer("Completed", default=0, compute="get_completed_submission") 
    
    def get_awaiting_submission(self):
        for t in self:
            memo = self.env['memo.model'].search([('document_folder', '=', t.id), ('state', '=', 'submit')])
            if t.name:
                t.number_of_awaiting = len([rec.id for rec in memo]) if memo else 0
            else:
                t.number_of_awaiting = False

    def get_unapproved_submission(self):
        for t in self:
            if t.name:
                memo = self.env['memo.model'].search([('document_folder', '=', t.id), ('state', '=', 'Sent')])
                t.opened_documents = len([rec.id for rec in memo]) if memo else 0
            else:
                t.opened_documents = False

    def get_completed_submission(self):
        for rec in self:
            if rec.name:
                memo = self.env['memo.model'].search([('document_folder', '=', rec.id), ('state', '=', 'Done')])
                rec.closed_documents = len([recw.id for recw in memo]) if memo else 0
            else:
                rec.closed_documents = False
    
    def update_next_occurrence_date(self):
        if self.period_type and self.interval_period:
            interval = self.interval_period
            recurrance_date = self.next_reoccurance_date if self.next_reoccurance_date else fields.Date.today()
            if self.period_type == 'months':
                self.next_reoccurance_date = recurrance_date + relativedelta(months=interval)
            elif self.period_type == 'years':
                self.next_reoccurance_date = recurrance_date + relativedelta(years=interval)
            elif self.period_type == 'days':
                self.next_reoccurance_date = recurrance_date + relativedelta(days=interval)
            # elif self.period_type == 'minutes':
            #     rec.next_reoccurance_date = recurrance_date + relativedelta(minutes=interval)
            # elif rec.period_type == 'hours':
            #     rec.next_reoccurance_date = recurrance_date + relativedelta(hours=interval)
        else:
            self.next_reoccurance_date = False

    @api.onchange('interval_period', 'period_type')
    def get_reoccurance_date(self):
        # TODO to be consider
        for rec in self:
            if rec.period_type and rec.interval_period:
                interval = rec.interval_period
                recurrance_date = rec.next_reoccurance_date if rec.next_reoccurance_date else fields.Date.today()
                if rec.period_type == 'months':
                    rec.next_reoccurance_date = recurrance_date + relativedelta(months=interval)
                elif rec.period_type == 'years':
                    rec.next_reoccurance_date = recurrance_date + relativedelta(years=interval)
                elif rec.period_type == 'days':
                    rec.next_reoccurance_date = recurrance_date + relativedelta(days=interval)
                # elif rec.period_type == 'minutes':
                #     rec.next_reoccurance_date = recurrance_date + relativedelta(minutes=interval)
                # elif rec.period_type == 'hours':
                #     rec.next_reoccurance_date = recurrance_date + relativedelta(hours=interval)
            else:
                rec.next_reoccurance_date = False

    @api.depends('document_ids')
    def count_submitted_documents(self):
        for rec in self:
            if rec.document_ids:
                rec.number_successful_submission = len(rec.document_ids.ids)
            else:
                rec.number_successful_submission = False

    def _cron_check_expiry(self):
        self.check_due_submission()

    def check_success_submission(self):
        pass 

    def check_due_submission(self):
        for rec in self:
            if rec.next_reoccurance_date and (rec.submission_maximum_range > 0):
                if (fields.Date.today() - rec.next_reoccurance_date).days > rec.submission_maximum_range:
                    document_within_range = rec.mapped('document_ids').filtered(
                        lambda s: s.submitted_date >= rec.next_reoccurance_date and s.submitted_date <= fields.Date.today() if s.submitted_date else False
                    )
                    if not document_within_range:
                        rec.number_failed_submission += 1

    def action_view_documents(self):
        # action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_team")
        # action['display_name'] = self.name
        # return action 
        tree_view_ref = self.env.ref('company_memo.tree_memo_model_view2')
        form_view_ref = self.env.ref('company_memo.memo_model_form_view_3')
        domain = [rec.id for rec in self.env['memo.model'].search([('document_folder','=', self.id)])]
        return {
              'name': 'Document memo',
              'view_type': 'tree',
              "view_mode": 'tree',
            #   'view_id': view_id.id,
              'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
              'res_model': 'memo.model',
              'type': 'ir.actions.act_window',
              'target': 'current',
              'domain': [('id', 'in', domain)],
        }

    def action_view_success_rate(self):
        pass

    def action_view_avg(self):
        pass

    def action_view_number_of_awaiting(self):
        pass

    def action_view_open_documents(self):
        pass

    def action_view_closed_documents(self):
        pass
    

