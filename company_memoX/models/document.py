from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import date
from odoo import http

class Document(models.Model):
    _inherit = 'documents.document'

    memo_category_id = fields.Many2one('memo.category', string="Category") 
    memo_id = fields.Many2one('memo.model', string="Memo") 
    submitted_by = fields.Many2one('hr.employee', string="Submitted By") 
    department_id = fields.Many2one('hr.department', string="Department") 
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
        string="Next reoccurance date")#, compute="get_reoccurance_date")

    interval_period = fields.Integer(
        string="interval period", default=1)

    submission_maximum_range = fields.Integer(
        string="Maximum submission range", default=2)
    submission_minimum_range = fields.Integer(
        string="Minimum submission range", default=2)
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
        ('months', 'Monthly'),
        ('weekly', 'Weekly'),
        ('days', 'Daily'),
        ('years', 'Yearly'),
        ('on_request', 'On Request'),
        ('when_applicable', 'When Applicable')
        # ('minutes', 'Minutes'),
        # ('hours', 'Hours'),
        ],
        string="Period type", default="months")
    applicable_date = fields.Date(string="Applicable Date")

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
    active = fields.Boolean("Active",default=True)
    users_followers = fields.Many2many(
        'hr.employee', 
        'document_folder_hr_employee_rel',
        'document_folder_id',
        'hr_employer_id',
        string='Followers')
    district_ids = fields.Many2many('hr.district', string='Responsible Districts')
    users_responsible = fields.Many2many('hr.employee', string='Responsible Users')
    submission_start_date = fields.Date(compute='compute_submission_start_expiry_date')
    expiry_date = fields.Date(compute='compute_submission_start_expiry_date')
    expiry_mail_sent = fields.Boolean(default=False)

    @api.depends('next_reoccurance_date', 'submission_minimum_range', 'submission_maximum_range')
    def compute_submission_start_expiry_date(self):
        for rec in self:
            if rec.next_reoccurance_date:
                rec.submission_start_date = rec.next_reoccurance_date - relativedelta(days=rec.submission_minimum_range)
                rec.expiry_date = rec.next_reoccurance_date + relativedelta(days=rec.submission_maximum_range)
            else:
                rec.submission_start_date = False
                rec.expiry_date = False

    def get_awaiting_submission(self):
        for t in self:
            memo = self.env['memo.model'].search([
                ('document_folder', '=', t.id), 
                ('state', '=', 'submit')
                ])
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
            elif self.period_type == 'weekly':
                self.next_reoccurance_date = recurrance_date + relativedelta(weeks=interval)
            elif self.period_type == 'years':
                self.next_reoccurance_date = recurrance_date + relativedelta(years=interval)
            elif self.period_type == 'days':
                self.next_reoccurance_date = recurrance_date + relativedelta(days=interval)
        else:
            self.next_reoccurance_date = False

    @api.onchange('period_type')
    def onchange_periodic_type(self):
        self.next_reoccurance_date = False
        self.interval_period = 0
        self.submission_maximum_range = 0
        self.submission_minimum_range = 0

    @api.onchange('interval_period')
    def get_reoccurance_date(self):
        # TODO to be consider
        for rec in self:
            interval = rec.interval_period or 0
            if rec.period_type:
                recurrance_date = fields.Date.today()
                if rec.period_type == 'months':
                    rec.next_reoccurance_date = recurrance_date + relativedelta(months=interval)
                elif rec.period_type == 'weekly':
                    rec.next_reoccurance_date = recurrance_date + relativedelta(weeks=interval)
                elif rec.period_type == 'years':
                    rec.next_reoccurance_date = recurrance_date + relativedelta(years=interval)
                elif rec.period_type == 'days':
                    rec.next_reoccurance_date = recurrance_date + relativedelta(days=interval)
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

    def get_xy_data(self):
        '''Test for document charts
        1. configure document folder with occurrence and min and max range set to 2 . ie two days
        2. Create a new memo of type document request,
        3. Approve the memo, 
        4. Reset the next occurrence and try again
        
        '''
        hr_department = self.env['hr.department'].sudo()
        department_total_progress = []
        departments = []
        # if memo_type_param == "document_request":
        document_folders = self.env['documents.folder'].search([])
        # documents_document = request.env['documents.document'].sudo()# .search([])

        total_document_folders = len(document_folders) # 5
        document_ratio = 100 / total_document_folders # == 20
        # document_ratio = float_round(document_ratio, precision_rounding=2)
        for document in document_folders:
            """Get all the departments in documents folder"""
            departments += [dep.id for dep in document.department_ids]
        for department in list(set(departments)): # set to remove duplicates
            department_submission = 0 
            for doc in document_folders:
                '''get the min date of submission before reoccurence and that after reoccurence date'''
                min_date = doc.next_reoccurance_date + relativedelta(days=-doc.submission_minimum_range)
                maximum_date = doc.next_reoccurance_date + relativedelta(days=doc.submission_maximum_range)
                docu_ids = doc.mapped('document_ids')
                if docu_ids:
                    submitted_documents_document = docu_ids.filtered(
                        lambda su: su.submitted_date >= min_date and su.submitted_date <= maximum_date and su.memo_id.dept_ids.id == hr_department.browse(department).id if su.submitted_date else False
                    ) # check if the submitted document is within the min date and maximum date and count it as +1
                    if submitted_documents_document:
                        department_submission += len(submitted_documents_document)
            dept_document_ratio = int(department_submission * document_ratio) # total to display 4 * 20 == 80
            department_total_progress.append(dept_document_ratio)
        return department_total_progress, [hr_department.browse(dp).name for dp in list(set(departments))]

    def action_view_documents(self):
        view_id = self.env.ref('documents.document_view_kanban').id
        submitted_documents = self.document_ids
        ret = {
                'name': "Documents",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'kanban',
                'res_model': 'documents.document', 
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', submitted_documents.ids)],
                'target': 'current'
                }
        return ret  

    def action_view_success_rate(self):
        pass

    def action_view_avg(self):
        pass

    def action_view_number_of_awaiting(self):
        view_id = self.env.ref('company_memo.tree_memo_model_view2').id
        memo = self.env['memo.model'].search([
            ('document_folder', '=', self.id), 
            ('state', '=', 'submit')])
        ret = {
                'name': "Document requests",
                'view_mode': 'tree',
                'view_id': view_id,
                'view_type': 'kanban',
                'res_model': 'memo.model', 
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [rec.id for rec in memo])],
                'target': 'current'
                }
        return ret  

    def action_view_open_documents(self):
        view_id = self.env.ref('company_memo.tree_memo_model_view2').id
        memo = self.env['memo.model'].search([
            ('document_folder', '=', self.id), 
            ('state', '=', 'Sent')])  
        ret = {
                'name': "Document requests",
                'view_mode': 'tree',
                'view_id': view_id,
                'view_type': 'kanban',
                'res_model': 'memo.model', 
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [rec.id for rec in memo])],
                'target': 'current'
                }
        return ret  

    def action_view_closed_documents(self):
        view_id = self.env.ref('company_memo.tree_memo_model_view2').id
        memo = self.env['memo.model'].search([
            ('document_folder', '=', self.id), 
            ('state', '=', 'Done')])
        ret = {
                'name': "Documents",
                'view_mode': 'tree',
                'view_id': view_id,
                'view_type': 'kanban',
                'res_model': 'memo.model', 
                'type': 'ir.actions.act_window',
                'domain': [('id', 'in', [rec.id for rec in memo])],
                'target': 'current'
                }
        return ret

    def _cron_notify_document(self):
        """
        
        """
        folders = self.env['documents.folder'].search([])
        today_date = fields.Date.today() 
        ready_for_submission = folders.filtered(lambda rec: isinstance(rec.next_reoccurance_date, date) and ((rec.next_reoccurance_date - today_date).days in range(0, rec.submission_minimum_range + 1)))
        for rec in ready_for_submission:
            deps =  rec.department_ids
            if deps:
                for dep in deps:
                   user_responsible = rec.users_responsible.search([('department_id', '=', dep.id)], limit=1)
                   obj = rec
                   template_id = self.env.ref('company_memo.mail_template_document_request_due_notification')
                   user_email = user_responsible.mapped('work_email')
                   email_to = dep.manager_id.work_email if dep.manager_id else user_email
                   email_cc = ','.join(user_email) if dep.manager_id else False
                   if email_to:
                        self._send_mail(obj, template_id, email_to, email_cc) 

    def _cron_get_expiry(self):
        self.send_mail_or_get_expire_defaulting_departments()

    def send_mail_or_get_expire_defaulting_departments(self, reusable=False):
        """
        used to return departments that havent submitted
        """
        folders = self.env['documents.folder'].search([
            ]) # get all the expired submission folders NOT SENT
        depts = []
        for folder in folders:
            if folder.submission_start_date and folder.expiry_date:
                if fields.Date.today() > folder.expiry_date:
                    folder_documents = folder.mapped('department_ids')
                    for dep in folder_documents:
                        sumbitted_departments = folder.mapped('document_ids').filtered(
                            lambda doc: doc.department_id.id == dep.id and doc.submitted_date >= folder.submission_start_date \
                                and doc.submitted_date <= folder.expiry_date
                                )
                        if not sumbitted_departments:
                            if not reusable:
                                # send mail to the followers, informing them that the department has defaulted
                                user_responsible = folder.users_responsible.search([('department_id', '=', dep.id)], limit=1)
                                obj = folder
                                template_id = self.env.ref('company_memo.mail_template_document_request_expiry_notification')
                                user_email = user_responsible.mapped('work_email')
                                email_to = dep.manager_id.work_email if dep.manager_id else user_email
                                followers_email = folder.users_followers.mapped('work_email')
                                email_cc = ','.join(followers_email)
                                if email_to:
                                        self._send_mail(obj, template_id, email_to, email_cc) 
                                depts.append(dep)
        if reusable:
            return depts
        else:
            folder.update_next_occurrence_date()	
        
    def _send_mail(self, model, template_id,email_to, email_cc):
        if template_id and email_to:
            ctx = dict()
            ctx.update({
				'default_model':  model._name,
				'default_res_id': model.id,
				'default_use_template': bool(template_id),
				'default_template_id': template_id.id,
                'default_email_to': email_to,
                'title': 'Cool Title for Document Request'
						})
            template_id.write({
				'email_to': email_to,
                'email_cc': email_cc
				})
            template_id.with_context(ctx).sudo().send_mail(model.id, force_send=False)

    def get_base_url(self):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return base_url