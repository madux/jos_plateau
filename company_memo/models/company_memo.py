from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from bs4 import BeautifulSoup
from odoo.tools import consteq, plaintext2html
from odoo import http
import random
from lxml import etree
from bs4 import BeautifulSoup
import io
import base64
import qrcode
import logging
from datetime import date, datetime, timedelta
import json
from dateutil.relativedelta import relativedelta
from num2words import num2words


_logger = logging.getLogger(__name__)

class ngAccountBudget(models.Model):
    _name = "ng.account.budget"
    
class NgAccountBudgetLine(models.Model):
    _name = "ng.account.budget.line"
    _description = "To hold the budget allocation lines"
    

    
class Memo_Model(models.Model):
    _name = "memo.model"
    _description = "Internal Memo"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name"
    _order = "id desc"
    
    @api.model
    def create(self, vals):
        code_seq = self.env["ir.sequence"].next_by_code("memo.model") or "/" if not self.code else self.code
        dept_seq = self.env['ir.sequence'].next_by_code('department-num')
        child_code = False
        po_memo = vals.get('memo_project_type')
        ms_config = self.env['memo.config'].search([
            ('memo_type', '=', vals['memo_type'])
            ], limit=1)
        project_prefix = 'REF'
        dept_suffix = ''
        if ms_config:
            project_prefix = ms_config.prefix_code or 'REF'
            dept_suffix = ms_config.department_code or 'X'
        if vals.get('project_memo_id'):
            project_memo_id = vals.get('project_memo_id', False) # id
            all_child_projects = self.env['memo.model'].sudo().search([
                ('project_memo_id', '=', project_memo_id),
                ('code', 'not in', [False,"", None]),
                ])
            parent_project = self.env['memo.model'].sudo().browse([project_memo_id])
            # raise ValidationError(f"what is split code =={all_child_projects}")
            split_code = ['00']
            if all_child_projects:
                last_child_project_code = all_child_projects[-1].code # get the last memos' code
                if last_child_project_code:
                    split_code = last_child_project_code.split('-') # get last number and add 1 to increment [PO-00045-X-100]
                    # i.e [PO-00045-X-100] ==> [PO-00045, X, 100]
                    # raise ValidationError(f"what is split code =={split_code} and parent project {project_memo_id}")
                    child_code = int(split_code[-1]) + 1
                # else:
                #     raise ValidationError(f"Parent File code Not found: Please manually locate the file associated with the parent code and modify the last code manually e.g modify the last [PO-00045-X-100]")
            else:
                split_code = parent_project.code.split('-') # [PO-00045-X-100]
                child_code = int(split_code[-1]) + 1
                # raise ValidationError(f"what is split code 2 =={split_code} and parent project {project_memo_id}")
            vals['code'] = f"{split_code[0]}-0{child_code}" if po_memo not in ['project_pro'] else ""
        else:
            vals['code'] = f"{project_prefix}{code_seq}-0{0}" if po_memo not in ['project_pro'] else "" # e.g [PO-00045-X-100]
        result = super(Memo_Model, self).create(vals)
        if self.attachment_ids:
            self.attachment_ids.write({'res_model': self._name, 'res_id': self.id})
        return result

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].sudo().read_group([
            ('res_model', '=', 'memo.model'), 
            ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for rec in self:
            rec.attachment_number = attachment.get(rec.id, 0)

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.actions']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'memo.model'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'memo.model', 'default_res_id': self.id}
        return res
    
    # default to current employee using the system 
    def _default_employee(self):
        return self.env.context.get('default_employee_id') or \
        self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    def _default_user(self):
        return self.env.context.get('default_user_id') or \
         self.env['res.users'].search([('id', '=', self.env.uid)], limit=1)
     
    # def get_publish_memo_types(self):
    #     user_branches = list(self.env.user.branch_id.id)
    #     memo_configs = self.env['memo.config'].search([
    #         ('active', '=', True),
    #         ('branch_ids', 'in', user_branches)
    #         ])
    #     memo_type_ids = [r.memo_type.id for r in memo_configs]
    #     return [('id', 'in', memo_type_ids)]
    
    @api.model
    def default_get(self, fields):
        res = super(Memo_Model, self).default_get(fields)
        memo_project_type = self.env.context.get('default_memo_project_type')
        default_budget_allocation = self.env.context.get('default_is_budget_allocation_request')
        external_payment_request = self.env.context.get('default_external_memo_request')
        
        ministry_of_finance = self.env.ref('plateau_addons.mda_ministry_of_finance')
        # finance_budget_head = self.env['ng.budget'].search(domain)
        # user_branches = list(self.env.user.branch_id.id)
        domain = [('active', '=', True)]
        # if memo_project_type: , ('branch_ids', 'in', user_branches)
        #     domain = [('active', '=', True), ('project_type', '=', memo_project_type)]
        memo_configs = self.env['memo.config'].search(domain)
        user_branch_id = self.env.user.branch_id
        res.update({
            'dummy_memo_types': [(6, 0, [rec.memo_type.id for rec in memo_configs if user_branch_id.id in rec.branch_ids.ids])],
            'dummy_budget_ids': [(6, 0, [rec.id for rec in self.env['ng.account.budget'].search([
                '|', ('branch_id', '=', self.env.user.branch_id.id),
                ('branch_id', 'in', self.env.user.branch_ids.ids)])
                                         ])],
            'request_mda_from': ministry_of_finance.id if default_budget_allocation or external_payment_request else False,
            })
        return res
        
    memo_type = fields.Many2one(
        'memo.type',
        string='Memo type',
        required=True,
        copy=True,
        # domain=lambda self: self.get_publish_memo_types(),
        ) 
    alert_option= fields.Selection(
        [
        ("normal", "Normal"), 
        ("warning", "Warning"), 
        ("danger", "Danger"),
        ], string="Alert Option", 
        compute="compute_deadline",
        help="""
        Used to determine the text to display 
        when task is coming to end date"""
    )
    
    dummy_memo_types = fields.Many2many(
        'memo.type',
        'memo_model_type_rel',
        'memo_type_id', 
        'memo_id',
        string='Dummy Memo type',
        )
    dummy_budget_ids = fields.Many2many(
        'ng.account.budget',
        'ng_account_budget_rel',
        'ng_account_budget_id', 
        'budget_id',
        string='Dummy budget',
        )
    memo_type_key = fields.Char('Memo type key', readonly=True)
    name = fields.Char('Subject', size=400)
    code = fields.Char('Code', readonly=True, store=True)
    employee_id = fields.Many2one('hr.employee', string = 'Employee', default =_default_employee) 
    direct_employee_id = fields.Many2one('hr.employee', string = 'Employee') 
    set_staff = fields.Many2one('hr.employee', string = 'Employee')
    demo_staff = fields.Integer(string='User',
                                default=lambda self: self.env['res.users'].search([
                                    ('id', '=', self.env.uid)], limit=1).id, compute="get_user_staff",)
        
    user_ids = fields.Many2one('res.users', string = 'Beneficiary', default =_default_user)
    dept_ids = fields.Many2one('hr.department', string ='Department', readonly = True, store =True, compute="employee_department",)
    description = fields.Char('Note')
    project_id = fields.Many2one('account.analytic.account', 'Project')
    project_memo_id = fields.Many2one('memo.model', 'Parent Project')
    vendor_id = fields.Many2one('res.partner', 'Vendor')
    amountfig = fields.Float('Budget Amount', store=True, default=1.0)
    description_two = fields.Text('Reasons')
    phone = fields.Char('Phone', store=True)
    work_instruction_description = fields.Char('WK instruction')
    email = fields.Char('Email', related='employee_id.work_email')
    reason_back = fields.Char('Return Reason')
    file_upload = fields.Binary('File Upload')
    total_so_amount = fields.Float('Invoice Amount', compute="compute_total_confirmed_so_amount")
    file_namex = fields.Char("FileName")
    stage_id = fields.Many2one(
        'memo.stage', 
        string='Stage', 
        store=True,
        domain=lambda self: self._get_related_stage(),
        )
            
    po_memo_ids = fields.One2many(
        'memo.model',
        'project_memo_id',
        string='Additional PO process')
    state = fields.Selection([('submit', 'Draft'),
                                ('Sent', 'Sent'),
                                ('Approve', 'Waiting For Payment / Confirmation'),
                                ('Approve2', 'Memo Approved'),
                                ('Done', 'Completed'),
                                ('Refuse', 'Refused'),
                              ], string='Status', index=True, readonly=True,
                             copy=False, default='submit',
                             required=True,
                             store=True,
                             help='Request Report state')
    date = fields.Datetime('Request Date', default=fields.Datetime.now())
    client_id = fields.Many2one('res.partner', 'Client')
    contractor_id = fields.Many2one('res.partner', 'Contractor', help="Always available if the request is for contract payment")
    client_address = fields.Char('Client Address', related="client_id.street", store=True)
    client_address2 = fields.Char('Address 2', related="client_id.street2", store=True)
    client_phone = fields.Char('Client Phone', related="client_id.phone", store=True)
    client_email = fields.Char('Client Email', related="client_id.email", store=True)
    client_country_id = fields.Char('Client Country', related="client_id.country_id.name", store=True)

    task_todo = fields.Integer('Task todo')#, compute="_compute_task_info", store=True)
    task_active = fields.Integer('Task active')#, compute="_compute_task_info", store=True)
    task_done = fields.Integer('Task done')#, compute="_compute_task_info", store=True)
    task_todo_percentage = fields.Integer('Task todo (%)', compute="compute_task_percentage", store=True)
    task_active_percentage = fields.Integer('Task active (%)', compute="compute_task_percentage", store=True)
    task_done_percentage = fields.Integer('Task done (%)', compute="compute_task_percentage", store=True)
    
    
    todo_document = fields.Integer('Documents todo')#, compute="compute_document_info", store=True)
    active_document = fields.Integer('Active Document')#, compute="compute_document_info", store=True)
    done_document = fields.Integer('Document Done')#, compute="compute_document_info", store=True)
    
    paid_expense = fields.Float('Paid expense')
    expected_revenue = fields.Float('Expected revenue')
    realized_income = fields.Float('Realized Income')

    # Reporting 
    amount_to_pay = fields.Float('Amount to pay')
    total_revenue = fields.Float('Revenue')
    total_budget = fields.Float('Budgets')
    amount_paid = fields.Float('Paid Invoices')
    amount_unpaid = fields.Float('Expected payment')
    total_so_balance = fields.Float('Balance', compute="compute_balance")
    total_so_expected_balance = fields.Float('Expected balance')
    total_income = fields.Float('Income', compute="compute_income")
    total_unpaid_po_expenses = fields.Float('Unpaid expenses')
    total_unpaid_so_incomes = fields.Float('Unpaid income')
    total_paid_po_expenses = fields.Float('Paid expenses', store=True, help="total sum of po confirmed")#, compute="depend_po_ids", )

    # Reporting 
    
    invoice_id = fields.Many2one(
        'account.move', 
        string='Invoice', 
        store=True,
        domain="[('move_type', '=', 'in_invoice'), ('state', '!=', 'cancel')]"
        )
    move_id = fields.Many2one(
        'account.move', 
        string='Move', 
        store=True,
        readonly=True
        )
    to_create_document = fields.Boolean(
        'Registered in Document Management',
        default=False,
        help="Used to create in Document Management")
    external_memo_request = fields.Boolean(string='External request', related="memo_type.is_external")
    # TRANSPORT
    truck_company_name = fields.Many2one('res.partner', string='Truck company Name')
    truck_reg = fields.Char(string='Truck registration No.')
    truck_type = fields.Char(string='Truck Type')
    truck_driver = fields.Many2one('res.partner', string='Driver details')
    truck_driver_phone = fields.Char(string='Driver Phone')
    waybill_ids = fields.One2many(
        'memo.transport.waybill', 
        'memo_id',
        string='Waybill details'
        ) 
            
    waybill_from = fields.Char(string='Pickup Location?')
    waybill_to = fields.Char(string='Drop Off Location')
    waybill_date = fields.Datetime(string='Date of Transportation')
    waybill_expected_arrival_date = fields.Datetime(string='Expected Arrival')
    waybill_note = fields.Char(string='Waybill Note')
    #### DURATIONS
    enabled_date_validity = fields.Date("Date Validity", default=False)
    enabled_date_procured = fields.Date("Date Procured", default=False)
    enable_procurment_amount = fields.Float("Procure Amount", default=False)
    enabled_date_paid = fields.Date("Date paid", default=False)
    validity_set = fields.Boolean("Validity Set", default=False)
    task_start_date = fields.Date(
        "Task start Date",
        default=fields.Date.today()
        )
    waybill_items = fields.Integer(string='No of items', compute="compute_waybill_item")
    
    @api.depends('waybill_ids')
    def compute_waybill_item(self):
        for rec in self:
            if rec.waybill_ids:
                items = len(rec.waybill_ids.ids)
                rec.waybill_items = items
            else:
                rec.waybill_items = 0
                
    task_end_date = fields.Date(
        "Task End Date",
        # compute="compute_task_end_date",
        store=True
        ) 
    remaining_task_duration = fields.Integer(
        "Remaining task duration",
        compute="compute_remaining_task_duration",
        help="the duration in days btw stage moved date and current date"
        )
    
    
    percentage_of_remaining_task = fields.Integer(
        "Expiry days in percentage",
        compute="compute_remaining_task_duration",
        help="the duration in percentage btw stage moved date and current date"
        )
    
    stage_duration = fields.Integer(
        "Task duration",
        compute="compute_stage_duration",
        )
                
    # percentage_of_total_task_todo = fields.Integer(
    #     "Percentage of task todo",
    #     )
    # percentage_of_total_task_active = fields.Integer(
    #     "Percentage of task todo",
    #     )
    
    # @api.depends('task_start_date')
    # def compute_task_end_date(self):
        # pass 
        # for rec in self:
        #     if rec.stage_id and rec.task_start_date:
        #         stage_duration = rec.stage_id.duration_config # default 20
        #         rec.task_end_date = rec.task_start_date + timedelta(days=stage_duration) 
        #     else:
        #         rec.task_end_date = False
         
                
    # Work instruction
    work_instruction_ids = fields.One2many(
        'memo.work.instruction',
        'memo_id',
        string='Work Instruction items',
        )

    soe_advance_reference = fields.Many2one('memo.model', 'SOE ref.')
    cash_advance_reference = fields.Many2one(
        'memo.model', 
        'Cash Advance ref.')
    date_deadline = fields.Date('Deadline date')
    status_progress = fields.Float(string="Progress(%)", compute='_progress_state')
    users_followers = fields.Many2many('hr.employee', string='Add followers') #, default=_default_employee)
    res_users = fields.Many2many('res.users', string='Approvers') #, default=_default_employee)
    comments = fields.Text('Comments', default="-")
    supervisor_comment = fields.Html('Supervisor Comments', default="")
    manager_comment = fields.Html('Manager Comments', default="")
    is_supervior = fields.Boolean(string='is supervisor', compute="compute_employee_supervisor")
    is_manager = fields.Boolean(string="is_manager", compute="compute_employee_supervisor")
    
    # Fields for server request
    applicationChange = fields.Boolean(string="Application Change")
    datapatch = fields.Boolean(string="Data patch")
    enhancement = fields.Boolean(string="Enhancement")
    databaseChange = fields.Boolean(string="Database Change")
    osChange = fields.Boolean(string="OS Change")
    ids_on_os_and_db = fields.Boolean(string="IDS on OS and DB")
    versionUpgrade = fields.Boolean(string="version Upgrade")
    hardwareOption = fields.Boolean(string="hardware Option")
    otherChangeOption = fields.Boolean(string="Other Change")
    other_system_details = fields.Html(string="Specify Other reason")
    justification_reason = fields.Html(string="Justification Reason")
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='No. Attachments')
    approver_id = fields.Many2one('hr.employee', 'Approver')
    approver_ids = fields.Many2many(
        'hr.employee',
        'memo_model_employee_rel',
        'memo_id',
        'hr_employee_id',
        string='Approvers'
        )
    user_is_approver = fields.Boolean(string="User is approver", compute="compute_user_is_approver")
    is_request_completed = fields.Boolean(
        string="is request completed", 
        default=False,
        help="Used to determine if the request business flow is completed. Hides all action buttons if checked")
    is_supervisor_commented = fields.Boolean(
        string="Supervisor commented?", 
        help="Used to determine if supervisor has commented"
        )
    is_manager_approved = fields.Boolean(
        string="Manager Approved?", 
        help="Used to determine if manager has approved from the website portal"
        )
    # Loan fields
    loan_type = fields.Selection(
        [
            # ("fixed-annuity", "Fixed Annuity"),
            # ("fixed-annuity-begin", "Fixed Annuity Begin"),
            ("fixed-principal", "Fixed Principal"),
            ("interest", "Only interest"),
        ],
        required=False,
        help="Method of computation of the period annuity",
        readonly=True,
    )
    loan_amount = fields.Monetary(
        currency_field="currency_id",
        required=False,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency", 
        default= lambda self: self.env.user.company_id.currency_id.id, 
        readonly=True,
    )
    periods = fields.Integer(
        required=False,
        readonly=True,
        help="Number of periods that the loan will last",
        default=12,
    )
    method_period = fields.Integer(
        string="Period Length (years)",
        default=1,
        help="State here the time between 2 depreciations, in months",
        required=False,
        readonly=True,
    )
    start_date = fields.Date(
        help="Start of the moves",
        readonly=True,
        copy=False,
    )
    loan_reference = fields.Integer(string="Loan Ref")
    active = fields.Boolean('Active', default=True)

    product_ids = fields.One2many('request.line', 'memo_id', string ='Products') 
    leave_start_date = fields.Datetime('Leave Start Date',  default=fields.Date.today())
    leave_end_date = fields.Datetime('Leave End Date', default=fields.Date.today())

    request_date = fields.Datetime('Request Start Date')
    request_end_date = fields.Datetime('Request End Date')

    leave_type_id = fields.Many2one('hr.leave.type', string="Leave type")
    memo_setting_id = fields.Many2one(
        'memo.config', 
        string="Memo config id",
        # related="stage_id.memo_config_id"
        )
    
    ###############3 RECRUITMENT ##### 
    job_id = fields.Many2one('hr.job', string='Requested Position',
                             help='The Job Position you expected to get more hired.',
                             )
    
    job_tmp = fields.Char(string="Job Title",
                          size=256,
                          readonly=True)
    
    established_position = fields.Selection([('yes', 'Yes'),
                                ('no', 'No'),
                              ], string='Established Position', index=True,
                             copy=False,
                             readonly=True,
                             store=True)
    recruitment_mode = fields.Selection([('Internal', 'Internal'),
                                ('External', 'External'),
                                ('Outsourced', 'Outsourced'),
                              ], string='Recruitment Mode', index=True,
                             copy=False,
                             readonly=True,
                             store=True)
    requested_department_id = fields.Many2one(
        'hr.department', 
        string ='Requested Department for Recruitment'
        ) 
    qualification = fields.Char('Qualification')
    age_required = fields.Char('Required Age')
    years_of_experience = fields.Char('Years of Experience')
    expected_employees = fields.Integer('Expected Employees', default=1,
                                        help='Number of extra new employees to be expected via the recruitment request.',
                                        required=False,
                                        index=True,
                                        )
    recommended_by = fields.Many2one('hr.employee', string='Recommended by')
    date_expected = fields.Date('Expected Date', index=True)

    closing_date = fields.Date('Closing Date')
    
    invoice_ids = fields.Many2many(
        'account.move', 
        'memo_invoice_rel',
        'memo_invoice_id',
        'invoice_memo_id',
        string='Invoice', 
        store=True,
        domain="[('state', '!=', 'cancel')]"
        )
    
    # MEMO THINGS 
    attachment_ids = fields.Many2many(
        'ir.attachment', 
        'memo_ir_attachment_rel',
        'memo_ir_attachment_id',
        'ir_attachment_memo_id',
        string='Attachment', 
        store=True,
        domain="[('res_model', '=', 'memo.model')]"
        )
    
    memo_sub_stage_ids = fields.Many2many(
        'memo.sub.stage', 
        'memo_sub_stage_rel',
        'memo_sub_stage_id',
        'memo_id',
        string='Sub Stages', 
        store=True,
        )
    stage_to_skip = fields.Many2one(
        'memo.stage', 
        string='Stage to skip', 
        store=True,
        help="Used to determine stage not to be included in this memo"
        )
    
    final_stage_id = fields.Char('final stage', compute="get_final_stage")
    first_stage = fields.Char('first stage', compute="get_first_stage")
    memo_project_type = fields.Char(string="Project type", help="For logistic companies")
    work_order_code = fields.Char(
        string="Work Order Code", 
        store=True,
        help="Used to store work order number"
        )
    frame_agreement_ids = fields.Many2many(
        'memo.frame.agreement', 
        'memo_frame_agreement_rel',
        'memo_id',
        'memo_frame_id',
        string="Frame Agreement"
        )

    dashboard_memo_ids = fields.Many2many(
        'memo.model', 
        'memo_model_dashboard_rel',
        'memo_model_dashboard_id',
        'memo_id',
        string='Memo Model dashboard', 
        store=True,
        )

    has_sub_stage = fields.Boolean(
        'Has Sub stage', 
        default=False, 
        store=True,
        )
     
    internal_memo_option = fields.Selection(
        [
        ("none", ""), 
        ("all", "All"), 
        ("selected", "Selected"),
        ], string="All / Selected")
    memo_category_id = fields.Many2one('memo.category', string="Category") 
    document_folder = fields.Many2one('documents.folder', string="Document folder")
    
    partner_ids = fields.Many2many(
        'res.partner', 
        'memo_res_partner_rel',
        'memo_res_partner_id',
        'memo_partner_id',
        string='Reciepients', 
        )
    is_contract_memo_request = fields.Boolean(string='Is Contract request', related="memo_type.is_contractor")
    external_memo_request = fields.Boolean(string='External request', related="memo_type.is_external")
    is_internal_transfer = fields.Boolean("Is internal payment ? ", 
                                          related="memo_type.is_internal",
                                          help="""
                                      This help to show if the payment is an internal payment 
                                      request or transfer to journals"""
                                      )
    payment_ids = fields.Many2many(
        "account.payment",
        string="Payment"
        )
    expiry_mail_sent = fields.Boolean(default=False, copy=False)

    # for logistic processes which includes 
    # ['import_process', 'export_process', 'agency_process']
    assigned_to = fields.Many2one('hr.employee', string="Assigned To", copy=False)
    date_assigned = fields.Date(string="Date Assigned", copy=False)
    logistic_item_ids = fields.One2many(
        'logistic.items',
        'memo_id',
        string="Packing list", copy=False)
    
    computed_stage_ids = fields.Many2many('memo.stage', compute='_compute_stage_ids', store=True)
    po_ids = fields.Many2many('purchase.order', 
                              store=True)
    so_ids = fields.Many2many('sale.order', 
                              store=True)
    freeze_po_budget = fields.Boolean(
        "Freeze budget", 
        help="If checked,  users wont be able to add PO", 
        default=False
        )
    to_unfreezed_budget = fields.Boolean(
        "Allow to unfreezed budget", 
        help="If checked, system triggers validation of adding reasons for requesting for the budget unfreeze", 
        default=False
        )
    unfreezed_budget_reason = fields.Text(
        "Reason to unfreezed budget", 
        default=False
        )

    qr_code_commonpass = fields.Binary(string="QR Code")
    
    ##** dashboard computed fields **##
    total_cost = fields.Float('Total PO Cost', compute="compute_dashboard_total")
    total_revenued = fields.Float('Total Revenue', store=True, compute="compute_dashboard_total")
    
    total_so_to_be_invoiced = fields.Float('Total SO to be Invoiced', compute="compute_dashboard_total")
    total_po_to_be_invoiced = fields.Float('Total PO to be Invoiced', compute="compute_dashboard_total")
    
    total_paid_cost = fields.Float('Total PO Paid', compute="compute_dashboard_total")
    total_paid_revenue = fields.Float('Total Paid',store=True, compute="compute_dashboard_total", help="total of All paid SO")
    
    total_closed_paid_cost = fields.Float('Total PO Paid', compute="compute_dashboard_total")
    total_closed_paid_revenue = fields.Float('Total SO Paid',store=True, compute="compute_dashboard_total", help="total of All paid SO")
    
    total_budgeted = fields.Float('Total Budgeted', compute="compute_dashboard_total")
    total_realized_percentage = fields.Float(
        'Realized / Revenue', 
        store=True,
        compute="compute_dashboard_total",
        help="total of paid SO * 100 / All Confirmed SO")
    
    total_revenue_percentage = fields.Float(
        'Revenue / Cost', 
        store=True,
        compute="compute_dashboard_total",
        help="Percentage of confirmed SO against cost budget")
    
    cost_revenue_margin = fields.Float(
        'Revenue / Cost Margin', 
        store=True,
        compute="compute_revenue_margin")
    
    displayed_cost_revenue_margin = fields.Char(
        '', 
        store=True,
        compute="compute_revenue_margin")
    
    second_quad_percentage = fields.Float(
        '', 
        store=True,
        compute="compute_dashboard_total",)
    displayed_second_quad_percentage = fields.Char(
        '', 
        store=True,
        compute="compute_dashboard_total")
 
    third_quad_percentage = fields.Float(
        '', 
        store=True,
        compute="compute_dashboard_total",)
    displayed_third_quad_percentage = fields.Char(
        '', 
        store=True,
        compute="compute_dashboard_total")
    
    fourth_quad_percentage = fields.Float(
        '', 
        store=True,
        compute="compute_dashboard_total",)
    displayed_fourth_quad_percentage = fields.Char(
        '', 
        store=True,
        compute="compute_dashboard_total")
    
    frame_agreement_budget = fields.Float(
        'Frame Agreement', 
        store=True,
        compute="compute_dashboard_total")
    
    frame_agreement_budget_percentage = fields.Float(
        'Budget balance', 
        store=True,
        compute="compute_dashboard_total")
    
    default_percentage_target = fields.Float(
        'Default Percentage', 
        store=True,
        default=100)
    
    is_cash_advance_retired = fields.Boolean(
        string="Is cash Advanced Retired", 
        help="Used to determine if user has fully retired his cash advance"
        ) 
    
    ## stock  fields ##
    stock_picking_id = fields.Many2one(
        "stock.picking",
        string="Stock picking"
        )
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Operation type"
        )

    def get_memo_po_orders(self):
        if self:
            pos = self.env['purchase.order'].search([('memo_id', '=', self.id)])
            return [('id', '=', 0)] if not pos else [('id', 'in', pos.ids)]
        
    @api.depends('stage_id')
    def compute_stage_duration(self):
        for rec in self:
            if rec.stage_id:
                stage_duration = rec.stage_id.duration_config # default 20
                rec.stage_duration = stage_duration
            else:
                rec.stage_duration = 0
                
    @api.depends('so_ids.amount_total')
    def compute_total_confirmed_so_amount(self):
        for rec in self:
            total = 0.0
            if rec.so_ids:
                total += sum([so.amount_total for so in rec.mapped('so_ids').filtered(lambda s: s.state not in ['draft', 'cancel'])])
            rec.total_so_amount = total 
                   
    @api.depends('task_end_date')
    def compute_remaining_task_duration(self):
        for rec in self:
            if rec.task_end_date:
                diff = rec.task_end_date - fields.Date.today() # e.g 10
                days_difference = diff.days
                rec.remaining_task_duration = diff.days
                stage_duration = rec.stage_id.duration_config # default 20
                rec.percentage_of_remaining_task = diff.days * 100 / stage_duration
                # computing for alert option
                if days_difference <= 0: # two days to the deadline
                    rec.alert_option = 'danger'
                elif days_difference in range(1, 5):
                    rec.alert_option = 'warning'
                elif days_difference >= 5:
                    rec.alert_option = 'normal'
            else:
                rec.remaining_task_duration = 0
                rec.percentage_of_remaining_task = 0
                rec.alert_option = ""
    
    @api.depends('task_todo', 'task_active', 'task_done')
    def compute_task_percentage(self):
        for rec in self:
            todo, active, done = rec.task_todo, rec.task_active, rec.task_done
            total_sum_task = todo + active + done
            if rec.task_todo or rec.task_active or rec.task_done:
            # if rec.name:
                rec.task_todo_percentage = todo * 100  / total_sum_task
                rec.task_active_percentage = active * 100  / total_sum_task
                rec.task_done_percentage = done * 100  / total_sum_task
            else:
                rec.task_todo_percentage = 0 
                rec.task_active_percentage = 0 
                rec.task_done_percentage = 0
                
    def print_way_bill(self): 
        return self.env.ref('company_memo.print_waybill_report').report_action(self)

    def print_po(self):
        if not self.po_ids:
            raise ValidationError("Sorry !!! There is no PO to print")
        self._compute_amount_in_words()
        return self.env.ref('company_memo.print_po_bill_report').report_action(self)
    
    amount_in_words = fields.Char(compute="_compute_amount_in_words")

    def _compute_amount_in_words(self):
        for record in self:
            payment_amount = sum([r.amount_total for r in self.payment_ids])
            total = payment_amount if payment_amount > 0 else self.amountfig
            amount_in_words = num2words(total, lang='en')
            record.amount_in_words = amount_in_words.upper() if amount_in_words and total > 0 else ""
    
    def print_payment_voucher(self):
        if not self.payment_ids:
            raise ValidationError("Sorry !!! There is no payment to print")
        return self.env.ref('company_memo.print_payment_voucher_memo_model_report').report_action(self)
    
    
    def send_client_mail_gate_pass(self):
        pass
    
    # @api.onchange('cash_advance_reference')
    # def cash_advance_reference(self):
    #     raise ValidationError('dere')
    #     if self.cash_advance_reference:
    #         raise ValidationError('dere')
    #         # if not self.employee_id:
    #         for rec in self.cash_advance_reference.mapped('product_ids').filtered(lambda s: s.retired == False):
    #             self.product_ids = [(0, 0, {
    #                 'memo_id': rec.id,
    #                 'product_id': rec.product_id.id,
    #                 'description': rec.description,
    #                 'amount_total': rec.amount_total,
    #             })]
    
    def action_add_extra_po(self):
        view = self.env.ref('company_memo.memo_model_new_simple_form_view')
        return {
                'name':'Request PO Confirmation',
                'type':'ir.actions.act_window',
                'view_type':'form',
                'res_model':'memo.model',
                'views':[(view.id, 'form')],
                'view_id':view.id,
                'target':'current',
                'context': {
                    'default_project_memo_id': self.id,
                    'default_memo_type': self.env.ref('company_memo.memo_config_po_extra_approval').id,
                    'default_client_id': self.client_id.id,
                    'default_employee_id': self.employee_id.id,
                    'default_name': f"PO Confirmation - For Project {self.code}",
                    # 'default_to_unfreezed_budget': True,
                    'default_memo_project_type': 'project_pro',
                    # 'default_to_memo_project_type': 'procurement',
                },
                }

    @api.depends("memo_setting_id")
    def get_first_stage(self):
        for record in self:
            if record.memo_setting_id and record.memo_setting_id.stage_ids:
                first_stage = record.memo_setting_id.stage_ids[0]
                record.first_stage = first_stage.name
            else:
                record.first_stage = False

    @api.depends("memo_setting_id")
    def get_final_stage(self):
        for record in self:
            if record.memo_setting_id and record.memo_setting_id.stage_ids:
                record.final_stage_id = record.memo_setting_id.stage_ids[-1].name
            else:
                record.final_stage_id = False
                
    def create_qr_code(self, code):
        qr = qrcode.QRCode()
        qr.add_data(code)
        return qr.make_image(fill_color="black", back_color="white")
    
    def qr_code(self):
        img = self.create_qr_code(self.code)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        self.write({
            'qr_code_commonpass': img_str,
        })

    @api.depends('attachment_ids')
    def compute_document_info(self):
        for rec in self:
            todo = 0
            active = 0
            done = 0
            if rec.attachment_ids:
                attachment_ids = rec.mapped('attachment_ids')
                for doc in attachment_ids:
                    active += 1
                    if doc and not doc.datas:
                        todo += 1
                    if doc.is_locked:
                        done += 1
                rec.todo_document = todo
                rec.active_document = active
                rec.done_document = done
            else:
                rec.todo_document = 0
                rec.active_document = 0
                rec.done_document = 0
            
    @api.depends('stage_id.memo_config_id')
    def _compute_stage_ids(self):
        for record in self:
            if record.stage_id.memo_config_id:
                record.computed_stage_ids = record.stage_id.memo_config_id.mapped('stage_ids').filtered(
                    lambda publish: publish.publish_on_dashboard
                )
            else:
                record.computed_stage_ids = False 
    
    def import_logistic_item(self):
        view = self.env.ref('company_memo.import_logistic_wizard_view')
        return {
                'name':'Cargo document!',
                'type':'ir.actions.act_window',
                'view_type':'form',
                'res_model':'import.logistic_wizard',
                'views':[(view.id, 'form')],
                'view_id':view.id,
                'target':'new',
                'context': {
                    'default_memo_id': self.id,
                    'default_partner_recieved_from': self.client_id.id,
                },
                }

    # @api.onchange('invoice_ids')
    # def onchange_realized(self):
    #     self.update_dashboard_finances()

    # @api.onchange('po_ids')
    # def onchange_po_ids(self):
    #     self.update_dashboard_finances() 

    # @api.onchange('so_ids')
    # def onchange_so_ids(self):
    #     self.update_dashboard_finances()

    @api.depends('total_revenue', 'total_budget')
    def compute_balance(self):
        for s in self:
            result = s.total_budget - s.total_revenue
            s.total_so_balance = result

    @api.depends('total_revenue', 'total_budget')
    def compute_income(self):
        for s in self:
            result = s.total_revenue - s.total_budget
            s.total_income = result

    def update_dashboard_finances(self): 
        invoice_expenses = 0
        invoice_income_paid = 0
        po_balance, so_balance = 0, 0
        budgets, so_amount_total = 0, 0

        for rec in self.po_ids:
            for inv in rec.invoice_ids:
                invoice_expenses += inv.amount_total_signed
                po_balance += inv.amount_residual
            budgets += rec.amount_total
        for rec in self.so_ids:
            for inv in rec.invoice_ids:
                invoice_income_paid += inv.amount_total_signed #
                so_balance += inv.amount_residual #
            so_amount_total += rec.amount_total
        # BUdget
        self.total_budget = budgets
        # Expenses
        self.total_paid_po_expenses = invoice_expenses
        self.amount_to_pay = budgets
        # Revenue
        self.total_revenue = so_amount_total
        # Due Invoice
        self.amount_unpaid = abs(so_balance) # so_amount_total - invoice_income_paid

        # Balance
        self.total_so_balance = budgets - abs(invoice_income_paid)
        self.amountfig = sum([amt.amount_total for amt in self.invoice_ids])
    
    @api.depends('total_cost', 'total_revenue')
    def compute_revenue_margin(self):
        for rec in self:
            total = float(rec.total_revenue - rec.total_cost)
            rec.cost_revenue_margin = round(float(total), 2)
            # rec.displayed_cost_revenue_margin = '₦' + str("{0:,}".format(total)) if total > 0 else '₦ 0.00'
            rec.displayed_cost_revenue_margin = '₦' + str("{0:,}".format(float(str(total).split('.')[0]))) if total > 0 else '₦ 0.00'
     
    @api.depends('name')
    def compute_dashboard_total(self):
        for rec in self:
            closed_stage = rec.memo_setting_id.stage_ids[-1].id if rec.memo_setting_id.stage_ids else 0
            # total_budgeted, total_revenue, total_paid_revenue = 0,0,0
            
            if rec.name: 
                frame_agreement_budget = 0
                # cost = rec.compute_po_naira_dollar_value(rec.so_ids)
                budget, revenue, paid_revenue, total_so_to_be_invoiced = rec.compute_so_naira_dollar_value(rec.so_ids)
                _logger.info(f"here is the computed value: {budget} {revenue} {paid_revenue}")
                frame_agreement_budget = sum([r.agreed_budget for r in rec.frame_agreement_ids])
                sum_po_ids = rec.compute_po_naira_dollar_value(rec.po_ids)
                total_cost = sum_po_ids[0]
                _logger.info(f"here is the computed value: {total_cost} {budget} {revenue} {paid_revenue}")
                
                rec.total_cost = total_cost
                total_so_to_be_invoiced = total_so_to_be_invoiced if rec.stage_id.id != closed_stage else 0 
                total_po_to_be_invoiced = sum_po_ids[3] if rec.stage_id.id != closed_stage else 0
                
                rec.total_so_to_be_invoiced = total_so_to_be_invoiced
                rec.total_po_to_be_invoiced = total_po_to_be_invoiced
                
                total_paid_cost = sum_po_ids[2]
                total_paid_revenue = paid_revenue
                
                rec.total_paid_cost = total_paid_cost
                rec.total_paid_revenue = total_paid_revenue
                
                total_closed_paid_revenue = paid_revenue if rec.stage_id.id == closed_stage else 0.00
                total_closed_paid_cost = sum_po_ids[2] if rec.stage_id.id == closed_stage else 0.00
                rec.total_closed_paid_revenue =total_closed_paid_revenue
                rec.total_closed_paid_cost = total_closed_paid_cost
                
                
                ##### tasks ######
                rec.total_revenue = float(revenue)
                rec.total_budget = budget if budget > 1 else frame_agreement_budget \
                    if frame_agreement_budget > 1 else sum_po_ids[0]
                # pos not in draft or cancel state
                confirmed_pos = rec.mapped('po_ids').filtered(
                    lambda po: po.state not in ['draft', 'cancel'])
                rec.total_paid_po_expenses = sum([amt.amount_total for amt in confirmed_pos])
                
                ##################
                rec.total_budgeted = budget
                rec.total_revenued = float(revenue)
                
                cr = rec.total_budgeted if budget > 1 else 1
                cost = rec.total_budgeted if budget > 1 else 1

                def compute_percentage(cost, rev):
                    '''sum = cost + revenue
                        (total_revenue_percentage = revenue * 100 / sum) = 45%
                        total_cost_percentage = cost * 100 / sum
                        e.g cost 250,000, revenue = 200,000 
                        
                        graph 45 / 55
                        '''
                    sum_revenue_cost = cost + rev
                    sum_revenue_cost = sum_revenue_cost if sum_revenue_cost > 1 else 1
                    total_revenue_percent = rev * 100.0 / sum_revenue_cost
                    return round(total_revenue_percent, 2)
                
                rec.total_revenue_percentage = compute_percentage(rec.total_cost, rec.total_revenue)
                
                rec.second_quad_percentage = compute_percentage(total_po_to_be_invoiced, total_paid_cost)
                rec.displayed_second_quad_percentage = f"{rec.second_quad_percentage} %"
                
                rec.third_quad_percentage = compute_percentage(total_closed_paid_cost, total_closed_paid_revenue)
                totalrealised = total_closed_paid_revenue - total_closed_paid_cost
                # rec.displayed_third_quad_percentage = '₦' + str("{0:,}".format(totalrealised)) if totalrealised > 0 else "₦ 0.00"
                rec.displayed_third_quad_percentage = '₦' + str("{0:,}".format(float(str(totalrealised).split('.')[0]))) if totalrealised > 0 else "₦ 0.00"
                
                rec.fourth_quad_percentage = compute_percentage(total_so_to_be_invoiced, total_paid_revenue)
                rec.displayed_fourth_quad_percentage = f"{rec.fourth_quad_percentage} %"
                
                rec.frame_agreement_budget = frame_agreement_budget
                
                fab = frame_agreement_budget if rec.frame_agreement_budget > 1 else 1
                rec.frame_agreement_budget_percentage = revenue * 100 / fab
                
                tr = revenue if revenue > 1 else 1
                rec.total_realized_percentage = paid_revenue * 100 / tr
                
            else:
                rec.total_budgeted = 0
                rec.total_revenue = 0.00
                rec.total_paid_revenue = 0.00
                rec.total_revenue_percentage = 0.00
                rec.second_quad_percentage = 0.00
                rec.third_quad_percentage = 0.00
                rec.fourth_quad_percentage = 0.00
                
                rec.frame_agreement_budget = 0.00
                rec.total_realized_percentage = 0.00
                rec.total_cost = 0.00
                rec.total_paid_cost = 0.00
                rec.total_paid_po_expenses = 0.00
                rec.total_closed_paid_revenue = 0.00
                rec.total_closed_paid_cost = 0.00
                rec.total_so_to_be_invoiced = 0.00
                
                rec.total_po_to_be_invoiced = 0.00
                rec.total_budget = 0.00
                rec.total_revenued = 0.00 
                
            # general_data = [{"values": [{"label": "Revenue", "type": "past", "value": total_revenue},
            #               {"label": "Cost", "type": "past", "value": total_budgeted}
            #               ]},
            #                 {"title": "", "key": "Residual amount", "is_sample_data": False}
            #                 ]
            # invoice_data = [{"values": [{"label": "Revenue", "type": "past", "value": total_paid_revenue},
            #               {"label": "Cost", "type": "past", "value": total_budgeted}
            #               ]},
            #                 {"title": "", "key": "Residual amount", "is_sample_data": False}]
            # rec.finance_general_dashboard_graph = json.dumps(general_data)
            # rec.finance_invoice_dashboard_graph = json.dumps(invoice_data)
    
    def view_general_finance(self):
        pass 
                
    def compute_so_naira_dollar_value(self, so_ids, currency='NGN'):
        total_budget_revenue, total_invoiced_revenue, total_paid_revenue, total_so_to_be_invoiced = 0.00, 0.00, 0.00, 0.00
        if so_ids:
            currency_usd_id = self.env.ref('base.USD') 
            usd_rate = currency_usd_id.mapped('rate_ids')
            rate = usd_rate[0].inverse_company_rate
            for so in so_ids:
                currency_id = so.pricelist_id.currency_id
                # compute btw dates of date approve
                two_date_before, two_date_after = so.date_order + timedelta(days=-2), so.date_order + timedelta(days=2)
                if currency in ['Naira', 'NGN']:
                    # do conversion to naira value
                    if currency_id.name == 'USD' or currency_id.id == 1:
                        # set the inverse company rate. ie compute from USD to naira
                        # filter the currency rate as at that time, if not found, used the current rate
                        # e.g 22 sep < 24 sep > 26 sept
                        
                        currency_rate = currency_id.mapped('rate_ids').filtered(
                            lambda cr: two_date_before.date() < cr.name and two_date_after.date() > cr.name
                            )
                        currency_rate_alternative = currency_id.rate_ids
                        if currency_rate.ids: # or currency_rate_alternative:
                            # rate = currency_rate[0].inverse_inverse_company_rate# or currency_rate_alternative[0].inverse_inverse_company_rate
                            rate = currency_rate[0].inverse_company_rate# or currency_rate_alternative[0].inverse_inverse_company_rate
                            total_budget_revenue += float(so.amount_total * rate)
                            total_invoiced_revenue += float(so.amount_total * rate) if so.state not in ['cancel'] else 0.00
                            total_so_to_be_invoiced += float(so.amount_total * rate) if so.invoice_status not in ['invoiced'] else 0.00
                            total_paid_revenue += float(so.amount_total * rate) if so.invoice_status in ['invoiced'] else 0.00
                        elif usd_rate:
                            rate = usd_rate[0].inverse_company_rate
                            total_budget_revenue += float(so.amount_total * rate)
                            total_invoiced_revenue += float(so.amount_total * rate) if so.state not in ['cancel'] else 0.00
                            total_paid_revenue += float(so.amount_total * rate) if so.invoice_status in ['invoiced'] else 0.00
                            total_so_to_be_invoiced += float(so.amount_total * rate) if so.invoice_status not in ['invoiced'] else 0.00
                        else:
                            raise ValidationError('You must ensure that both currencies (NGN, USD) has at least an update rate ids')
                    else: # value to display is in naira
                        total_budget_revenue += float(so.amount_total)
                        total_invoiced_revenue += float(so.amount_total) if so.state not in ['cancel'] else 0.00
                        total_paid_revenue += float(so.amount_total) if so.invoice_status in ['invoiced'] else 0.00
                        total_so_to_be_invoiced += float(so.amount_total) if so.invoice_status not in ['invoiced'] else 0.00
                else: 
                    # Convert all value to USD value
                    _logger.info(f'Rate SO converted {so.amount_total} --- {so.amount_total / 1600}')
                    if currency_id.name in ['NGN', 'Naira', False]:# or currency_id.currency_unit_label == 'Naira':
                        currency_rate = usd_rate.filtered(
                            lambda cr: two_date_before.date() < cr.name and two_date_after.date() > cr.name)
                        if currency_rate.ids:
                            # _logger.info(f'Rate sxxxx SO {currency_usd_id} --- {so}... {currency_rate} or {usd_rate}')
                            rate = currency_rate[0].inverse_company_rate or usd_rate[0].inverse_company_rate
                            # total += so.amount_total / rate
                            total_budget_revenue += float(so.amount_total / rate)
                            total_invoiced_revenue += float(so.amount_total / rate) if so.state not in ['cancel'] else 0.00
                            total_paid_revenue += float(so.amount_total / rate) if so.invoice_status in ['invoiced'] else 0.00
                            total_so_to_be_invoiced += float(so.amount_total / rate) if so.invoice_status not in ['invoiced'] else 0.00
                            # ie. 50000 * 1600
                        elif usd_rate:
                            rate = usd_rate[0].inverse_company_rate
                            total_budget_revenue += float(so.amount_total / rate)
                            total_invoiced_revenue += float(so.amount_total / rate) if so.state not in ['cancel'] else 0.00
                            total_paid_revenue += float(so.amount_total / rate) if so.invoice_status in ['invoiced'] else 0.00
                            total_so_to_be_invoiced += float(so.amount_total / rate) if so.invoice_status not in ['invoiced'] else 0.00
                            _logger.info(f"AT WHAT RATE {so.name} {so.amount_total} -{rate} TOTAL {total_budget_revenue}")
                        else:
                            raise ValidationError('You must ensure that currencies (USD) has at least an update rate ids')
                    else: # value to display is in USD
                        _logger.info(f"AT WHAT RATE 2{so.name}")
                        # total += so.amount_total
                        total_budget_revenue += float(so.amount_total)
                        total_invoiced_revenue += float(so.amount_total) if so.state not in ['cancel'] else 0.00
                        total_paid_revenue += float(so.amount_total) if so.invoice_status in ['invoiced'] else 0.00
                        total_so_to_be_invoiced += float(so.amount_total) if so.invoice_status not in ['invoiced'] else 0.00
        _logger.info(f"TOTAL COMPUTED 2 {total_budget_revenue} =--- {total_invoiced_revenue},  -- {total_paid_revenue}")
        return round(total_budget_revenue, 2), round(total_invoiced_revenue, 2), round(total_paid_revenue, 2),  round(total_so_to_be_invoiced, 2)
    
    def compute_po_naira_dollar_value(self, poo, currency='NGN'):
        total_cost, total_invoiced_cost, total_paid_cost, total_po_to_be_invoiced = 0.00, 0.00, 0.00, 0.00
        if poo:
            _logger.info(f'TEST MY {poo}')
            for po in poo:
                currency_id = po.currency_id
                # compute btw dates of date approve
                two_date_before, two_date_after = po.date_approve or po.date_order + timedelta(days=-2), po.date_approve or po.date_order + timedelta(days=2)
                if currency in ['Naira', 'NGN']:
                    # do conversion to naira value
                    if currency_id.name == 'USD' or currency_id.id == 1:
                        # set the inverse company rate. ie compute from USD to naira
                        # filter the currency rate as at that time, if not found, used the current rate
                        # e.g 22 sep < 24 sep > 26 sept
                        currency_rate = currency_id.mapped('rate_ids').filtered(
                            lambda cr: two_date_before.date() < cr.name and two_date_after.date() > cr.name
                            )
                        currency_usd_id = self.env.ref('base.USD')
                        usd_rate = currency_usd_id.mapped('rate_ids')
                        
                        currency_rate_alternative = currency_id.rate_ids
                        if currency_rate.ids: # if currency_rate or usd_rate:
                            _logger.info(f"am joj {currency_rate}")
                            rate = currency_rate[0].inverse_company_rate# or currency_rate_alternative[0].inverse_inverse_company_rate
                            total_cost += po.amount_total * rate
                            total_invoiced_cost += po.amount_total * rate if po.state not in ['draft', 'cancel'] else 0.00
                            total_paid_cost += po.amount_total * rate if po.invoice_status in ['invoiced'] else 0.00
                            total_po_to_be_invoiced += float(po.amount_total * rate) if po.invoice_status not in ['invoiced'] else 0.00
                        
                            # ie. 50000 * 0.002600
                        elif usd_rate:
                            rate = usd_rate[0].inverse_company_rate
                            total_cost += po.amount_total * rate
                            total_invoiced_cost += (po.amount_total * rate) if po.state not in ['draft', 'cancel'] else 0.00
                            total_paid_cost += (po.amount_total * rate) if po.invoice_status in ['invoiced'] else 0.00
                            total_po_to_be_invoiced += float(po.amount_total * rate) if po.invoice_status not in ['invoiced'] else 0.00
                        else:
                            raise ValidationError('You must ensure that both currencies (NGN, USD) has at least an update rate ids')
                    else: # value to display is in naira
                        total_cost += po.amount_total
                        total_invoiced_cost += po.amount_total if po.state not in ['draft', 'cancel'] else 0.00
                        total_paid_cost += po.amount_total if po.invoice_status in ['invoiced'] else 0.00
                        total_po_to_be_invoiced += float(po.amount_total) if po.invoice_status not in ['invoiced'] else 0.00
                else: 
                    # Convert all to USD value
                    if currency_id.name in ['NGN', 'Naira', False] or currency_id.currency_unit_label == 'Naira':
                        # set the company rate. ie compute from naira to USD
                        # filter the currency rate as at that time, if not found, used the current rate
                        # e.g 22 sep < 24 sep > 26 sept
                        currency_usd_id = self.env.ref('base.USD')
                        usd_rate = currency_usd_id.mapped('rate_ids')
                        
                        currency_rate = usd_rate.filtered(
                            lambda cr: two_date_before.date() < cr.name and two_date_after.date() > cr.name
                            )
                        # currency_rate_alternative = currency_id.rate_ids
                        if currency_rate.ids:
                            rate = currency_rate[0].inverse_company_rate or usd_rate[0].inverse_company_rate
                            # total += po.amount_total / rate
                            total_cost += float(po.amount_total / rate)
                            total_invoiced_cost += (po.amount_total / rate) if po.state not in ['draft', 'cancel'] else 0.00
                            total_paid_cost += po.amount_total / rate if po.invoice_status in ['invoiced'] else 0.00
                            total_po_to_be_invoiced += float(po.amount_total / rate) if po.invoice_status not in ['invoiced'] else 0.00
                            # ie. 50000 * 1600
                        elif usd_rate:
                            rate = usd_rate[0].inverse_company_rate
                            total_cost += float(po.amount_total / rate)
                            total_invoiced_cost += (po.amount_total / rate) if po.state not in ['draft', 'cancel'] else 0.00
                            total_paid_cost += (po.amount_total / rate) if po.invoice_status in ['invoiced'] else 0.00
                            total_po_to_be_invoiced += float(po.amount_total / rate) if po.invoice_status not in ['invoiced'] else 0.00
                        else:
                            raise ValidationError('You must ensure that both currencies (NGN, USD) has at least an update rate ids')
                    else: # value to display is in USD
                        total_cost += po.amount_total
                        total_invoiced_cost += po.amount_total if po.state not in ['draft', 'cancel'] else 0.00
                        total_paid_cost += po.amount_total if po.invoice_status in ['invoiced'] else 0.00
                        total_po_to_be_invoiced += float(po.amount_total) if po.invoice_status not in ['invoiced'] else 0.00
        _logger.info(f'TOTAL NOT INVOICED==> {total_po_to_be_invoiced}')
        return round(total_cost), round(total_invoiced_cost), round(total_paid_cost), round(total_po_to_be_invoiced, 2)
    
    @api.depends('memo_setting_id')
    def compute_task_info(self):
        for rec in self:
            if rec.attachment_ids:
                rec.attachment_ids.write({'res_model': rec._name, 'res_id': rec.id})
            rec.amountfig = sum([amt.amount_total for amt in rec.invoice_ids])
            if rec.memo_setting_id: 
                all_todo_ids = rec.memo_setting_id.sudo().mapped('stage_ids')
                all_invoices, all_documents = 0, 0
                all_todo_sub_invoices, all_todo_sub_documents = 0, 0
                revenue, paid_expense, realized_income =0, 0, 0
                all_active_sub_stage_ids = self.memo_sub_stage_ids
                all_active_invoice = rec.sudo().mapped('invoice_ids')
                all_active_document =rec.sudo().mapped('attachment_ids')
                for stage in all_todo_ids:
                    all_documents += len(stage.required_document_line.ids)
                    all_invoices += len(stage.required_invoice_line.ids)
                    for sub_stage in stage.sub_stage_ids:
                        all_todo_sub_documents += len(sub_stage.required_document_line.ids)
                        all_todo_sub_invoices += len(sub_stage.required_invoice_line.ids)
                sub_stage_doc, sub_stage_invoice = 0, 0
                for acsub in all_active_sub_stage_ids:
                    sub_stage_doc += len(acsub.attachment_ids.ids)
                    sub_stage_invoice += len(acsub.invoice_ids.ids)
                
                sub_stage_done_doc = 0
                sub_stage_done_invoice = 0
                for sub_active in self.memo_sub_stage_ids:
                    if sub_active.attachment_ids:
                        sub_stage_done_doc += len(sub_active.mapped('attachment_ids').filtered(lambda s: s.is_locked).ids)
                    if sub_active.invoice_ids:
                        sub_stage_done_invoice += len(sub_active.mapped('invoice_ids').filtered(lambda s: s.payment_state in ['paid', 'in_payment']))
                    sub_stage_doc += len(acsub.attachment_ids.ids)
                    sub_stage_invoice += len(acsub.invoice_ids.ids)

                todos = sum([all_invoices, all_documents , sub_stage_doc, sub_stage_invoice]) # get all the stages --> documents to update(not attached), invoices to process(not attached), sub process documents(not attached)
                active = sum([len(all_active_document.ids), len(all_active_invoice.ids), sub_stage_doc + sub_stage_invoice])  # get all the current stage --> documents to update, invoices to process, sub stages invoices and documents to process
                done = sum([
                    len(all_active_invoice.filtered(lambda ad: ad.payment_state in ['paid', 'in_payment'])), 
                    len(all_active_document.filtered(lambda ad: ad.is_locked)), 
                    sub_stage_done_invoice + 
                    sub_stage_done_doc
                    ]) # get all the current stage --> documents to update, invoices to process, sub stages invoices and documents to process
                total_sum_task = todos + active + done
                rec.write({
                    'task_todo': todos,
                    'task_active': active,
                    'task_done': done, 
                    # 'task_todo_percentage': todos * 100  / total_sum_task,
                    # 'task_active_percentage': active * 100  / total_sum_task,
                    # 'task_done_percentage': done * 100  / total_sum_task,
                }) 
            else:
                rec.write({
                    'task_todo': False,
                    'task_active': False,
                    'task_done': False, 
                    # 'task_todo_percentage': 0,
                    # 'task_active_percentage': 0,
                    # 'task_done_percentage': 0,
                })
        
    @api.depends('name')
    def _compute_task_info(self):
        for rec in self:
            if rec.memo_setting_id: 
                all_todo_ids = rec.memo_setting_id.sudo().mapped('stage_ids')
                all_invoices, all_documents = 0, 0
                all_todo_sub_invoices, all_todo_sub_documents = 0, 0
                revenue, paid_expense, realized_income =0, 0, 0
                all_active_sub_stage_ids = self.memo_sub_stage_ids
                all_active_invoice = rec.sudo().mapped('invoice_ids')
                all_active_document =rec.sudo().mapped('attachment_ids') 
                for stage in all_todo_ids:
                    all_documents += len(stage.required_document_line.ids)
                    all_invoices += len(stage.required_invoice_line.ids)
                    for sub_stage in stage.sub_stage_ids:
                        all_todo_sub_documents += len(sub_stage.required_document_line.ids)
                        all_todo_sub_invoices += len(sub_stage.required_invoice_line.ids)
                sub_stage_doc, sub_stage_invoice = 0, 0
                for acsub in all_active_sub_stage_ids:
                    sub_stage_doc += len(acsub.attachment_ids.ids)
                    sub_stage_invoice += len(acsub.invoice_ids.ids)
                
                sub_stage_done_doc = 0
                sub_stage_done_invoice = 0
                for sub_active in self.memo_sub_stage_ids:
                    if sub_active.attachment_ids:
                        sub_stage_done_doc += len(sub_active.mapped('attachment_ids').filtered(lambda s: s.is_locked).ids)
                    if sub_active.invoice_ids:
                        sub_stage_done_invoice += len(sub_active.mapped('invoice_ids').filtered(lambda s: s.payment_state in ['paid', 'in_payment']))
                    sub_stage_doc += len(acsub.attachment_ids.ids)
                    sub_stage_invoice += len(acsub.invoice_ids.ids)

                todos = sum([all_invoices, all_documents , sub_stage_doc, sub_stage_invoice]) # get all the stages --> documents to update(not attached), invoices to process(not attached), sub process documents(not attached)
                active = sum([len(all_active_document.ids), len(all_active_invoice.ids), sub_stage_doc + sub_stage_invoice])  # get all the current stage --> documents to update, invoices to process, sub stages invoices and documents to process
                done = sum([
                    len(all_active_invoice.filtered(lambda ad: ad.payment_state in ['paid', 'in_payment'])), 
                    len(all_active_document.filtered(lambda ad: ad.is_locked)), 
                    sub_stage_done_invoice + 
                    sub_stage_done_doc
                    ]) # get all the current stage --> documents to update, invoices to process, sub stages invoices and documents to process
                rec.write({
                    'task_todo': todos,
                    'task_active': active,
                    'task_done': done,
                    # 'expected_revenue': revenue,
                    # 'realized_income': realized_income,
                    # 'paid_expense': paid_expense,
                }) 
            else:
                rec.write({
                    'task_todo': False,
                    'task_active': False,
                    'task_done': False,
                    # 'expected_revenue': False,
                    # 'realized_income': False,
                    # 'paid_expense': False,
                })
    
    def write(self, vals):
        
        old_length = len(self.users_followers)
        if self.attachment_ids:
            self.attachment_ids.write({'res_model': self._name, 'res_id': self.id})
        
        res = super(Memo_Model, self).write(vals)
        if 'users_followers' in vals:
            if len(self.users_followers) < old_length:
                raise ValidationError("Sorry you cannot remove followers")
        return res

    @api.constrains('document_folder')
    def check_next_reoccurance_constraint(self):
        if self.document_folder and self.document_folder.next_reoccurance_date:
            if fields.Date.today() < self.document_folder.next_reoccurance_date:
                raise ValidationError(f'You cannot submit this document because the todays date is lesser than the reoccurence date {self.document_folder.next_reoccurance_date}')
     
    @api.constrains('project_memo_id')
    def check_project_memo_id_constraint(self):
        if self.id == self.project_memo_id.id:
            raise ValidationError("Sorry !!! you cannot set parent project with same file")
      
    set_all_po = fields.Boolean('Remove all record')
    def update_file_po(self):
        '''go to po lines, if memoid has code? remove else leave'''
        memos = self
        if self.set_all_po:
            memos = self.env['memo.model'].search([])
        for m in memos:
            records_to_unlink = []
            # if m.po_ids:
            for po in m.po_ids:
                # check if the po.memo_id have a code, unlink because it's a sub process/file PO
                if po.memo_id.code:
                    records_to_unlink.append(po.id)
            raise ValidationError(records_to_unlink)
            m.po_ids = [(3, r.id) for r in records_to_unlink]               
                    
    def send_memo_to_contacts(self):
        if not self.partner_ids:
            raise ValidationError('No partner is select, check to ensure your memo option is in "All or Selected"')
        view_id = self.env.ref('mail.email_compose_message_wizard_form')
        return {
                'name': 'Send memo Message',
                'view_type': 'form',
                'view_id': view_id.id,
                "view_mode": 'form',
                'res_model': 'mail.compose.message',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_partner_ids': self.partner_ids.ids,
                    'default_subject': self.name,
                    'default_attachment_ids': self.attachment_ids.ids,
                    'default_body_html': self.description,
                    'default_body': self.description,
                },
            } 
    # MEMO THINGS 
    ################################
    def _get_related_stage(self):
        if self.memo_type:
            domain = [
                ('memo_type', '=', self.memo_type.id), 
                ('department_id', '=', self.employee_id.department_id.id)
                ]
        else:
            domain=[('id', '=', 0)]
        return domain 
    
    @api.onchange('payment_ids')
    def get_payment_amount(self):
        if self.payment_ids:
            self.amountfig = sum([rec.amount for rec in self.payment_ids])
    
    @api.onchange('memo_type')
    def get_default_stage_id(self):
        """ Gives default stage_id """
        if self.memo_type:
            self.attachment_ids.unlink()
            if not self.employee_id.department_id:
                raise ValidationError("Contact Admin !!!  Employee must be linked to a department")
            if not self.res_users:
                department_id = self.employee_id.department_id
                ms = self.env['memo.config'].sudo().search([
                    ('memo_type', '=', self.memo_type.id),
                    # ('department_id', '=', department_id.id)
                    ], limit=1)
                
                if ms.stage_ids:
                    memo_setting_stage = ms.stage_ids[0]
                    self.stage_id = memo_setting_stage.id if memo_setting_stage else False
                    self.memo_setting_id = ms.id
                    self.update_validity_set(self.stage_id) 
                    self.memo_type_key = self.memo_type.memo_key 
                    self.has_sub_stage = True if memo_setting_stage.sub_stage_ids else False
                    self.users_followers = [
                        (4, self.employee_id.administrative_supervisor_id.id),
                        ]
                    invoices, documents = self.generate_required_artifacts(self.stage_id, self, '')
                    self.sudo().write({
                        'invoice_ids': [(4, iv) for iv in invoices],
                        'attachment_ids': [(4, dc) for dc in documents]
                        })
                    self.generate_sub_stage_artifacts(self.stage_id)
                else:
                    self.memo_type = False
                    self.stage_id = False
                    self.memo_setting_id = False
                    self.memo_type_key = False
                    # self.code = False
                    self.has_sub_stage = False 
        else:
            self.stage_id = False

    def generate_sub_stage_artifacts(self, stage_id):
        sub_stage_ids = stage_id.sub_stage_ids
        self.has_sub_stage = True if stage_id.sub_stage_ids else False
        self.sudo().write({
                'memo_sub_stage_ids': [(3, exist_stage.id) for exist_stage in self.memo_sub_stage_ids],
                })
        if sub_stage_ids:
            for stg in sub_stage_ids:
                sub_stage = self.env['memo.sub.stage'].sudo().create({
                    'name': stg.name,
                    'memo_id': self.id,
                    'sub_stage_id': stg.id,
                    'approver_ids': stg.approver_ids.ids,
                    'description': stg.description,
                })
                invoices, documents = self.generate_required_artifacts(stg, sub_stage, '')
                sub_stage.sudo().write({
                'invoice_ids': [(4, iv) for iv in invoices],
                'attachment_ids': [(4, dc) for dc in documents]
                })
                
                self.sudo().write({
                'memo_sub_stage_ids': [(4, sub_stage.id)],
                })

    def generate_required_artifacts(self, stage_id, obj, code=''):
        """This generate invoice lines from the configure stage"""
        stage_invoice_line = stage_id.mapped('required_invoice_line')
        stage_document_line = stage_id.mapped('required_document_line')
        invoices, documents= [], []
        if stage_invoice_line:
            if not self.client_id:
                raise ValidationError("Client / Partner must be selected before invoice validation")
            for stage_inv in stage_invoice_line:
                already_existing_stage_invoice_line = obj.mapped('invoice_ids').filtered(
                    lambda exist: exist.stage_invoice_name == stage_inv.name and exist.state not in ['posted'])
                if not already_existing_stage_invoice_line:
                    movetype = 'in_invoice' if stage_inv.move_type == 'vendor' else 'out_invoice'
                    invid = self.function_generate_move_entries(
                        invoice_name = f"{stage_inv.name}/{self.id}/{self.stage_id.id}", invoice_required=stage_inv.compulsory, code=code, movetype=movetype)
                    
                    invoices.append(invid.id)

        if stage_document_line:
            for stage_doc in stage_document_line:
                already_existing_stage_document_line = obj.mapped('attachment_ids').filtered(
                    lambda exist: exist.stage_document_name == stage_doc.name)
                if not already_existing_stage_document_line:
                    doc_name = f"EXP-P/{stage_doc.name}/{code}"
                    # ref = str(self.id)[] if str(self.id).startswith('NewId') else self.id
                    docid = self.function_generate_attachment(
                        attachment_name=stage_doc.name, 
                        report_binary = False, 
                        mimetype = False,
                        document_name = f"{stage_doc.name}-{self.id}-{stage_id.id}", 
                        compulsory=stage_doc.compulsory,
                        code=code
                        )
                    documents.append(docid.id) 
        return invoices, documents, 

    def function_generate_attachment(self, **kwargs):
        attachment_name, report_binary, mimetype,document_name, compulsory = kwargs.get('attachment_name'),\
            kwargs.get('report_binary'), kwargs.get('mimetype'), kwargs.get('document_name'), \
            kwargs.get('compulsory')
        code = kwargs.get('code')
        attachObj = self.env['ir.attachment']
        attachid = attachObj.search([('stage_document_name', '=', document_name),('code', '=', code)], limit=1) # recasting this means you must recast this line above
        if not attachid:
            attachid = attachObj.create({
                'name': attachment_name,
                # 'type': 'binary',
                'datas': report_binary,
                'store_fname': attachment_name,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': mimetype,
                'stage_document_name': document_name,
                'stage_document_required': compulsory,
                'code': code,
                'memo_id': self.id,
            })
        return attachid
    
    def function_generate_move_entries(self, **kwargs):
        """Check if the user is enlisted as the approver for memo type
        if approver is an account officer, system generates move and open the exact record"""
        # purchase payment journal
        movetype = kwargs.get('movetype')
        purchase_journal_id = self.env['account.journal'].search(
        [('type', '=', 'purchase'),
            ('code', '=', 'BILL')
            ], limit=1)
        sale_journal_id = self.env['account.journal'].search(
        [('type', '=', 'sale'), ('code', '=', 'INV')], limit=1)
        journal_id = purchase_journal_id if movetype == 'in_invoice' else sale_journal_id
        if not journal_id:
            raise ValidationError(
                "No journal configured for accounting, kindly contact admin to create one."
                )
        invoice_name = kwargs.get('invoice_name') or "-"
        invoice_required = kwargs.get('invoice_required')
        account_move = self.env['account.move'].sudo()
        # Please be careful not to remove this name below, 
        # name = f"EXP-P/{invoice_name}/{kwargs.get('code')}"
        prefix = 'P000001' if movetype == 'in_invoice' else 'S000001'
        suffix = '100' if self.memo_type_key in ['import_process', 'export_process'] else '200'
        domain = ('move_type', '=', 'in_invoice') if movetype == 'in_invoice' else ('move_type', '=', 'out_invoice')
        last_invoice = self.env['account.move'].search(
            [('name', 'ilike', prefix), domain], 
            order="create_date desc", 
            limit=1
            )
        
        if last_invoice:
            lastinv = last_invoice.name.split('-')
            suffix = int(lastinv[1]) + 1 if len(lastinv) > 1 else suffix
        prefix_code = f"{prefix}-{suffix}" 
        name = prefix_code
        inv = account_move.search([('name', '=', name)], limit=1) # recasting this means you must recast this line above
        if not inv:
            partner_id = self.client_id
            inv = account_move.create({ 
                'memo_id': self.id,
                'ref': name, #f'{prefix_code}-{self.code}',
                'origin': self.code,
                'partner_id': partner_id.id,
                'company_id': self.env.user.company_id.id,
                'currency_id': self.env.user.company_id.currency_id.id,
                # Do not set default name to account move name, because it
                'name': name,
                'move_type': movetype,
                'invoice_date': fields.Date.today(),
                'date': fields.Date.today(),
                'journal_id': journal_id.id,
                'stage_invoice_name': invoice_name or '',
                'stage_invoice_required': invoice_required if invoice_required else False,
            })
        return inv

    @api.depends('approver_id')
    def compute_user_is_approver(self):
        for rec in self:
            if rec.stage_id.is_approved_stage and self.env.user.id in [r.user_id.id for r in rec.stage_id.approver_ids]: 
                rec.user_is_approver = True
                rec.users_followers = [(4, self.env.user.employee_id.id)]
            else:
                rec.user_is_approver = False
 
    @api.model
    def fields_view_get(
        self, 
        view_id='company_memo.memo_model_form_view_3', 
        view_type='form', 
        toolbar=False, 
        submenu=False):
        res = super(Memo_Model, self).fields_view_get(view_id=view_id,
                                                      view_type=view_type,
                                                      toolbar=toolbar,
                                                      submenu = submenu)
        doc = etree.XML(res['arch']) 
        # users = self.env['memo.model'].search([('user_id', 'in', self.users_followers.user_id.id)])
        for rec in self.res_users:
            if rec.id == self.env.uid:
                for node in doc.xpath("//field[@name='users_followers']"):
                    node.set('modifiers', '{"readonly": true}') 
                    
                for node in doc.xpath("//button[@name='return_memo']"):
                    node.set('modifiers', '{"invisible": true}')
        res['arch'] = etree.tostring(doc)
        return res

    @api.depends('set_staff')
    def get_user_staff(self):
        for rec in self:
            if rec.set_staff:
                rec.demo_staff = rec.set_staff.user_id.id
            else:
                rec.demo_staff = False
    
    # get the employee's department
    @api.depends('employee_id')
    def employee_department(self):
        if self.employee_id:
            self.dept_ids = self.employee_id.department_id.id
        else:
            self.dept_ids = False
    
    @api.depends('employee_id')
    def compute_employee_supervisor(self):
        for rec in self:
            
            if rec.employee_id:
                current_user = rec.env.user
                if current_user.id == rec.employee_id.administrative_supervisor_id.user_id.id:
                    rec.is_supervior = True
                else:
                    rec.is_supervior = False
                
                if current_user.id == rec.employee_id.parent_id.user_id.id:
                    rec.is_manager = True
                else:
                    rec.is_manager = False
            else:
                rec.is_supervior = False
                rec.is_manager = False 

    def print_memo(self):
        report = self.env["ir.actions.report"].search(
            [('report_name', '=', 'company_memo.memomodel_print_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env.ref('company_memo.print_memo_model_report').report_action(self)
    
    def print_work_instruction(self):

        self.work_order_code = self.env['ir.sequence'].next_by_code('work-instruction')
        self.qr_code()
        report = self.env["ir.actions.report"].search(
            [('report_name', '=', 'company_memo.work_instruction_print_report_template')], limit=1)
        if report:
            report.write({'report_type': 'qweb-pdf'})
        return self.env.ref('company_memo.print_work_instruction_report').report_action(self)
    
    def set_draft(self):
        if self.env.uid != self.employee_id.user_id.id:
            raise ValidationError(
                "You are not allowed to resend this because you are not the initiator"
                )
        for rec in self:
            if rec.memo_setting_id and rec.memo_setting_id.stage_ids:
                draft_stage = rec.memo_setting_id.stage_ids[0]
                # removing user to allow resubmission
                user_id = self.mapped('res_users').filtered(
                    lambda user: user.id == self.env.uid
                    )
                if user_id:
                    rec.res_users = [(3, user_id.id)]
                rec.write({
                    'state': "submit", 
                    'direct_employee_id': False, 
                    'stage_id': draft_stage.id
                    })
     
    def user_done_memo(self):
        for rec in self:
            rec.write({'state': "Done"})
     
    def Cancel(self):
        if self.employee_id.user_id.id != self.env.uid:
            raise ValidationError(
                'Sorry!!! you are not allowed to cancel a memo not initiated by you.'
                ) 
        
        if self.state not in ['Refuse', 'Sent']:
            raise ValidationError(
                'You cannot cancel a memo that is currently undergoing management approval'
                )
        for rec in self:
            rec.write({
                'state': "submit", 
                'direct_employee_id': False, 
                'users_followers': False,
                'set_staff': False,
                })

    def get_url(self, id):
        base_url = http.request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        internal_path = "/web#id={}&model=memo.model&view_type=form".format(id)
        internal_url = base_url + internal_path
        return "<a href='{}'>Click</a>".format(internal_url)
    
    """line 4 - 7 checks if the current user is the initiator of the memo, 
    if true, raises warning error else: it opens the wizard"""

    def return_validator(self):
        user_exist = self.mapped('res_users').filtered(
            lambda user: user.id == self.env.uid
            )
        if user_exist and self.env.user.id not in [r.user_id.id for r in self.stage_id.approver_ids]:
            raise ValidationError(
                """Sorry you are not allowed to reject /  return you own initiated memo"""
                )
        
    def validate_memo_for_approval(self):
        item_lines = self.mapped('product_ids')
        type_required_items = ['material_request', 'procurement_request', 'vehicle_request']
        if self.memo_type.memo_key in type_required_items and self.state in ["Approve2"]:
            without_source_location_and_qty = item_lines.filtered(
                lambda sef: sef.source_location_id == False or sef.quantity_available < 1
                )
            if without_source_location_and_qty:
                 raise ValidationError(
                     """Please ensure all request lines 
                     has a source location and quantity greater than 0"""
                     )

    def validate_compulsory_document(self):
        """Check if compulsory documents have uploaded"""  
        attachments = self.mapped('attachment_ids').filtered(
                    lambda iv: not iv.datas
                )
        if attachments:
            for count, doc in enumerate(attachments, 1):
                isn = doc.name.split('/')
                doc_name = isn[0] if isn else '-'
                matching_attachment = self.stage_id.mapped('required_document_line').filtered(
                    lambda dc: dc.name == doc_name
                )
                matching_stage_doc = matching_attachment and matching_attachment[0]
                if matching_stage_doc.compulsory and not doc.datas:
                    document_name = doc.stage_document_name.replace('New', ' REF NO:')
                    raise ValidationError(f"""Attachment with name '{document_name}' at line {count} does not have any data attached
                        """
                        )

    def validate_waybill_details(self):
        if self.memo_setting_id.project_type == 'transport' or self.memo_type_key == "transport":
            '''Check if the stage requires waybill details validation'''
            if self.stage_id.require_waybill_detail: 
                details_required = []
                if not self.truck_company_name:
                    details_required.append('Truck company Name')
                if not self.truck_reg:
                    details_required.append('Truck Registration No')
                if not self.truck_driver:
                    details_required.append('Truck driver')
                if not self.truck_driver_phone:
                    details_required.append('Driver phone')
                if not self.waybill_note:
                    details_required.append('Waybill Note')
                if not self.truck_type:
                    details_required.append('Truck type')
                if not self.waybill_from:
                    details_required.append('Waybill From')
                if not self.waybill_to:
                    details_required.append('Waybill To')
                if not self.waybill_date:
                    details_required.append('Waybill Date')
                if not self.waybill_expected_arrival_date:
                    details_required.append('Expected Arrival')
                if not self.waybill_ids:
                    details_required.append('Waybill items')
                if details_required:
                    raise ValidationError(f"{','.join(details_required)} fields must be provided")
                
    def validate_po_line(self):
        '''if the stage requires PO confirmation'''
        self.procurement_confirmation()

    def validate_so_line(self):
        self.sale_order_confirmation()
 
    def validate_invoice_line(self):
        '''Check all invoice in draft and check if 
        the current stage that matches it is compulsory
        if compulsory, system validates it'''
        
        invoice_ids = self.mapped('invoice_ids').filtered(
                    lambda iv: iv.state in ['draft']
                )
        if invoice_ids:
            for count, inv in enumerate(invoice_ids, 1):
                isn = inv.stage_invoice_name.split('/') if inv.stage_invoice_name else False
                inv_stage_name = isn[0] if isn else '-'
                matching_stage_invoice = self.stage_id.mapped('required_invoice_line').filtered(
                    lambda rinv: rinv.name == inv_stage_name
                )
                matching_stage_invoice = matching_stage_invoice and matching_stage_invoice[0]
                if matching_stage_invoice.compulsory:
                    if inv.payment_state not in ['paid', 'partial', 'in_payment']:
                        raise ValidationError(f"Invoice at line {count} must be posted and paid before proceeding")
                    invoice_line = inv.mapped('invoice_line_ids')
                    if not invoice_line:
                        raise ValidationError(f"Add at least one invoice billing line at line {count}")
                    invoice_line_without_price = inv.mapped('invoice_line_ids').filtered(
                        lambda s: s.price_unit <= 0
                        )
                    if invoice_line_without_price:
                        raise ValidationError(f"All invoice line must have a price amount greater than 0 at line {count}")

    def validate_payment_line(self):
        '''Ensures a payment line is added if is_internal transfer'''
        msg = """
        Please ensure at least one payment line / Finance line is added!!!. 
        Use the Payment request / Finance tab
        """
        if self.is_internal_transfer and not self.invoice_ids:
            raise ValidationError(msg) 
        if self.external_memo_request and not self.payment_ids:
            raise ValidationError(msg) 
            
    def validate_sub_stage(self):
        for count, rec in enumerate(self.memo_sub_stage_ids, 1):
            if not rec.sub_stage_done:
                raise ValidationError(f"""There are unfinished sub task at line {count} that requires completion before moving to the next stage""")
    
    def validate_other_validity(self):
        if self.stage_id.enabled_date_validity_config and not self.enabled_date_validity:
            raise ValidationError("Please kindly ensure date validity is set")
        if self.stage_id.enabled_date_procured_config and not self.enabled_date_procured:
            raise ValidationError("Please kindly ensure date procured is set")
        if self.stage_id.enable_procurment_amount_config and not self.enable_procurment_amount:
            raise ValidationError("Please kindly ensure procurement amount is added")
        if self.stage_id.enabled_date_paid_config and not self.enabled_date_paid:
            raise ValidationError("Please kindly ensure date paid is added")
    
    # self.validate_waybill_details()
    # self.validate_po_line()
    # self.validate_so_line()
    # self.validate_invoice_line()
    # self.validate_other_validity()
    
    ################### BUDGET ##############
    '''
    If is budget verification process, system auto set the field
    budget_id will show only budget heads of MDAs,
    Once you select budget_has_allocation, throws an error if no budget allocation
    amount is found
    '''
    is_budget_verification_memo_request = fields.Boolean(
        string='Is Budget Verification Process',
        related="memo_type.is_verification",
        default=False)
    budget_has_allocation = fields.Boolean(
        string='Has Allocation', 
        default=False, store=True)
    budget_id = fields.Many2one(
        'ng.account.budget', 
        string='Budget Head', 
        store=True, 
        # domain=lambda self: self._get_related_stage(),
        )
    is_budget_allocation_request = fields.Boolean(
        string='Is Budget Allocation Process',
        related="memo_type.is_allocation",
        default=False)
    # required and visible if budget allocation is set
    # if completed, system generates a line in ng.account.budget.line with the budget head Id selected
    budget_balance_amount = fields.Float(
        string='Budget Balance Amount', 
        store=True, 
        )
    budget_amount = fields.Float(
        string='Budget Amount', 
        store=True, 
        )
    
    @api.onchange("budget_id")
    def change_budget_record(self):
        if self.budget_id:
            self.budget_balance_amount = self.budget_id.budget_variance
        else:
            self.budget_balance_amount = 0
            
    def check_aprrover_user(self):
        # if self.env.user.id not in [r.user_id.id for r in self.stage_id.approver_ids]:
        # if self.env.user.id != self.create_uid.id:
        #     raise ValidationError(
        #         f"""You are not responsible to validate this record. \n\
        #         Current User ID: {self.env.user.name} and {self.create_uid.name}"""
        #         )
        pass
            
    # the budget approved by request MDA
    # visible if is_budget_allocation_request is true
    
    def approve_budget_allocation(self):
        self.check_aprrover_user()
        for rec in self:
            
            # budget = self.env['ng.account.budget'].create({
            #     'name': f"{self.branch_id.name} - f{datetime.strftime(fields.Date.today(), '%Y-%m-%d')}", 
            #     'date_from': fields.Date.today(),
            #     'date_to': fields.Date.today() + relativedelta(months=5), 
            #     'general_journal_id': self.branch_id.default_journal_id.id,
            #     'general_account_id': self.branch_id.default_account_id.id,
            #     'budget_amount': self.budget_amount,
            #     'active': True,
            #     'branch_id': self.branch_id.id,
            #     'paid_date': fields.Date.today(),
            # })
            
            if not any([rec.budget_amount, self.budget_id]):
                raise ValidationError(f"""
                                      Record with code number {rec.code} does not have 
                                      Budget head or budget amount
                                      """)
            if not rec.request_mda_from.default_journal_id or not self.request_mda_from.default_account_id:
                raise ValidationError(f"""
                                      Ensure the {rec.request_mda_from.name} has default journal and default account id set
                                      Contact Admin to properly set it in the multi branch setting
                                      """)
            account_move = self.env['account.move'].sudo()
            inv = account_move.search([('memo_id', '=', rec.id)], limit=1)
            if not inv:
                inv = account_move.create({ 
                    'memo_id': self.id,
                    'ref': self.code,
                    'origin': self.code,
                    'partner_id': self.env.user.partner_id.id,
                    'company_id': self.env.user.company_id.id,
                    'currency_id': self.env.user.company_id.currency_id.id,
                    # Do not set default name to account move name, because it
                    # is unique 
                    # 'name': f"CADV/ {self.code}",
                    # 'move_type': 'in_receipt',
                    'invoice_date': fields.Date.today(),
                    'ng_budget_id': self.budget_id.id,
                    'date': fields.Date.today(),
                    'journal_id': self.request_mda_from.default_journal_id.id,
                    'line_ids': [
                        (0, 0, vals) for vals in [
                            {
                                # 'move_id': inv.id,
                                'name': rec.description,
                                'ref': f'{self.code}',
                                'account_id': self.request_mda_from.default_account_id.id or self.request_mda_from.default_account_id.id,
                                'debit': rec.budget_amount,
                                'quantity': 1,
                                'code': rec.code,
                                # 'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
                                # 'product_id': pr.product_id.id if pr.product_id else None,
                            }, 
                            {
                                # 'move_id': inv.id,
                                'name': rec.description,
                                'ref': f'{self.code}',
                                'account_id': self.branch_id.default_account_id.id or self.branch_id.default_journal.default_account_id.id,
                                'credit': rec.budget_amount, 
                                'code': rec.code, 
                            }
                        ]
                    ]
                }) 
            view_id = self.env.ref('account.view_move_form').id
            ret = {
                'name': "Account Move",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'account.move',
                'res_id': inv.id,
                'type': 'ir.actions.act_window',
                'target': 'current'
                }
            return ret
   
    @api.onchange('budget_id')
    def check_budget_funds(self):
        if self.budget_id:
            if self.budget_id.budget_variance <= 0:
                raise ValidationError("""
                                  There is no budget allocated for the budget head
                                  """)
            else:
                self.budget_has_allocation = True
        else:
            self.budget_has_allocation = False
            
    # def _get_related_budget(self):
    #     # user = self.env.user
    #     # branch = self.branch_id
    #     # if user.branch_id or user.allowed_branch_ids:
    #     #     ng_budget_ids = self.env['ng.account.budget'].search([
    #     #         '|',('branch_id', 'in', user.allowed_branch_ids.ids),
    #     #         ('branch_id', '=', user.branch_id.id)])
    #     #     branch_budget_ids = [rec.id for rec in ng_budget_ids]
    #     #     domain = [('id', 'in', branch_budget_ids)] 
    #     #     raise ValidationError(user.branch_id.name)
    #     # else:
    #     #     domain=[('id', '=', 1112)]
    #     return []
    has_print_budget_certificate = fields.Boolean('budget certificated print', store=True)

    def generate_memo_attachment(self, attachment_name, pdf_content):
        attachmentObj = self.env['ir.attachment'].create({
            'name': attachment_name,
            'type': 'binary',
            'datas': pdf_content,
            'store_fname': attachment_name,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/x-pdf'
        })
        return attachmentObj
    
    def print_budget_certifcation(self):
        pass 
        # create report 
        # generate the report as attachment
        # create attachment on the attachment line
        # self.has_print_budget_certificate = True
        # pdf = self.env.ref('plateau_addons.print_budget_certificate_report').report_action(self) 
        # pdf_content = base64.b64encode(pdf)
        # attachment = self.generate_attachment(pdf_content)
        # if attachment:
        #     self.attachment_ids = [(4, attachment.id)]
        
    def confirm_budget_verification(self):
        self.check_aprrover_user()
        memo_setting_id = self.memo_setting_id
        last_stage = memo_setting_id.stage_ids.ids[-1]
        if not self.has_print_budget_certificate:
            raise ValidationError("Please ensure you have printed the budget certification recommended to be attached to physical document(s) sent to the governor")
        self.confirm_memo(self.env.user.employee_id, "Record is now finally validated")
        
    
    ################################
    def validate_payments(self):
        if self.stage_id.require_bill_payment: 
            payment_unposted = self.mapped('payment_ids').filtered(
                    lambda st: st.state in ['draft']
                )
            if payment_unposted:
                raise ValidationError("Please kindly Post each payment on payment lines")
            
                
    def forward_memo(self):
        self.validate_compulsory_document()
        self.validate_sub_stage()
        self.validate_payments()
        user_exist = self.mapped('res_users').filtered(
            lambda user: user.id == self.env.uid
            )
        if user_exist and self.env.user.id not in [r.user_id.id for r in self.stage_id.approver_ids]:
            raise ValidationError(
                """You cannot forward this memo again unless returned / cancelled!!!"""
                )
        self.validate_payment_line()
        # if self.memo_project_type in ['project_pro'] and not self.po_ids.ids:
        #     raise ValidationError(
        #         """You cannot forward this memo without Purchase lines added"""
        #         )
        if self.document_folder and not self.env['ir.attachment'].sudo().search([
                ('res_id', '=', self.id), 
                ('res_model', '=', self._name)
            ]):
            raise ValidationError(
                """Please attach at least one document"""
                )
        memo_setting_id = self.memo_setting_id
        first_stage = memo_setting_id.stage_ids.ids.index(self.stage_id.id)      
        if self.external_memo_request:
            """Check if the first stage has governors approval"""
            if first_stage == 0 and not self.env['ir.attachment'].sudo().search([
                ('res_id', '=', self.id), 
                ('res_model', '=', self._name)]):
                raise ValidationError(
                    """Please attach governor's approval"""
                    )
        if self.is_contract_memo_request:
            if first_stage == 0 and not self.env['ir.attachment'].sudo().search([
                ('res_id', '=', self.id), 
                ('res_model', '=', self._name)]):
                raise ValidationError(
                    """Please attach contract verification document"""
                    )
            # did another check here to ensure user selects payment line
            if not self.contractor_ids:
                raise ValidationError(
                    """Please Add contractor request lines"""
                    )

        # if self.to_unfreezed_budget and not self.po_ids:
        #     raise ValidationError("Please add PO and Provide reasons for Additional PO approval")
        if self.memo_type.memo_key == "Payment":
            if self.contractor_ids or self.payment_ids or self.invoice_ids:# self.amountfig <= 0:
                # raise ValidationError(
                #     """Please Add payment request lines"""
                #     ) 
                pass
            else:
                raise ValidationError("Please add the payment lines or contractor lines")
        elif self.memo_type.memo_key == "material_request" and not self.product_ids:
            raise ValidationError("Please add request line") 
        view_id = self.env.ref('company_memo.memo_model_forward_wizard')
        condition_stages = [self.stage_id.yes_conditional_stage_id.id, self.stage_id.no_conditional_stage_id.id] or []
        # if not self.is_budget_verification_memo_request:
        #     self.confirm_budget_verification()
        # else:  
        return {
                'name': 'Forward Memo',
                'view_type': 'form',
                'view_id': view_id.id,
                "view_mode": 'form',
                'res_model': 'memo.foward',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_memo_record': self.id,
                    'default_resp': self.env.uid,
                    'default_dummy_conditional_stage_ids': [(6, 0, condition_stages)],
                    'default_has_conditional_stage': True if self.stage_id.memo_has_condition else False,
                },
            }

    """The wizard action passes the employee whom the memo was director to this function."""
    def get_initial_stage(self, memo_type, department_id):
        memo_settings = self.env['memo.config'].sudo().search([
            ('memo_type.memo_key', '=', memo_type),
            ('department_id', '=', department_id)
            ], limit=1)
        if memo_settings and memo_settings.stage_ids:
            initial_stage_id = memo_settings.stage_ids[0]
        else:
            initial_stage_id= self.env.ref('company_memo.memo_initial_stage')
        return initial_stage_id
        
    def get_next_stage_artifact(self, current_stage_id, from_website=False):
        """
        args: from_website: used to decide if the record is 
        generated from the website or from odoo internal use
        """
        approver_ids = []
        memo_settings = self.env['memo.config'].sudo().search([
            ('memo_type', '=', self.memo_type.id),
            ('department_id', '=', self.employee_id.department_id.id)
            ], limit=1)
        memo_setting_stages = memo_settings.mapped('stage_ids').filtered(
            lambda skp: skp.id != self.stage_to_skip.id
        )
        if memo_settings and current_stage_id:
            mstages = memo_settings.stage_ids # [3,6,8,9]
            _logger.info(f'Found stages are {memo_setting_stages.ids}')
            last_stage = mstages[-1] if mstages else False # 'e.g 9'
            if last_stage and last_stage.id != current_stage_id.id:
                current_stage_index = memo_setting_stages.ids.index(current_stage_id.id)
                next_stage_id = memo_setting_stages.ids[current_stage_index + 1] # to get the next stage
            else:
                next_stage_id = self.stage_id.id
            next_stage_record = self.env['memo.stage'].browse([next_stage_id])
            if next_stage_record:
                approver_ids = next_stage_record.approver_ids.ids
            return approver_ids, next_stage_record.id
        else:
            raise ValidationError(
                "Please ensure to configure the Memo type for the employee department"
                )
    
    def update_final_state_and_approver(self, from_website=False, default_stage=False, assigned_to=False):
        if from_website:
            pass
        else:
            # updating the next stage
            approver_ids = self.get_next_stage_artifact(self.stage_id)[0] 
            next_stage_id= default_stage or self.get_next_stage_artifact(self.stage_id)[1] 
            self.stage_id = next_stage_id
            self.freeze_po_budget = self.stage_id.freeze_po_budget
            invoices, documents = self.generate_required_artifacts(self.stage_id, self, self.code)
            self.sudo().write({
                'invoice_ids': [(4, iv) for iv in invoices],
                'attachment_ids': [(4, dc) for dc in documents]
                })
            self.generate_sub_stage_artifacts(self.stage_id)
            # determining the stage to update the already existing state used to hide or display some components
            if self.stage_id:
                if self.stage_id.is_approved_stage:
                    if self.memo_type.memo_key in ["Payment", 'loan', 'cash_advance', 'soe']:
                        self.state = "Approve"
                    else:
                        self.state = "Approve2"
                # important: users_followers must be required in for them to see the records.
                if self.sudo().stage_id.approver_ids:
                    self.sudo().update({
                        'users_followers': [(4, appr.id) for appr in self.sudo().stage_id.approver_ids],
                        'set_staff': assigned_to.id if assigned_to else self.sudo().stage_id.approver_ids[0].id # FIXME To be reviewed
                        })
            if self.memo_setting_id and self.memo_setting_id.stage_ids:
                ms = self.memo_setting_id.stage_ids
                last_stage = ms[-1]
                # if id of next stage is the same with the id of the last stage of memo setting stages, 
                # write stage to done
                random_memo_approver_ids = [rec.id for rec in self.memo_setting_id.approver_ids if rec]
                if last_stage.id == next_stage_id:
                    self.sudo().write({
                            'state': 'Done',
                            'closing_date': fields.Date.today(),
                            })
                    if last_stage.approver_ids or random_memo_approver_ids:
                        approver_ids = last_stage.approver_id.ids or random_memo_approver_ids
                        self.sudo().write({
                            # 'approver_id': random.choice(approver_ids),
                            'approver_ids': [(4, appr) for appr in approver_ids],
                            })
            self.update_validity_set(self.stage_id)

    def lock_artifacts_from_modification(self):
        attachments = self.mapped('attachment_ids')
        invoices = self.mapped('invoice_ids')
        for att in attachments:
            att.is_locked = True

        for inv in invoices:
            inv.is_locked = True
        
        if self.memo_sub_stage_ids:
            for sub in self.memo_sub_stage_ids:
                attachments = sub.mapped('attachment_ids')
                invoices = sub.mapped('invoice_ids')
                for subatt in attachments:
                    subatt.is_locked = True

                for subinv in invoices:
                    subinv.is_locked = True
 
    def confirm_memo(self, employee, comments, from_website=False, default_stage_id=False): 
        '''args => default_stage_id : stage_obj'''
        type = "loan request" if self.memo_type.memo_key == "loan" else "memo"
        Beneficiary = self.employee_id.name or self.user_ids.name
        body_msg = f"""Dear sir / Madam, \n <br/>
        I wish to notify you that a {type} with description,\n {self.name},
        from {Beneficiary} (Department: {self.employee_id.department_id.name or "-"}) \
        was sent to you for review / approval. \n <br/> Kindly {self.get_url(self.id)} \n <br/>
         Yours Faithfully.{self.env.user.name}""" 
        self.direct_employee_id = False 
        self.lock_artifacts_from_modification() # first locks already generated artifacts to avoid further modification
        if default_stage_id:
            # first set the stage id and then update
            self.update_final_state_and_approver(from_website, default_stage_id)
        else:
            self.update_final_state_and_approver(from_website, False, employee)
        # update the po_memo_ids with child data
        if self.to_unfreezed_budget and self.project_memo_id:
            self.project_memo_id.po_memo_ids = [(4, self.id)]

        self.mail_sending_direct(body_msg)
        body = "%s for %s initiated by %s, moved by- ; %s and sent to %s" %(
            type,
            self.name,
            Beneficiary,
            self.env.user.name,
            employee.name
            )
        body_main = body + "\n with the comments: %s" %(comments)
        self.follower_messages(body_main)
        self.compute_task_info()
        # self.update_dashboard_finances()

    def update_validity_set(self, stageObj):
        self.validity_set = True if stageObj and \
            stageObj.enabled_date_paid_config or stageObj.enable_procurment_amount_config \
                or stageObj.enabled_date_procured_config or stageObj.enabled_date_validity_config else False
        # setting the stage start date
        self.task_start_date = fields.Date.today()
        stage_duration = stageObj.duration_config # default 20
        self.task_end_date = fields.Date.today() + timedelta(days=stage_duration) 
             
    def procurement_confirmation(self):
        if self.stage_id.require_po_confirmation:
            if not self.po_ids:
                raise ValidationError("Please enter purchase order lines")
            else:
                # i removed this because Timothy said So: 
                pass 
                
                # po_without_lines = self.mapped('po_ids').filtered(
                #     lambda tot: tot.amount_total < 1
                # )
                # if po_without_lines:
                #     raise ValidationError("Please kindly ensure that all purchase order lines are added with price amount")

            po_without_confirmation = self.mapped('po_ids').filtered(
                    lambda st: st.state in ['draft', 'sent']
                )
            if po_without_confirmation:
                raise ValidationError(
                    """All POs must be confirmed at this stage. To avoid errors, 
                    Please kindly go through each PO to confirm them""")
        if self.stage_id.require_bill_payment: 
            # '''Checks if the PO is expecting a picking count and there is no pickings '''
            # without_picking_reciept = self.mapped('po_ids').filtered(
            #         lambda st: st.incoming_picking_count > 0 and not st.picking_ids
            #     )
            # if without_picking_reciept:
            #     raise ValidationError('Please ensure all PO(s) has been recieved before Vendor Bill is generated')
            # for po in self.mapped('po_ids'):
            #     if po.mapped('picking_ids').filtered(
            #         lambda st: st.state != "done"
            #     ):
            #         raise ValidationError("Please ensure all PO picking / receipts are marked done before vendor bill is generated")
            po_without_invoice_payment = self.mapped('po_ids').filtered(
                    lambda st: st.invoice_status not in ['invoiced']
                )
            if po_without_invoice_payment:
                raise ValidationError("Please kindly create and pay the bills for each PO lines")
            
    def sale_order_confirmation(self):
        if self.stage_id.require_so_confirmation:
            if not self.so_ids:
                raise ValidationError(
                    """Please enter Sale order lines"""
                    )
            so_without_lines = self.mapped('so_ids').filtered(
                    lambda tot: tot.amount_total < 1
                )
            if so_without_lines:
                    raise ValidationError("Please kindly ensure that all Sale order lines are added with price amount")

            so_without_confirmation = self.mapped('so_ids').filtered(
                    lambda st: st.state in ['draft', 'sent']
                )
            if so_without_confirmation:
                raise ValidationError(
                    """All SOs must be confirmed at this stage. To avoid errors, 
                    Please kindly go through each SO to confirm them""")
        if self.stage_id.require_bill_payment:
            '''Checks if the PO is expecting a picking count and there is no pickings '''
            so_without_invoice_payment = self.mapped('so_ids').filtered(
                    lambda st: st.invoice_status not in ['invoiced'])
            if so_without_invoice_payment:
                raise ValidationError("Please kindly create and pay the bills for each Client Invoice lines")
 
    def mail_sending_direct(self, body_msg): 
        subject = "Memo Notification"
        email_from = self.env.user.email
        follower_list = [item2.work_email for item2 in self.users_followers if item2.work_email]
        stage_followers_list = [
            appr.work_email for appr in self.stage_id.memo_config_id.approver_ids if appr.work_email
            ] if self.stage_id.memo_config_id.approver_ids else []
        
        '''this is also going to send mail to the sub stage / task assignees'''
        sub_task_list = []
        for subtask in self.stage_id.sub_stage_ids:
            sub_task_list += [ap.work_email for ap in subtask.approver_ids if ap.work_email]
        email_list = follower_list + stage_followers_list + sub_task_list
        approver_emails = [eml.work_email for eml in self.stage_id.approver_ids if eml.work_email] + sub_task_list
        mail_to = (','.join(approver_emails)) 
        emails = (','.join(elist for elist in email_list))
        mail_data = {
                'email_from': email_from,
                'subject': subject,
                'email_to': mail_to or emails,
                'reply_to': email_from,
                'email_cc': emails,
                'body_html': body_msg
            }
        mail_id = self.env['mail.mail'].sudo().create(mail_data)
        self.env['mail.mail'].sudo().send(mail_id)
    
    def _get_group_users(self):
        followers = []
        account_id = self.env.ref('company_memo.mainmemo_account')
        acc_group = self.env['res.groups'].search([('id', '=', account_id.id)], limit=1)
        for users in acc_group.users:
            employee = self.env['hr.employee'].search([('user_id', '=', users.id)])
            for rex in employee:
                followers.append(rex.id)
        return self.write({'users_followers': [(4, follow) for follow in followers]})
    
    def determine_if_user_is_config_approver(self):
        """
        This determines if the user is responsible to approve the memo as a Purchase Officer
        This will open up the procurement application to proceed with the respective record
        """
        memo_settings = self.env['memo.config'].sudo().search([
            ('id', '=', self.memo_setting_id.id)
            ])
        memo_approver_ids = memo_settings.approver_ids
        user = self.env.user
        emloyee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if emloyee and emloyee.id in [emp.id for emp in memo_approver_ids] or self.env.uid in [r.user_id.id for r in self.stage_id.approver_ids]:
            return True
        else:
            return False

    def complete_memo_transactions(self): # Always available to Some specific groups
        body = "MEMO COMPLETION NOTIFICATION: -Approved By ;\n %s on %s" %(self.env.user.name,fields.Date.today())
        body_msg = f"""Dear {self.employee_id.name}, 
        <br/>I wish to notify you that a {type} with description, '{self.name}',\
        from {self.employee_id.department_id.name or self.user_ids.name} \
        department have been Confirmed by {self.env.user.name}.<br/>\
        Respective authority should take note. \
        <br/>Kindly {self.get_url(self.id)} <br/>\
        Yours Faithfully<br/>{self.env.user.name}"""
        return self.generate_memo_artifacts(body_msg, body)

    def check_supervisor_comment(self):
        if self.memo_type.memo_key == "server_access":
            if self.employee_id.administrative_supervisor_id and not self.supervisor_comment:
                raise ValidationError(
                    """Please Inform the employee's supervisor to comment on this before approving 
                    """)
            elif not self.employee_id.administrative_supervisor_id and not self.manager_comment:
                raise ValidationError(
                    """Please Inform the employee's Manager to comment on this before approving 
                    """)
                    
    def user_approve_memo(self): # Always available to Some specific groups
        return self.approve_memo()

    def approve_memo(self): # Always available to Some specific groups
        ### check if supervisor has commented on the memo if it is server access
        self.check_supervisor_comment()
        self.procurement_confirmation()
        is_config_approver = self.determine_if_user_is_config_approver()
        if self.env.uid == self.employee_id.user_id.id and not is_config_approver:
            raise ValidationError(
                """You are not Permitted to approve a Payment Memo. 
                Forward it to the authorized Person""")
        if self.env.uid not in [r.user_id.id for r in self.stage_id.approver_ids]:
            raise ValidationError(
                """You are not Permitted to approve this Memo. Contact the authorized Person"""
                )
        body = "MEMO APPROVE NOTIFICATION: -Approved By ;\n %s on %s" %(self.env.user.name,fields.Date.today())
        type = "request"
        body_msg = f"""Dear {self.employee_id.name}, <br/>I wish to notify you that a {type} with description, '{self.name}',\
                from {self.employee_id.department_id.name or self.user_ids.name} department have been approved by {self.env.user.name}.<br/>\
                Respective authority should take note. \
                <br/>Kindly {self.get_url(self.id)} <br/>\
                Yours Faithfully<br/>{self.env.user.name}"""
        users = self.env['res.users'].sudo().browse([self.env.uid])
        self.validate_compulsory_document()
        self.update_final_state_and_approver()
        
        # REASON WHY I AM DOING THIS IS UNKNOWN: 
        '''If the file has a parent project and there is no code generated
        system should update the PO lines of the parent project: 
        This means the POs is an Added PO approval for that project
        
        But if the process has parent project and has a code, the the PO line shouldnt be added to the 
        parent project. it is a sub project'''
        # update the related memo PO if PO exist 
        if self.project_memo_id and self.code in [False, '', None]:
            if self.po_ids:
                self.project_memo_id.po_ids = [(4, po.id) for po in self.po_ids]

        self.sudo().write({'res_users': [(4, users.id)]})
        return self.generate_memo_artifacts(body_msg, body)
  
    def generate_memo_artifacts(self, body_msg, body):
        if self.memo_type.memo_key == "material_request":
            return self.generate_stock_material_request(body_msg, body)
        elif self.memo_type.memo_key == "procurement_request":
            return self.generate_stock_procurement_request(body_msg, body)
        elif self.memo_type.memo_key == "vehicle_request":
            self.generate_vehicle_request(body_msg) 
        elif self.memo_type.memo_key == "recruitment_request":
            self.generate_recruitment_request(body_msg) 
        elif self.memo_type.memo_key == "leave_request":
            self.generate_leave_request(body_msg, body)
        elif self.memo_type.memo_key == "cash_advance":
            self.update_memo_type_approver()
            self.mail_sending_direct(body_msg)
        elif self.memo_type.memo_key == "soe":
            self.update_memo_type_approver()
            self.mail_sending_direct(body_msg)
        elif self.memo_type.memo_key == "server_access":
            self.update_memo_type_approver()
            self.mail_sending_direct(body_msg)

        elif self.memo_type.memo_key == "Payment":
            self.generate_payment_request(body_msg)
            self.mail_sending_direct(body_msg)

        elif self.memo_type.memo_key == "employee_update":
            return self.generate_employee_update_request()
        else:
            document_message = "Also check related documentation on the document management system" if self.to_create_document else ""
            body_msg = f"""Dear sir / Madam, \n <br/>
            <br/>I wish to notify you that a {type} with description, {self.name},\n <br/> 
            from {self.employee_id.name} (Department: {self.employee_id.department_id.name or "-"}) \
            was sent to you for review / approval. \n <br/> {document_message} \n <br/>
            Kindly {self.get_url(self.id)} \n <br/>
            <br/> Yours Faithfully<br/>{self.env.user.name}"""
            self.state = "Done"
            self.update_final_state_and_approver()
            self.direct_employee_id = False
            self.generate_document_management()
            self.mail_sending_direct(body_msg)

    def generate_document_management(self):
        if self.to_create_document:
            document_obj = self.env['documents.document'].sudo()
            document_folder_obj = self.env['documents.folder'].sudo()
            attach_document_ids = self.env['ir.attachment'].sudo().search([
                ('res_id', '=', self.id), 
                ('res_model', '=', self._name)
            ])
            document_folder = document_folder_obj.search([('id', '=', self.document_folder.id)])
            if document_folder:
                for att in attach_document_ids:
                    document = document_obj.create({
                        'name': self.name,
                        'folder_id': document_folder.id,
                        'attachment_id': att.id,
                        'memo_category_id': self.memo_category_id.id,
                        'owner_id': self.env.user.id,
                        'is_shared': True,
                        'submitted_date': fields.Date.today(),
                    })
                    document_folder.update({'document_ids': [(4, document.id)]})
                document_folder.update_next_occurrence_date()
            else:
                raise ValidationError("""
                                      Ops! No documentation folder setup available for the requester department. 
                                      Contact admin to configure """
                                      )

    def generate_employee_update_request(self, body_msg=False):
        employee_ids = [rec.employee_id.id for rec in self.employee_transfer_line_ids]
        return {
              'name': 'Employee Transfer',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'hr.employee.transfer',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_employee_ids': employee_ids,
                  'default_employee_transfer_lines': self.employee_transfer_line_ids.ids
              },
        }

    def generate_stock_material_request(self, body_msg, body):
        stock_picking_type_out = self.env.ref('stock.picking_type_out')
        stock_picking = self.env['stock.picking']
        existing_picking = stock_picking.search([('memo_id', '=', self.id)], limit=1)
        user = self.env.user
        warehouse_location_id = self.env['stock.warehouse'].search([
            ('company_id', '=', user.company_id.id) 
        ], limit=1)
        destination_location_id = self.env.ref('stock.stock_location_customers')
        if not existing_picking:
            vals = {
                'scheduled_date': fields.Date.today(),
                'picking_type_id': stock_picking_type_out.id,
                'origin': self.code,
                'memo_id': self.id,
                'partner_id': self.employee_id.user_id.partner_id.id,
                'move_ids_without_package': [(0, 0, {
                                'name': self.code, 
                                'picking_type_id': stock_picking_type_out.id,
                                'location_id': mm.source_location_id.id or warehouse_location_id.lot_stock_id.id,
                                'location_dest_id': destination_location_id.id,
                                'product_id': mm.product_id.id,
                                'product_uom_qty': mm.quantity_available,
                                'date_deadline': self.date_deadline,
                }) for mm in self.product_ids]
            }
            stock = stock_picking.sudo().create(vals)
        else:
            stock = existing_picking
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            """Check if the user is enlisted as the approver for memo type"""
            view_id = self.env.ref('stock.view_picking_form').id
            ret = {
                'name': "Stock Request",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'stock.picking',
                'res_id': stock.id,
                'type': 'ir.actions.act_window',
                'domain': [],
                'target': 'current'
                }
            return ret

    def generate_stock_procurement_request(self, body_msg, body):
        """
        Check po record if already create, popup the wizard, 
        else create pO and pop up the wizard
        """
        stock_picking_type_in = self.env.ref('stock.picking_type_in')
        purchase_obj = self.env['purchase.order']
        existing_po = purchase_obj.search([('memo_id', '=', self.id)], limit=1)
        if not existing_po:
            vals = {
                'date_order': self.date,
                'picking_type_id': stock_picking_type_in.id,
                'origin': self.code,
                'memo_id': self.id,
                'partner_id': self.employee_id.user_id.partner_id.id,
                'order_line': [(0, 0, {
                                'product_id': mm.product_id.id,
                                'name': mm.description or f'{mm.product_id.name} Requistion',
                                'product_qty': mm.quantity_available,
                                'price_unit': mm.amount_total,
                                'date_planned': self.date,
                }) for mm in self.product_ids]
            }
            po = purchase_obj.create(vals)
        else:
            po = existing_po
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            """Check if the user is enlisted as the approver for memo type"""
            self.follower_messages(body)
            view_id = self.env.ref('purchase.purchase_order_form').id
            ret = {
                'name': "Purchase Order",
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': 'purchase.order',
                'res_id': po.id,
                'type': 'ir.actions.act_window',
                'domain': [],
                'target': 'new'
                }
            return ret
            
    def view_parent_project(self):
        if not self.project_memo_id:
            raise ValidationError('No related project found for this Record')
        view_id = self.env.ref('company_memo.memo_model_form_view_3').id
        ret = {
            'name': "Parent Project",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'memo.model',
            'res_id': self.project_memo_id.id,
            'type': 'ir.actions.act_window',
            'target': 'new'
            }
        return ret
    
    def action_validate_cargo_line(self):
        if not self.picking_type_id:
            raise ValidationError("Please provide operation type id")
        for rec in self.logistic_item_ids:
            if not rec.product_id:
                raise ValidationError("Please provide a product")
        
            if not rec.source_location_id:
                raise ValidationError("Please provide source location id")
            if not rec.destination_location_id:
                raise ValidationError("Please provide destination id")
            
        vals = {
                'scheduled_date': fields.Date.today(),
                'picking_type_id': self.picking_type_id.id,
                'origin': self.code,
                'memo_id': self.id,
                'partner_id': self.client_id.id,
                'move_ids_without_package': [(0, 0, {
                                'name': self.code, 
                                'picking_type_id': li.picking_type_id.id,
                                'location_id': li.source_location_id.id,
                                'location_dest_id': li.destination_location_id.id,
                                'product_id': li.product_id.id,
                                'product_uom_qty': li.quantity_to_move,
                                'date_deadline': fields.Date.today(),
                            }) for li in self.logistic_item_ids]
            }
        stock_picking = self.env['stock.picking'].create(vals)
        self.stock_picking_id = stock_picking.id 
       
    def generate_vehicle_request(self, body_msg):
        # TODO: generate fleet asset
        self.state = 'Done'
        self.is_request_completed = True
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)

    def generate_payment_request(self, body_msg):
        if self.invoice_ids:
            invoice_without_payment = self.mapped('invoice_ids').filtered(
                lambda se: se.payment_state not in ['paid', 'partial', 'in_payment'])
            if invoice_without_payment:
                raise ValidationError(
                    """Kindly click each of the invoice line to ensure payments are posted and payments registered manually to avoid errors
                    """)
        elif self.payment_ids:
            payment_without_post = self.mapped('payment_ids').filtered(
                lambda se: se.state not in ['posted'])
            if payment_without_post:
                raise ValidationError(
                    """Kindly click each of the payment lines to ensure payments are posted manually to avoid errors
                """)
        elif self.contractor_ids:
            contractor_ids = self.mapped('contractor_ids')
            for pnp in contractor_ids:
                payment_without_post = pnp.mapped('payment_ids').filtered(
                    lambda se: se.state not in ['posted'])
                if payment_without_post:
                    raise ValidationError(
                        """Kindly click each of the contractor lines to ensure payments are posted manually to avoid errors
                    """)
        else:
            raise ValidationError("No payment/Contractors to validate")
        self.state = 'Done'
        self.is_request_completed = True
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)

    def generate_recruitment_request(self, body_msg=False):
        """
        Create HR job application ready for publication 
        """
        recruitment_request_obj = self.env['hr.job.recruitment.request']
        existing_hrr = recruitment_request_obj.search([
            ('memo_id', '=', self.id),
            ], limit=1)
        if not existing_hrr:
            vals = {
                'job_tmp': self.job_tmp,
                'department_id': self.requested_department_id.id,
                'name': self.name,
                'memo_id': self.id,
                'recruitment_mode': self.recruitment_mode,
                'job_id': self.job_id.id,
                'user_id': self.employee_id.user_id.id,
                'user_to_approve_id': random.choice([r.user_id.id for r in self.stage_id.approver_ids]),
                'expected_employees': self.expected_employees,
                'recommended_by': self.recommended_by.user_id.id,
                'description': BeautifulSoup(self.description or "-", features="lxml").get_text(),
                'requirements': self.qualification,
                'age_required': self.age_required,
                'years_of_experience': self.years_of_experience,
                'state': 'confirmed',
                'date_expected': self.date_expected,
                'date_accepted': fields.Date.today(),
                'date_confirmed': fields.Date.today(),
            }
            rr_id = recruitment_request_obj.create(vals)
        else:
            rr_id = existing_hrr
        self.update_memo_type_approver()
        if body_msg:
            self.mail_sending_direct(body_msg)
        self.state = 'Done'
        """Check if the user is enlisted as the approver for memo type"""
        view_id = self.env.ref('hr_cbt_portal_recruitment.hr_job_recruitment_request_form_view').id
        ret = {
            'name': "Recruitment request",
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'hr.job.recruitment.request',
            'res_id': rr_id.id,
            'type': 'ir.actions.act_window',
            'domain': [],
            'target': 'current'
            }
        return ret

    def generate_leave_request(self, body_msg, body):
        leave = self.env['hr.leave'].sudo()
        vals = {
            'employee_id': self.employee_id.id,
            'request_date_from': self.leave_start_date,
            'request_date_to': self.leave_end_date,
            'name': BeautifulSoup(self.description or "Leave request", features="lxml").get_text(),
            'holiday_status_id': self.leave_type_id.id,
            'origin': self.code,
            'memo_id': self.id,
        }
        leave_id = leave.create(vals)
        leave_id.action_approve()
        leave_id.action_validate()
        self.state = 'Done'
        self.mail_sending_direct(body_msg)

    def generate_move_entries(self):
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
            """Check if the user is enlisted as the approver for memo type
            if approver is an account officer, system generates move and open the exact record"""
            view_id = self.env.ref('account.view_move_form').id
            # move_id = self.generate_move_entries()
            journal_id = self.env['account.journal'].search(
            [('type', '=', 'purchase'),
             ('code', '=', 'BILL')
             ], limit=1)
            account_move = self.env['account.move'].sudo()
            inv = account_move.search([('memo_id', '=', self.id)], limit=1)
            if not inv:
                partner_id = self.employee_id.user_id.partner_id
                inv = account_move.create({ 
                    'memo_id': self.id,
                    'ref': self.code,
                    'origin': self.code,
                    'partner_id': partner_id.id,
                    'company_id': self.env.user.company_id.id,
                    'currency_id': self.env.user.company_id.currency_id.id,
                    # Do not set default name to account move name, because it
                    # is unique 
                    # 'name': f"CADV/ {self.code}",
                    'move_type': 'in_receipt',
                    'invoice_date': fields.Date.today(),
                    'date': fields.Date.today(),
                    'journal_id': journal_id.id,
                    'invoice_line_ids': [(0, 0, {
                            'name': pr.product_id.name if pr.product_id else pr.description,
                            'ref': f'{self.code}: {pr.product_id.name or pr.description}',
                            'account_id': pr.product_id.property_account_expense_id.id or pr.product_id.categ_id.property_account_expense_categ_id.id if pr.product_id else journal_id.default_account_id.id,
                            'price_unit': pr.amount_total,
                            'quantity': pr.quantity_available,
                            'discount': 0.0,
                            'code': pr.code,
                            'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
                            'product_id': pr.product_id.id if pr.product_id else None,
                    }) for pr in self.product_ids],
                })
            self.move_id = inv.id
            self.state = "Done"
            self.update_final_state_and_approver()
            return self.record_to_open(
            "account.move", 
            view_id,
            inv.id,
            f"Journal Entry - {inv.name}"
            ) 
        else:
            raise ValidationError("Sorry! You are not allowed to validate cash advance payments")
        
    def generate_soe_entries(self):
        is_config_approver = self.determine_if_user_is_config_approver()
        if is_config_approver:
             
            """Check if the user is enlisted as the approver for memo type
            if approver is an account officer, system generates move and open the exact record"""
            view_id = self.env.ref('account.view_move_form').id
            journal_id = self.env['account.journal'].search(
            [('type', '=', 'sale'),
             ('code', '=', 'INV')
             ], limit=1)
            # 5000 - 3000
            account_move = self.env['account.move'].sudo()
            inv = account_move.search([('memo_id', '=', self.id)], limit=1)
            if not inv:
                partner_id = self.employee_id.user_id.partner_id
                inv = account_move.create({ 
                    'memo_id': self.id,
                    'ref': self.code,
                    'origin': self.code,
                    'partner_id': partner_id.id,
                    'company_id': self.env.user.company_id.id,
                    'currency_id': self.env.user.company_id.currency_id.id,
                    # Do not set default name to account move name, because it
                    # is unique 
                    'name': f"SOE {self.code}",
                    'move_type': 'out_receipt',
                    'invoice_date': fields.Date.today(),
                    'date': fields.Date.today(),
                    'journal_id': journal_id.id,
                    'invoice_line_ids': [(0, 0, {
                            'name': pr.product_id.name if pr.product_id else pr.description,
                            'ref': f'{self.code}: {pr.product_id.name}',
                            'account_id': pr.product_id.property_account_income_id.id or pr.product_id.categ_id.property_account_income_categ_id.id if pr.product_id else journal_id.default_account_id.id,
                            'price_unit': pr.used_amount,
                            'quantity': pr.used_qty,
                            'discount': 0.0,
                            'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
                            'product_id': pr.product_id.id if pr.product_id else None,
                    }) for pr in self.product_ids],
                })
                for pr in self.mapped('product_ids').filtered(lambda x: x.to_retire):
                    cash_advance_amount = self.env['account.move.line'].search([
                        ('code', '=', pr.code)
                        ], limit=1) # locating the existing cash_advance_line to get the initial request amount
                    if cash_advance_amount:
                        approved_cash_advance_amount = cash_advance_amount.price_unit
                        balance_remaining = approved_cash_advance_amount - pr.used_amount # e.g 5000 - 3000 = 2000
                        inv.invoice_line_ids = [(0, 0, {
                                'name': pr.product_id.name if pr.product_id else pr.description,
                                'ref': f'{self.code}: {pr.product_id.name}',
                                'account_id': pr.product_id.property_account_income_id.id or pr.product_id.categ_id.property_account_income_categ_id.id if pr.product_id else journal_id.default_account_id.id,
                                'price_unit': balance_remaining, # pr.used_total,
                                'quantity': pr.used_qty,
                                'discount': 0.0,
                                'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
                                'product_id': pr.product_id.id if pr.product_id else None,
                        })]
                        pr.update({'retired': True}) # updating the Line as retired
            self.update_inventory_product_quantity()
            self.state = "Done"
            self.update_final_state_and_approver()
            return self.record_to_open(
            "account.move", 
            view_id,
            inv.id,
            f"Journal Entry SOE - {inv.name}"
            ) 
        else:
            raise ValidationError("Sorry! You are not allowed to validate cash advance payments")
         
    def record_to_open(self, model, view_id, res_id=False, name=False):
        obj = self.env[f'{model}'].search([('origin', '=', self.code)], limit=1)
        if obj:
            return self.open_related_record_view(
                model, 
                res_id if res_id else obj.id ,
                view_id,
                name if name else f"{obj.name}"
            )
        else:
            raise ValidationError("No related record found for the memo")

    def update_inventory_product_quantity(self):
        '''this will be used to raise a stock tranfer record. Once someone claimed he returned a 
         positive product (storable product) , 
         system should generate a stock picking to update the new product stock
         if product does not exist, To be asked for '''
        stock_picking_type_out = self.env.ref('stock.picking_type_out')
        stock_picking = self.env['stock.picking']
        user = self.env.user
        warehouse_location_id = self.env['stock.warehouse'].search([
            ('company_id', '=', user.company_id.id) 
        ], limit=1)
        partner_location_id = self.env.ref('stock.stock_location_customers')
        vals = {
            'scheduled_date': fields.Date.today(),
            'picking_type_id': stock_picking_type_out.id,
            'origin': self.code,
            'partner_id': self.employee_id.user_id.partner_id.id,
            'move_ids_without_package': [(0, 0, {
                            'name': self.code, 
                            'picking_type_id': stock_picking_type_out.id,
                            'location_id': partner_location_id.id,
                            'location_dest_id': mm.source_location_id.id or warehouse_location_id.lot_stock_id.id,
                            'product_id': mm.product_id.id,
                            'product_uom_qty': mm.quantity_available,
                            'date_deadline': self.date_deadline,
            }) for mm in self.mapped('product_ids').filtered(
                lambda pr: pr.product_id and pr.product_id.detailed_type == "product" and pr.to_retire == True)]
        }
        stock_picking.sudo().create(vals)

    def open_related_record_view(self, model, res_id, view_id, name="Record To approved"):
        ret = {
                'name': name,
                'view_mode': 'form',
                'view_id': view_id,
                'view_type': 'form',
                'res_model': model,
                'res_id': res_id,
                'type': 'ir.actions.act_window',
                'domain': [],
                'target': 'current'
                }
        return ret

    def update_memo_type_approver(self):
        """update memo type approver"""
        memo_settings = self.env['memo.config'].sudo().search([
                ('memo_type', '=', self.memo_type.id),
                ('department_id', '=', self.employee_id.department_id.id)
                ])
        memo_approver_ids = memo_settings.approver_ids
        for appr in memo_approver_ids:
            self.sudo().write({
                'users_followers': [(4, appr.id)] 
            })
      
    def view_related_record(self):
        if self.memo_type.memo_key == "material_request":
            view_id = self.env.ref('stock.view_picking_form').id
            return self.record_to_open('stock.picking', view_id)
             
        elif self.memo_type.memo_key == "procurement_request":
            view_id = self.env.ref('purchase.purchase_order_form').id
            return self.record_to_open('purchase.order', view_id)
        elif self.memo_type.memo_key == "vehicle_request":
            pass 
        elif self.memo_type.memo_key == "leave_request":
            view_id = self.env.ref('hr_holidays.hr_leave_view_form').id
            return self.record_to_open('purchase.order', view_id)
        elif self.memo_type.memo_key == "cash_advance":
            view_id = self.env.ref('account.view_move_form').id
            return self.record_to_open('account.move', view_id)
        else:
            pass 

    def follower_messages(self, body):
        pass 
        # body= "RETURN NOTIFICATION;\n %s" %(self.reason_back)
        # body = body
        # records = self._get_followers()
        # followers = records
        # self.message_post(body=body)
        # self.message_post(body=body, 
        # subtype='mt_comment',message_type='notification',partner_ids=followers)
     
    def validate_account_invoices(self):
        if self.external_memo_request and not self.payment_ids:
            '''If external payment transfer, system displays the payment line'''
            raise ValidationError("Please ensure the payment lines are added")
        else:
            not_done = self.mapped('payment_ids').filtered(lambda se: se.state in ['draft'])
            if not_done:
                raise ValidationError("Payments should be posted manually to ensure data accuracy")
        
        if self.is_internal_transfer and not self.invoice_ids:
            '''If external payment transfer, system displays the payment line'''
            raise ValidationError("Please ensure the invoice lines are added")
        else:
            not_done = self.mapped('invoice_ids').filtered(lambda se: se.state in ['draft'])
            if not_done:
                raise ValidationError("Payments should be posted manually to ensure data accuracy")
         
        self.state = 'Done'
        self.is_request_completed = True
        body = "MEMO APPROVE NOTIFICATION: -Approved By ;\n %s on %s" %(self.env.user.name,fields.Date.today())
        type = "request"
        body_msg = f"""Dear {self.employee_id.name}, <br/>I wish to notify you that a {type} with description, '{self.name}',\
                from {self.employee_id.department_id.name} department (MDA: {self.branch_id.name}) have been approved by {self.env.user.name}.<br/>\
                Respective authority should take note. \
                <br/>Kindly {self.get_url(self.id)} <br/>\
                Yours Faithfully<br/>{self.env.user.name}"""
        self.update_final_state_and_approver()
        self.update_memo_type_approver()
        self.mail_sending_direct(body_msg)

        # if not self.is_internal_transfer:
        #     if not self.invoice_ids:
        #         raise ValidationError("Please ensure the invoice lines are added")
        #     else:
        #         invalid_record = self.mapped('invoice_ids').filtered(
        #             lambda s: not s.partner_id or not s.journal_id) # payment_journal_id
        #         if invalid_record:
        #             raise ValidationError("""
        #                                   Partner, Payment journal must be selected. 
        #                                   Also ensure the status is in draft""")
        
        # else:
        #     if not self.payment_ids or self.invoice_ids:
        #         raise ValidationError("Please ensure the payment lines are added")
        #     '''If internal payment transfer, system displays the payment line'''
        #     nodone = self.mapped('payment_ids').filtered(lambda se: se.state in ['draft'])
        #     if nodone:
        #         raise ValidationError("Payments should be handled manually to ensure accuracy")
        #     else:
        #         self.state = 'Done'

                
    def action_post_and_vallidate_payment(self): # Register Payment
        self.validate_account_invoices()
 
    def get_payment_method_line_id(self, payment_type, journal_id):
            if journal_id:
                available_payment_method_lines = journal_id._get_available_payment_method_lines(payment_type)
            else:
                available_payment_method_lines = False
            # Select the first available one by default.
            if available_payment_method_lines:
                payment_method_line_id = available_payment_method_lines[0]._origin
            else:
                payment_method_line_id = False
            return payment_method_line_id
            
    def validate_invoice_and_post_journal(
            self, journal_id, inv): 
            """To be used only when they request for automatic payment generation"""
            account_payment = self.env['account.payment'].sudo()
            outbound_payment_method = self.env['account.payment.method'].sudo().search(
                [('code', '=', 'manual'), ('payment_type', '=', 'outbound')], limit=1)
            payment_method = 2
            if journal_id:
                payment_method = journal_id.outbound_payment_method_line_ids[0].id if \
                    journal_id.outbound_payment_method_line_ids else outbound_payment_method.id \
                        if outbound_payment_method else payment_method
                
            payment_method_line_id = self.get_payment_method_line_id('outbound', journal_id)
            payment_vals = {
                'date': fields.Date.today(),
                'amount': inv.amount_total,
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'ref': inv.name,
                'move_id': inv.id,
                'journal_id': 8, #inv.payment_journal_id.id,
                'currency_id': inv.currency_id.id,
                'partner_id': inv.partner_id.id,
                'destination_account_id': inv.line_ids[1].account_id.id,
                'payment_method_line_id': payment_method, #payment_method_line_id.id if payment_method_line_id else payment_method,
            }
            payments = self.env['account.payment'].create(payment_vals)
            payments.action_post()

    def Register_Payment(self):
        if self.env.uid in [r.user_id.id for r in self.stage_id.approver_ids]:
            raise ValidationError(
                """You are not Permitted to approve this Memo. Contact the authorized Person
            """)
        view_id = self.env.ref('account.view_account_payment_form')
        if (self.memo_type.memo_key != "Payment") or (self.amountfig < 1):
            raise ValidationError("(1) Memo type must be 'Payment'\n (2) Amount must be greater than one to proceed with payment")
        account_payment_existing = self.env['account.payment'].search([
            ('memo_reference', '=', self.id)
            ], limit=1)
        vals = {
                'name':'Memo Payment',
                'view_mode': 'form',
                'view_id': view_id.id,
                'view_type': 'form',
                'res_model': 'account.payment',
                'type': 'ir.actions.act_window',
                'target': 'current'
                }
        if not account_payment_existing:
            vals.update({
                'context': {
                        'default_amount': self.amountfig,
                        'default_payment_type': 'outbound',
                        'default_partner_id':self.vendor_id.id or self.employee_id.user_id.partner_id.id, 
                        'default_memo_reference': self.id,
                        'default_communication': self.name,
                },
                'domain': [],
            })
        else:
            vals.update({
                'res_id': account_payment_existing.id
            })
        return vals

    def generate_loan_entries(self):
        pass
        # if self.loan_reference:
        #     raise ValidationError("You have generated a loan already for this record")
        # view_id = self.env.ref('account_loan.account_loan_form')
        # if (self.memo_type.memo_key != "loan") or (self.loan_amount < 1):
        #     raise ValidationError("Check validation: \n (1) Memo type must be 'loan request'\n (2) Loan Amount must be greater than one to proceed with loan request")
        # ret = {
        #     'name':'Generate loan request',
        #     'view_mode': 'form',
        #     'view_id': view_id.id,
        #     'view_type': 'form',
        #     'res_model': 'account.loan',
        #     'type': 'ir.actions.act_window',
        #     'domain': [],
        #     'context': {
        #             'default_loan_type': self.loan_type,
        #             'default_loan_amount': self.loan_amount,
        #             'default_periods':self.periods or 12,  
        #             'default_partner_id':self.employee_id.user_id.partner_id.id,  
        #             'default_method_period':self.method_period,  
        #             'default_rate': 15, 
        #             'default_start_date':self.start_date, 
        #             'default_name': self.code,
        #     },
        #     'target': 'current'
        #     }
        # return ret

    def migrate_records(self):
        account_ref = self.env['account.payment'].search([])
        for rec in account_ref:
            memo_rec = self.env['memo.model'].search([('code', '=', rec.communication)])
            if memo_rec:
                memo_rec.state = "Done"
        
    def return_memo(self):
        msg = "You have initially forwarded this memo. Kindly use the cancel button or wait for approval"
        self.return_validator()
        default_sender = self.mapped('res_users')
        last_sender = self.env['hr.employee'].search([('user_id', '=', default_sender[-1].id)]).id if default_sender else False
        return {
              'name': 'Reason for Return',
              'view_type': 'form',
              "view_mode": 'form',
              'res_model': 'memo.back',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': {
                  'default_memo_record': self.id,
                  'default_date': self.date,
                  'default_direct_employee_id': last_sender,
                  'default_resp':self.env.uid,
              },
        }
    
    @api.depends('state')
    # Depending on any field change (ORM or Form), the function is triggered.
    def _progress_state(self):
        for order in self:
            if order.state in ["submit", "Refuse"]:
                order.status_progress = random.randint(0, 5)
            elif order.state == "Sent":
                order.status_progress = random.randint(30, 40)
            elif order.state == "Approve":
                order.status_progress = random.randint(90, 95)
            elif order.state == "Approve2":
                order.status_progress = random.randint(90, 95)
            elif order.state == "Done":
                order.status_progress = random.randint(99, 100)
            else:
                order.status_progress = random.randint(0, 1) # 100 / len(order.state)
    
    @api.model
    def _cron_notify_server_request_followers(self):
        """
        System should check all requests end date expired, and send message
        to server admin or followers. 
        """
        expired_memos = self.env['memo.model'].search([
            ('request_end_date', '<', fields.Datetime.now()),
            ('expiry_mail_sent', '=', False),
            ('memo_type', '=', 'server_access'),
            ])
        for exp in expired_memos:
            if exp.memo_setting_id and exp.memo_setting_id.approver_ids:
                body_msg = f"""Dear Sir, \n \
                    <br/>I wish to notify you that a server access request with description, {exp.name},<br/>  
                    from {exp.employee_id.name} \
                    has now expired. <br/> <br/>Go to the request {self.get_url(exp.id)} \
                """
                exp.mail_sending_direct(body_msg)
                exp.expiry_mail_sent = True

    def unlink(self):
        sys_admin = self.env.user.has_group("base.group_system")
        assessed_user = self.create_uid.id == self.env.uid or sys_admin
        for delete in self: # .filtered(lambda delete: delete.state in ['Sent','Approve2', 'Approve']):
            if delete.state == 'submit':
                if not assessed_user: 
                    raise ValidationError("You cannot delete request not created by you")
            elif delete.state in ['Sent','Approve2', 'Approve', 'Done']:
                raise ValidationError(_('You cannot delete a Memo which is in %s state.') % (delete.state,))
        return super(Memo_Model, self).unlink()


class MemoFrameAgreement(models.Model):
    _name = "memo.frame.agreement"

    name = fields.Char("Name", required=True)
    active = fields.Boolean("Active", required=False, default=True)
    code = fields.Char("Code", required=False)
    memo_id = fields.Many2one(
        "memo.model", 
        string="Project Ref"
        )
    client_ids = fields.Many2many(
        "res.partner", 
        "frame_agreement_partner_rel",
        "frame_agreement_id",
        "partner_id",
        string="Clients"
        )
    currency_id = fields.Many2one(
        "res.currency", 
        string="Currency"
        )
    agreed_budget = fields.Float("Max Budget", required=False)
    description = fields.Char("Description", required=False)
    
    @api.model
    def create(self, vals):
        code = self.env['ir.sequence'].next_by_code('memo-frame-agreement')
        vals['code'] = code
        result = super(MemoFrameAgreement, self).create(vals)
        return result
