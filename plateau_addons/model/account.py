from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


import logging

_logger = logging.getLogger(__name__)


class accountPublicSegment(models.Model):
    _name = "account.public.segment"

    name = fields.Char(string='Segment')
    code = fields.Char(string='Code')
    active = fields.Boolean(string='Active')
    account_segment_ids = fields.Many2many(
        'account.account',
         'account_account_segment_rel',
          'account_segment_id',
           'account_id', 
           string='Account Segment'
           )
    account_branch_ids = fields.Many2many(
        'multi.branch',
         'account_branch_segment_rel',
          'account_branch_id',
           'branch_id', 
           string='MDAs'
           )
    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Other Recurrent"),
            ("asset_current", "Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Liability"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "REVENUE"),
            ("income_other", "Other Income"),
            ("expense", "Expenditure"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string='Account Type',
        tracking=True,
        store=True,
        default="asset_cash"
    )


class accountAccount(models.Model):
    _inherit = "account.account"

    account_segment_id = fields.Many2one('account.public.segment', string='Account Segment')

class accountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    code = fields.Char(string='Code')
    

class accountJournal(models.Model):
    _inherit = "account.journal"
    
    for_public_use = fields.Boolean(string="For Public user")
    
    code = fields.Char(
        string='Short Code',
        size=20, 
        required=True, 
        help="Shorter name used for display. The journal entries of this journal will also be named using this prefix by default.")
     
    def _get_internal_users_ids(self):
        Group = self.env['res.groups']
        group_roles = self.env.ref('ik_multi_branch.account_major_user').id
        users = Group.browse([group_roles]).users
        return users and users.ids or []
    
    def get_filtered_journal_record(self):
        view_id_form = self.env.ref('account.view_account_journal_form')
        view_id_tree = self.env.ref('account.view_account_journal_tree')
        view_id_kanban = self.env.ref('account.account_journal_dashboard_kanban_view')
        user = self.env.user
        allowed_internal_users = self._get_internal_users_ids()
        record_ids = []
        if user.id in allowed_internal_users: 
            return {
                'type': 'ir.actions.act_window',
                'name': _('Journals'),
                'res_model': 'account.journal',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'view_id': view_id_kanban.id,
                'views': [(view_id_kanban.id, 'kanban'), (view_id_tree.id, 'tree'), (view_id_form.id,'form')],
                'target': 'current',
                'domain': []
            }
        else:
            
            domain = [
                ('for_public_use', '=', False), 
                # ('branch_id', '=', user.branch_id.id),
                ('branch_id', 'in', user.branch_id.ids),
                # ('create_uid','=', user.id),
            ]
            non_user_journals = self.env['account.journal'].sudo().search(domain)
            record_ids = [res.id for res in non_user_journals]
            return {
                'type': 'ir.actions.act_window',
                'name': _('Journals'),
                'res_model': 'account.journal',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'view_id': view_id_kanban.id,
                'views': [(view_id_kanban.id, 'kanban'), (view_id_tree.id, 'tree'), (view_id_form.id,'form')],
                'target': 'current',
                'domain': [('id', 'in', record_ids)]
            } 
        
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    external_memo_request = fields.Boolean(string='External request')
    is_top_account_user = fields.Boolean('Is top account user?', compute="compute_top_account_user")
    suitable_journal_ids = fields.Many2many('account.journal', compute='_compute_suitable_journal_ids')
    destination_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Destination Journal',
        domain="[('id', 'in', suitable_journal_ids)]",
        check_company=True,
    )
    request_mda_from = fields.Many2one('multi.branch', string='Requesting From MDA?')

    # domain="[('type', 'in', ('bank','cash')), ('company_id', '=', company_id), ('id', '!=', journal_id)]",

    # payment_journal_id = fields.Many2one(
    #     'account.journal', 
    #     string="Payment Journal", 
    #     required=False,
    #     domain="[('id', 'in', suitable_journal_ids)]"
    #     )

    @api.depends('external_memo_request')
    def compute_top_account_user(self):
        for rec in self:
            account_major_user = (self.env.is_admin() or self.env.user.has_group('ik_multi_branch.account_major_user'))
            if rec.external_memo_request and account_major_user:
                rec.is_top_account_user = True
            else:
                rec.is_top_account_user = False

    @api.constrains('amount')
    def check_amount(self):
        if self.amount <= 0:
            raise ValidationError('Amount must be greater than 0 !!!')

    def action_post(self):
        account_major_user = (self.env.is_admin() or self.env.user.has_group('ik_multi_branch.account_major_user'))
        # if self.memo_reference:
        #     # if not self.memo_reference.stage_id.is_approved_stage:
        #     #     raise ValidationError("Ops. You are not allowed confirm this Bill at this stage")
        #     if self.memo_reference.stage_id.is_approved_stage and self.env.user.id not in [r.user_id.id for r in self.memo_reference.stage_id.approver_ids]: 
        #         # if self.external_memo_request and not account_major_user or if self.memo_id.stage_id.approver_ids.ids :
        #         raise ValidationError("Ops. You are not allowed confirm this Bill. Ensure system admin adds you to the list approvers for this stage")
        # else:
        #     raise ValidationError("ddddEnsure system admin adds you to the lithis stage")
        if self.memo_reference:
            stage = self.memo_reference.stage_id
            approval_users = [r.user_id.id for r in stage.approver_ids]
            if self.env.user.id not in approval_users:
                raise ValidationError(f"Only these users are allowed to post at this stage {[rec.name for rec in stage.approver_ids]}")
        res = super(AccountPayment, self).action_post()
        return res
    
    @api.depends('company_id')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            Journals = self.env['account.journal'].sudo()
            domain = [
                ('company_id', '=', company_id), 
                ('type', 'in', ('bank','cash')),
                ('id', '!=', m.journal_id.id),
                ]
                
            account_major_user = (self.env.is_admin() or self.env.user.has_group('ik_multi_branch.account_major_user'))
            branch_ids = [rec.id for rec in self.env.user.branch_ids if rec] + [self.env.user.branch_id.id]
            journal_ids = []
            Journal_Search =Journals.search([])
            
            for journal in Journal_Search:
                 
                journal_branches = [rec.id for rec in journal.allowed_branch_ids] + [journal.branch_id.id]
                if set(branch_ids).intersection(set(journal_branches)):
                    journal_ids.append(journal.id)
                
                if journal.for_public_use:
                    journal_ids.append(journal.id)
                 
            if account_major_user:
                domain = domain 
            else:
                # journal_ids = journal_ids.remove(self.journal_id.id) # removed the id of already selected journal id
                domain = [
                    ('company_id', '=', company_id),
                    ('type', 'in', ('bank','cash')),
                    ('id', 'in', journal_ids),
                    ]

            m.suitable_journal_ids = self.env['account.journal'].search(domain)

   
class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'
    
    ng_budget_line_id = fields.Many2one(
        'ng.account.budget.line',
        string='Budget',
        readonly=False,
        tracking=True,
        ondelete='restrict')
    
    ng_budget_line_ids = fields.Many2many(
        'ng.account.budget.line',
        string='Budget Tag',
        readonly=False,
        compute="_compute_ng_budget_line")
    
    budget_balance = fields.Float('Budget Balance', related="ng_budget_line_id.budget_balance")
    
    @api.depends('account_id')
    def _compute_ng_budget_line(self):
        user = self.env.user
        # if user.branch_id or user.branch_ids:
            # for m in self:
        if self.account_id:
            budget_line_ids = self.env['ng.account.budget.line'].search([
            ('branch_id', '=', self.branch_id.id),
            # ('account_id', '=', self.account_id.id)
            ])
            if budget_line_ids:
                self.ng_budget_line_ids = [(6, 0, budget_line_ids.ids)]
            else:
                self.ng_budget_line_ids = False
        else:
            self.ng_budget_line_ids = False
         
                
    # @api.model
    # def default_get(self, fields):
    #     res = super(Memo_Model, self).default_get(fields)
    #     memo_project_type = self.env.context.get('default_memo_project_type')
    #     default_budget_allocation = self.env.context.get('default_is_budget_allocation_request')
    #     external_payment_request = self.env.context.get('default_external_memo_request')
        
    #     ministry_of_finance = self.env.ref('plateau_addons.mda_ministry_of_finance')
    #     # finance_budget_head = self.env['ng.budget'].search(domain)
    #     # user_branches = list(self.env.user.branch_id.id)
    #     domain = [('active', '=', True)]
    #     # if memo_project_type: , ('branch_ids', 'in', user_branches)
    #     #     domain = [('active', '=', True), ('project_type', '=', memo_project_type)]
    #     memo_configs = self.env['memo.config'].search(domain)
    #     user_branch_id = self.env.user.branch_id
    #     res.update({
    #         'dummy_memo_types': [(6, 0, [rec.memo_type.id for rec in memo_configs if user_branch_id.id in rec.branch_ids.ids])],
    #         'dummy_budget_ids': [(6, 0, [rec.id for rec in self.env['ng.account.budget'].search([
    #             '|', ('branch_id', '=', self.env.user.branch_id.id),
    #             ('branch_id', 'in', self.env.user.branch_ids.ids)])
    #                                      ])],
    #         'request_mda_from': ministry_of_finance.id if default_budget_allocation or external_payment_request else False,
    #         'request_mda_from': ministry_of_finance.id if default_budget_allocation or external_payment_request else False,
    #         })
    #     return res
         
class AccountInvoice(models.Model):
    _inherit = 'account.move'
     
    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain or 'general'
            company_id = m.company_id.id or self.env.company.id
            Journals = self.env['account.journal'].sudo()
            account_major_user = (self.env.is_admin() or self.env.user.has_group('ik_multi_branch.account_major_user'))
            domain = [('company_id', '=', company_id), ('type', '=', journal_type)]
            branch_ids = [rec.id for rec in self.env.user.branch_ids if rec] + [self.env.user.branch_id.id]
            journal_ids = []
            for journal in Journals.search([]):
                journal_branches = [rec.id for rec in journal.allowed_branch_ids] + [journal.branch_id.id]
                if set(branch_ids).intersection(set(journal_branches)):
                    journal_ids.append(journal.id)
                 
                if journal.for_public_use:
                    journal_ids.append(journal.id)
            if account_major_user:
                domain = [
                ('company_id', '=', company_id),
                ('type', '=', journal_type),
                ]
            else:
                domain = [
                    ('company_id', '=', company_id),
                    ('type', '=', journal_type),
                    ('id', 'in', journal_ids)
                ]

            m.suitable_journal_ids = self.env['account.journal'].search(domain)

    external_memo_request = fields.Boolean('Is external memo request?')
    is_top_account_user = fields.Boolean('Is top account user?') #, compute="compute_top_account_user")
    budget_id = fields.Many2one(
        'ng.account.budget',
        string='Budget',
        readonly=False,
        tracking=True
        )
    dummy_budget_ids = fields.Many2many(
        'ng.account.budget',
        string='Budget',
        readonly=False,
        compute="_compute_mda_budget")

    @api.depends('company_id')
    def _compute_mda_budget(self):
        user = self.env.user
        # for m in self:
        # if user.branch_id or user.branch_ids:
        if self.branch_id:
            # branches = [rec.id for rec in user.branch_ids] + [user.branch_id.id]
            mda_budget_ids = self.env['ng.account.budget'].search([('branch_id', '=', self.branch_id.id)])
            if mda_budget_ids:
                self.dummy_budget_ids = mda_budget_ids
            else:
                self.dummy_budget_ids = False
        else:
            self.dummy_budget_ids = False
            
    partner_id = fields.Many2one(
        'res.partner',
        string='Beneficiary',
        readonly=True,
        tracking=True,
        inverse='_inverse_partner_id',
        check_company=True,
        change_default=True,
        ondelete='restrict',
    )
    # @api.depends('move_type')
    # def compute_top_account_user(self):
    #     for rec in self:
    #         if (self.env.is_admin() or self.env.user.has_group('ik_multi_branch.account_major_user')):
    #             rec.is_top_account_user = True
    #             rec.external_memo_request = False
    #         else:
    #             rec.is_top_account_user = False
    #             rec.external_memo_request = True

    # def check_budget_limit(self):
    #     # check analytic account - 
    #     # under budget lines, check the positions that contains the the selected chart of account and the budget line is on negative (for expenses)
    #     # if so, check the used amount on that line for that period,  if it exceeds, then raise a validationError.
    #     for rec in self.invoice_line_ids:
    #         _logger.info(rec.analytic_distribution)
    #         raise ValidationError(rec.analytic_distribution)
    
    def cancel_budget_utilized_amount(self):
        #  
        for rec in self.invoice_line_ids:
            if rec.ng_budget_line_id and rec.ng_budget_line_id.utilized_amount > 0:
                rec.ng_budget_line_id.utilized_amount -= rec.price_subtotal
                    
    def check_budget_limit_and_post(self):
        if self.ng_budget_id:
            '''Check if budget head is selected and computes total of 
            each budget against the budget balance
            '''
            already_checked = []
            for rec in self.invoice_line_ids:
                if rec.ng_budget_line_id and rec.ng_budget_line_id.id not in already_checked:
                    budget_invoice_ids = self.mapped('invoice_line_ids').filtered(
                        lambda bd: bd.ng_budget_line_id.id == rec.ng_budget_line_id.id
                    )
                    total_budget, total_balance_budget = 0.00, 0.00
                    for r in budget_invoice_ids:
                        total_balance_budget += r.budget_balance
                        total_budget += r.price_subtotal
                    already_checked.append(rec.ng_budget_line_id.id)
                    if total_budget > rec.budget_balance:
                        raise ValidationError(f"""
                        Your move line with name {rec.name or "N/A"} account 
                        {rec.ng_budget_line_id.economic_id.name or rec.ng_budget_line_id.account_id.name} budget {rec.ng_budget_line_id.economic_id.name or rec.ng_budget_line_id.account_id.name}
                        has sub total amount greater than the Budget - {rec.ng_budget_line_id.economic_id.name or rec.ng_budget_line_id.account_id.name} balance
                                          """)
                    
                    rec.ng_budget_line_id.utilized_amount += total_budget
    
             
    def action_post(self):
        account_major_user = (self.env.is_admin() or self.env.user.has_group('ik_multi_branch.account_major_user'))
        if self.external_memo_request and not account_major_user:
            raise ValidationError("Ops. You are not allowed confirm this Bill. Only Accountant General Group is responsible to do this.")
        self.check_budget_limit_and_post()
        res = super(AccountInvoice, self).action_post()
        return res
    
    def button_cancel(self):
        account_major_user = (self.env.is_admin() or self.env.user.has_group('ik_multi_branch.account_major_user'))
        if self.external_memo_request and not account_major_user:
            raise ValidationError("Ops. You are not allowed cancel this Bill. Only Accountant General Group is responsible to do this.")
        self.cancel_budget_utilized_amount()
        res = super(AccountInvoice, self).action_post()
        return res
    
    def button_register_payment(self):
        account_major_user = (self.env.is_admin() or self.env.user.has_group('ik_multi_branch.account_major_user'))
        if not account_major_user:
            raise ValidationError("""
                                  Ops. You are not allowed pay this Bill. Only Branch/ Accountant General
                                   Group is responsible to do this.""")
        
        view = self.env.ref('account.view_account_payment_form')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context= {
            'default_is_internal_transfer': True,
            'default_amount': self.amount_total,
            'default_payment_type': 'outbound',
            'default_journal_id': False,
            # 'default_move_id': self.id,
            'default_branch_id': self.branch_id.id,
            'default_external_memo_request': True,
        }
        return {
                'name':'Payment transfer',
                'type':'ir.actions.act_window',
                'view_type':'form',
                'res_model':'account.payment',
                'views':[(view.id, 'form')],
                'view_id':view.id,
                'target':'new',
                'context':context,
                }

