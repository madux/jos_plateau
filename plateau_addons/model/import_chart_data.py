from odoo import fields, models ,api, _
from tempfile import TemporaryFile
from odoo.exceptions import UserError, ValidationError, RedirectWarning
import base64
import random
import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta as rd
import xlrd
from xlrd import open_workbook
import base64

_logger = logging.getLogger(__name__)


class accountPayment(models.Model):
    _inherit = "account.payment"


    def action_post(self):
        res = super(accountPayment, self).action_post()
        if self.external_memo_request and self.is_internal_transfer:
            self.create_generate_statement_line()
        return res

    def create_generate_statement_line(self):
        if self.external_memo_request and self.is_internal_transfer:
            # create first statement for negative debit 
            account_bank_statement_line = self.env['account.bank.statement.line'].sudo()
            debit_vals = {
                'journal_id': self.journal_id.id, 
                'amount': -self.amount,
                'payment_ref': self.narration,
                'date': self.date
            }
            credit_vals = {
                'journal_id': self.destination_journal_id.id, 
                'amount': self.amount,
                'payment_ref': self.narration,
                'date': self.date
            }
            account_bank_statement_line.create(debit_vals) 
            account_bank_statement_line.create(credit_vals) 


class accountAccount(models.Model):
    _inherit = "account.account"
    
    is_migrated = fields.Boolean(string="Is migrated")
    ng_budget_lines = fields.One2many('ng.account.budget', 'general_account_id', string='Budget lines')


class ngAccountBudget(models.Model):
    _name = "ng.account.budget"
    _rec_name = "general_journal_id"
    _description = "To hold the budget of accounts and journal"
    
    is_migrated = fields.Boolean(string="Is migrated")
    general_journal_id = fields.Many2one('account.journal', string='Journal')
    general_account_id = fields.Many2one('account.account', string='Account')
    budget_id = fields.Many2one('account.budget.post', string='Budget')
    budget_amount = fields.Float(string="Budget Amount")
    budget_used_amount = fields.Float(string="Utilized Amount")
    budget_variance = fields.Float(string="Budget Variance", compute="compute_variance")
    active = fields.Boolean(string="Active", default=True)
    date_from = fields.Date(string="Date from")
    date_to = fields.Date(string="Date To")
    paid_date = fields.Date(string="Paid Date")
    branch_id = fields.Many2one('multi.branch', string='MDA Sector',required=False)
    move_id = fields.Many2one('account.move', string='Move')

    @api.depends('budget_amount', 'budget_used_amount')
    def compute_variance(self):
        for rec in self:
            if rec.budget_amount and rec.budget_used_amount:
                rec.budget_variance = rec.budget_amount - rec.budget_used_amount
            else:
                rec.budget_variance = False


class accountJournal(models.Model):
    _inherit = "account.journal"
    
    is_migrated = fields.Boolean(string="Is migrated")

class accountAnalytic(models.Model):
    _inherit = "account.analytic.account"
    
    general_journal_id = fields.Many2one('account.journal', string='Journal')
    general_account_id = fields.Many2one('account.account', string='Account')


class crossoveredBudget(models.Model):
    _inherit = "crossovered.budget"
    
    general_journal_id = fields.Many2one('account.journal', string='Journal')
    general_account_id = fields.Many2one('account.account', string='Account')

class crossoveredBudgetLine(models.Model):
    _inherit = "crossovered.budget.lines"
    
    general_journal_id = fields.Many2one('account.journal', string='Journal')
    general_account_id = fields.Many2one('account.account', string='Account')


class ImportPLCharts(models.TransientModel):
    _name = 'pl.import.wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)
    import_type = fields.Selection(
        selection=[
            ("chart", "Chart/Journal Approved Budget"),
            ("transaction", "MDA Account transactions"),
        ],
        string="Import Type", tracking=True,
        required=False, default = "chart"
    )

    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Account Type", tracking=True,
        required=False, default="expense"
    )
    journal_type = fields.Selection(
        selection=[
            ("purchase", "Purchase"),
            ("sale", "Sale"),
            ("bank", "Bank"),
            ("cash", "Cash"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Journal Type", tracking=True,
        required=False,
    )

    default_account = fields.Many2one('account.account', string="Default account")
    running_journal_id = fields.Many2one('account.journal', string="Running Journal")
    budget_id = fields.Many2one('crossovered.budget', string="Budget")
    budget_position_id = fields.Many2one('account.budget.post', string="Budgetary position")
    account_analytic_plan_id = fields.Many2one('account.analytic.plan', string="Analytic account plan", default=lambda self: self.env['account.analytic.plan'].sudo().search([], limit=1))

    def create_update_budget_line(self, account_id, journal_id, branch_id, budget_id, move_id, date_from=False, date_to=False, paid_date=False, budget_amount=0, amount_used=0):
        exist_journal = self.env['ng.account.budget'].search([
            ('general_account_id', '=', account_id),
            ('general_journal_id', '=', journal_id),
            ], limit=1)
        if not exist_journal and budget_amount> 0:
            self.env['ng.account.budget'].create({ 
                'general_journal_id': journal_id, 
                'general_account_id': account_id, 
                'budget_amount': budget_amount, 
                'budget_used_amount': amount_used,
                'branch_id': branch_id.id,
                'move_id': move_id.id if move_id else False, 
                'active': True, 
                'date_from': date_from,
                'date_to': date_to,
                'paid_date': paid_date,
                'budget_id': budget_id.id,
            })
        else:
            exist_journal.update({
                'general_journal_id': journal_id, 
                'general_account_id': account_id,
                'budget_used_amount': exist_journal.budget_used_amount + amount_used, 
                'move_id':  move_id.id if move_id else False,
                'active': True, 
            })

    @api.onchange('running_journal_id')
    def onchange_running_journal(self):
        if self.running_journal_id:
            if not self.running_journal_id.suspense_account_id:
                raise ValidationError("Please ensure that the selected account has a suspense account for external bank transaction")
                
    def create_company(self, name, company_registry):
        if name and company_registry:
            company_obj = self.env['res.company']
            company = company_obj.search([('company_registry', '=', company_registry)], limit=1)
            if not company:
                company = self.env['res.company'].create({
                    'name': name,
                    'company_registry': company_registry,
                })
            return company
        else:
            return None
        
    def generate_analytic_plan(self, partner):
        analytic_account_plan = self.env['account.analytic.plan'].sudo()
        if partner:
            account_existing = analytic_account_plan.search([('code', '=', partner.vat)], limit = 1)
            account = analytic_account_plan.create({
                        "name": partner.name,
                        "code": partner.vat,
                        "default_applicability": 'optional',
                    }) if not account_existing else account_existing
            return account
        else:
            return None

    def create_contact(self, name, code):
        if name and code:
            partner = self.env['res.partner'].search([('vat', '=', code)], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': name,
                    'vat': str(code).replace('.0', ''),
                })
            return partner
        else:
            return None
        
    def create_branch(self, name, code):
        if name and code:
            branch = self.env['multi.branch'].search([('code', '=', code)], limit=1)
            if not branch:
                branch = self.env['multi.branch'].create({
                    'name': name,
                    'code': code,
                })
            return branch
        else:
            return None
        
    def create_analytic_account(self, name, partner, branch, account_id, journal_id, budget_amount):
        analytic_account = self.env['account.analytic.account'].sudo()
        if partner:
            # plan_id = self.generate_analytic_plan(partner)
            account_existing = analytic_account.search([('code', '=',partner.vat)], limit = 1)
            account = analytic_account.create({
                        "name": name or f"{journal_id.code - journal_id.code }", #partner.name.strip().title() +' - '+ partner.vat,
                        "partner_id": partner.id,
                        "branch_id": branch.id,
                        'company_id': self.env.company.id,
                        'general_journal_id': journal_id.id if journal_id else False, 
                        'general_account_id': account_id.id, 
                        'currency_id': self.env.user.company_id.currency_id.id,
                        # "company_id": self.env.user.company_id.id,
                        "plan_id": self.account_analytic_plan_id.id, #plan_id.id if plan_id else False,
                        "crossovered_budget_line": [(0, 0, {
                            'name': name, 
                            'analytic_plan_id': self.account_analytic_plan_id.id,
                            'date_from': fields.Date.today(), 
                            'date_to': fields.Date.today() + rd(days=30), 
                            'planned_amount': budget_amount, 
                            'crossovered_budget_id': self.budget_id.id, 
                            'general_budget_id': self.budget_position_id.id, 
                            'general_journal_id': journal_id.id if journal_id else False, 
                            'general_account_id': account_id.id, 
                        })]
                        # "line_ids": [(0, 0, {
                        #     'name': name, 
                        #     'general_account_id': account_id.id,
                        #     'amount': budget_amount, 
                        #     'journal_id': journal_id.id, 
                        #     'date_from': fields.Date.today(), 
                        #     'date_to': fields.Date.today() + rd(days=20), 
                        #     'planned_amount': journal_id.id, 

                        # })]
                    }) if not account_existing else account_existing
            return account
        else:
            return None
        
    def create_journal_entry(self, label, journal_id, 
                             origin, date_invoice, analytic_distribution_id, 
                             movelines):
        # movelines => List of dictionary object
        account_move = self.env['account.move'].sudo()

        # partner_id = company_id.partner_id
        inv = account_move.create({  
            'ref': origin,
            'origin': origin,
            # 'partner_id': partner_id.id,
            'company_id': self.env.company.id,
            # 'company_id': self.env.user.company_id.id,
            'invoice_date': date_invoice or fields.Date.today(),
            'currency_id': self.env.user.company_id.currency_id.id,
            # Do not set default name to account move name, because it
            # is unique
            # 'name': f"{label} {origin}",
            'invoice_date': fields.Date.today(),
            'date': fields.Date.today(),
            'journal_id': journal_id.id,
            'move_type': 'entry',
            # is_purchase_document(include_receipts=True)
        })
        line = movelines
        # raise ValidationError(f"{line.get('debit')} - credit {line.get('credit')}")
        moveline = [{
                    'name': line.get('name'),
                    'ref': f"{line.get('name')} {origin}",
                    'account_id': line.get('debit_account_id'),
                    'analytic_distribution': {analytic_distribution_id.id: 100} if analytic_distribution_id else False, # analytic_distribution_id.id,
                    'debit': line.get('debit'),
                    'credit': 0.00,
                    'move_id': inv.id, 
                    'company_id': self.env.company.id,
            },
        {
                    'name': line.get('name'),
                    'ref': f"{line.get('name')} {origin}",
                    'account_id': line.get('credit_account_id'),
                    'analytic_distribution': {analytic_distribution_id.id: 100} if analytic_distribution_id else False, # analytic_distribution_id.id,
                    'debit': 0,
                    'credit': line.get('credit'),
                    'move_id': inv.id,
                    'company_id': self.env.company.id,
            }]
        for r in moveline:
            _logger.info(r)
        inv.invoice_line_ids = [(0, 0, move) for move in moveline]
        # debit_leg = self.env['account.move.line'].create({
        #             'name': line.get('name'),
        #             'ref': f"{line.get('name')} {origin}",
        #             'account_id': line.get('debit_account_id'),
        #             'analytic_distribution': {analytic_distribution_id.id: 100}, # analytic_distribution_id.id,
        #             'debit': line.get('debit'),
        #             'credit': 0.00,
        #             'move_id': inv.id,
        #     })
        # credit_leg =self.env['account.move.line'].create({
        #             'name': line.get('name'),
        #             'ref': f"{line.get('name')} {origin}",
        #             'account_id': line.get('credit_account_id'),
        #             'debit': 0,
        #             'credit': line.get('credit'),
        #             'move_id': inv.id,
        #     })
        # inv.write({'invoice_line_ids': [(6, 0, [credit_leg, debit_leg])]
        # })
        return inv
    
    def create_chart_of_account(self, name, code, type=False):
        account_chart_obj = self.env['account.account']
        if name and code:
            _logger.info(f'AXCOUNT CODE {code}')
            # raise ValidationError(code)

            account_existing = account_chart_obj.search([('code', '=', code)], limit = 1)
            account = account_chart_obj.create({
                        "name": name.strip().upper(),
                        "code": code,
                        'is_migrated': True,
                        'company_id': self.env.company.id,
                        # "company_id": self.env.user.company_id.id,
                        "reconcile": False,
                        "account_type": self.account_type if not type else type, # use type expenses
                    }) if not account_existing else account_existing
            return account
        else:
            return None
        
    def create_journal(self, code, name, branch, journal_type):#, default_account_id, other_accounts):
        #journal_type:  'sale', 'purchase', 'cash', 'bank', 'general'
        if name and code:
            journal_obj =  self.env['account.journal']
            account_journal_existing = journal_obj.search([('code', '=',code)], limit = 1)
            journal = journal_obj.create({
                'name': name,
                'type': journal_type,
                'code': code,
                'alias_name': ''.join(random.choice('EdcpasHwodfo!xyzus$rs1234567') for _ in range(10)),
                'alias_domain': ''.join(random.choice('domain') for _ in range(8)),
                'is_migrated': True,
                'branch_id': branch.id,
                'company_id': self.env.company.id,
                # "company_id": self.env.user.company_id.id,
                # 'default_account_id': default_account_id,
                # 'loss_account_id': other_accounts.get('loss_account_id') if journal_type in ['bank'] else False,
                # 'profit_account_id': other_accounts.get('profit_account_id') if journal_type in ['bank'] else False,
            }) if not account_journal_existing else account_journal_existing
            return journal
        else:
            return None

    def import_records_action(self):
        if self.import_type == "chart":
            self.import_charts_journal()
        else:
            self.import_account_transaction() 

    # def import_charts_journal(self):
    #     for rec in self.env['account.account'].search([]):
    #         rec.code = rec.code.replace('.0', '')
    def import_charts_journal(self):

        if self.data_file:
            # file_datas = base64.decodestring(self.data_file)
            file_datas = base64.decodebytes(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet_index = int(self.index) if self.index else 0
            sheet = workbook.sheet_by_index(sheet_index)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select file and type of file')
        errors = ['The Following messages occurred']
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = []
        for row in file_data:
            if row[0] and row[1] and row[5] and row[2]:
                code = str(row[0]).replace('.0', '')
                # raise ValidationError(type(code))
                # raise ValidationError(code)
                # code = str(int(row[0])) if type(row[0]) == float else str(int(row[0]))
                partner = self.create_contact(row[1].strip(), code)
                branch = self.create_branch(row[1].strip(), code)
                description = row[3] or ""
                # Creating the main charts of accounts id for main company account 
                account_code = str(row[2]).replace('.0', '') #str(row[2])[:-2] # str(int(row[2])) if type(row[2]) == float else str(int(row[2])) # CONVERTING IT FROM FLOAT TO INTEGER, THEN TO STRING
                account_id = self.create_chart_of_account(row[5], account_code, self.account_type)
                _logger.info(
                    f"Surviving this game {row} and {account_id.name} and code {account_code}"
                )
                journal_type_items = ['bank']
                journal = None
                for journal_type in journal_type_items:
                    journal = self.create_journal(
                        f"{code}", # 009901
                        f" {str(row[1])}", 
                        branch,
                        journal_type,
                        )
                    account_id.update({
                        # 'allowed_journal_ids': [(4, journal.id)],
                        'branch_id': branch,
                    })
                budget_amount = float(row[4]) if type(row[4]) in [int, float] else 0
                # analytic_account_id = self.create_analytic_account(row[3], partner, branch, account_id, journal, budget_amount)
                date_from=False
                date_to=False
                paid_date=fields.Date.today()
                self.create_update_budget_line(account_id.id, journal.id, branch, self.budget_id, False, date_from, date_to, paid_date, budget_amount, 0)
                movelines = {
                    'name': description,
                    'account_id': account_id.id,
                    'credit': budget_amount,
                    'debit': budget_amount,
                    'debit_account_id': self.default_account.id,
                    'credit_account_id': account_id.id,
                }

                # Not to be created
                journal_move_id = self.create_journal_entry(
                    description, journal, 
                    description, False,
                    False, 
                    movelines)
                journal_move_id.action_post()
                _logger.info(f'data artifacts generated: {account_id.name}')
                count += 1
                success_records.append(row[0])
            else:
                unsuccess_records.append(row[0])
        errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
        errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
        if len(errors) > 1:
            message = '\n'.join(errors)

    def import_account_transaction(self):
        # MDA Bank transactions sample
        if self.data_file:
            file_datas = base64.decodebytes(self.data_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet_index = int(self.index) if self.index else 0
            sheet = workbook.sheet_by_index(sheet_index)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select file and type of file')
        errors = ['The Following messages occurred']
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = []
        account_bank_statement_line = self.env['account.bank.statement.line'].sudo()
        if not self.running_journal_id:
            raise ValidationError('please select a running journal') 
        
        for row in file_data:
            # 0 Date of Approval, 1 Date of Payment,	2 Head
            # 3 Sub-Head, 4 Credit (₦)  5 Debit (₦) 
            # bank_journal_id = self.env['account.journal'].search(
            # [('type', '=', 'bank'),
            #     ], limit=1)
            if row[2]:
                debit, credit= row[5], row[6]
                account_code= str(row[2]).replace('.0', '') # str(int(row[2])) if type(row[2]) in [float, int] else str(row[2])
                account_head_id = self.env['account.account'].search([('code', '=', account_code)], limit=1)
                # raise ValidationError(type(row[2]))

                if debit or credit:
                    journal_head = str(row[1]).replace("'", "") #row[1] 
                    journal_head = str(row[1]).replace('.0', '')
                    source_journal = self.env['account.journal'].search([('code', '=', str(journal_head))], limit = 1)
                    if not account_head_id:
                        unsuccess_records.append(f"No related account found with code {row[2]} found ")
                    else:
                        date_of_payment = fields.Date.today() 
                        year, month, day = False, False, False
                        date_row = row[0]
                        if date_row:
                            if type(date_row) in [float, int]:
                                date_of_payment = datetime(*xlrd.xldate_as_tuple(date_row, 0))
                            elif type(date_row) in str:
                                dp = date_row.split('/')
                                if dp:
                                    year = int(dp[2])
                                    month = int(dp[1])
                                    day = int(dp[0])
                                    date_of_payment = date(year, month, day)
                        debit = row[5] if row[5] and row[5] > 0 else False
                        credit = row[6] if row[6] and row[6] > 0 else False
                        narration = row[4]
                        movelines = {
                            'name': narration,
                            'account_id': account_head_id.id,
                            'credit': credit,
                            'debit': debit,
                            'debit_account_id': account_head_id.id,
                            'credit_account_id': self.default_account.id, # account of the bank that will be on credit
                        }
                        account_move = self.env['account.move'].sudo()
                        inv = account_move.create({  
                            'ref': narration,
                            'origin': narration,
                            'company_id': self.env.company.id,
                            'company_id': self.env.company.id,
                            'invoice_date': date_of_payment or fields.Date.today(),
                            'currency_id': self.env.user.company_id.currency_id.id,
                            'invoice_date': fields.Date.today(),
                            'date': fields.Date.today(),
                            'journal_id': source_journal.id or self.running_journal_id.id,
                            'move_type': 'entry',
                        })
                        line = movelines
                        if line.get('credit') and line.get('credit') > 0:
                            moveline = [{
                                        'name': line.get('name'),
                                        'ref': f"{line.get('name')} {narration}",
                                        'account_id': line.get('debit_account_id'),
                                        'analytic_distribution': False, # analytic_distribution_id.id,
                                        'debit': line.get('credit'),
                                        'credit': 0.0,
                                        'move_id': inv.id, 
                                        'company_id': self.env.company.id,
                                },
                                {
                                        'name': line.get('name'),
                                        'ref': f"{line.get('name')} {narration}",
                                        'account_id': line.get('credit_account_id'),
                                        'analytic_distribution': False, # analytic_distribution_id.id,
                                        'debit': 0,
                                        'credit': line.get('credit'),
                                        'move_id': inv.id,
                                        'company_id': self.env.company.id,
                                    }]
                            self.create_update_budget_line(line.get('debit_account_id'), inv.journal_id.id, inv.journal_id.branch_id, False, False, False, False, date_of_payment, budget_amount=False, amount_used=line.get('credit'))
                            
                        else:
                            moveline = [{
                                        'name': line.get('name'),
                                        'ref': f"{line.get('name')} {narration}",
                                        'account_id': line.get('credit_account_id'),
                                        'analytic_distribution': False, # analytic_distribution_id.id,
                                        'debit': 0,
                                        'credit': line.get('debit'),
                                        'move_id': inv.id, 
                                        'company_id': self.env.company.id,
                                },
                                {
                                        'name': line.get('name'),
                                        'ref': f"{line.get('name')} {narration}",
                                        'account_id': self.running_journal_id.suspense_account_id.id,
                                        'analytic_distribution': False, # analytic_distribution_id.id,
                                        'debit': line.get('debit'),
                                        'credit': 0,
                                        'move_id': inv.id,
                                        'company_id': self.env.company.id,
                                }]
                            
                        inv.invoice_line_ids = [(0, 0, move) for move in moveline]
                        inv.action_post()
                        _logger.info(f'Loading the create new move with id: {inv.id}')
                        count += 1
                        success_records.append(row)
                else:
                    unsuccess_records.append(account_head_id)
        errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
        errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message)

    # def import_account_transaction(self):
    #     # MDA Bank transactions sample
    #     if self.data_file:
    #         file_datas = base64.decodebytes(self.data_file)
    #         workbook = xlrd.open_workbook(file_contents=file_datas)
    #         sheet_index = int(self.index) if self.index else 0
    #         sheet = workbook.sheet_by_index(sheet_index)
    #         data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
    #         data.pop(0)
    #         file_data = data
    #     else:
    #         raise ValidationError('Please select file and type of file')
    #     errors = ['The Following messages occurred']
    #     unimport_count, count = 0, 0
    #     success_records = []
    #     unsuccess_records = []
    #     account_bank_statement_line = self.env['account.bank.statement.line'].sudo()
    #     if not self.running_journal_id:
    #         raise ValidationError('please select a running journal') 
        
    #     for row in file_data:
    #         # 0 Date of Approval, 1 Date of Payment,	2 Head
    #         # 3 Sub-Head, 4 Credit (₦)  5 Debit (₦) 
    #         journal_head = row[2]
    #         date_of_payment = fields.Date.today() 
    #         year, month, day = False, False, False
    #         if row[1]:
    #             if type(row[1]) in [float, int]:
    #                 date_of_payment = datetime(*xlrd.xldate_as_tuple(row[1], 0))
    #             elif type(row[1]) in str:
    #                 dp = row[1].split('/')
    #                 if dp:
    #                     year = int(dp[2])
    #                     month = int(dp[1])
    #                     day = int(dp[0])
    #                     date_of_payment = date(year, month, day)
    #         credit = row[6] if row[6] and row[6] > 0 else False
    #         debit = row[7] if row[7] and row[7] > 0 else False
    #         narration = row[5]
    #         if journal_head and debit:
    #             source_journal = self.env['account.journal'].search([('code', '=', str(journal_head))], limit = 1)
    #             if source_journal:
    #                 # internal_payment = self.create_internal_payment(
    #                 #     date_of_payment, 
    #                 #     credit,
    #                 #     debit,
    #                 #     narration,
    #                 #     source_journal,
    #                 #     )
    #                 credit_vals = {
    #                     'journal_id': source_journal.id, 
    #                     'amount': debit,
    #                     'payment_ref': f"{row[4]}, {narration}",
    #                     'date': date_of_payment
    #                 }
    #                 debit_vals = {
    #                     'journal_id': self.running_journal_id.id, 
    #                     'amount': -debit,
    #                     'payment_ref': f"{row[4]}, {narration}",
    #                     'date': date_of_payment
    #                 }
    #                 account_bank_statement_line.create(credit_vals) 
    #                 account_bank_statement_line.create(debit_vals) 
    #                 _logger.info(f'Loading the journal payment: {journal_head}')
    #                 count += 1
    #                 success_records.append(journal_head)
    #             else:
    #                 unsuccess_records.append(f"No related journal with code {journal_head} found ")

    #         elif credit and not journal_head:
    #             account_bank_statement_line = self.env['account.bank.statement.line'].sudo()
    #             credit_vals = {
    #                 'journal_id': self.running_journal_id.id, 
    #                 'amount': credit,
    #                 'payment_ref': narration,
    #                 'date': date_of_payment
    #             }
    #             account_bank_statement_line.create(credit_vals) 
    #         else:
    #             unsuccess_records.append(journal_head)
    #     errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
    #     errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
    #     if len(errors) > 1:
    #         message = '\n'.join(errors)
    #         return self.confirm_notification(message)

    def create_internal_payment(self, date_of_payment, credit, debit, narration, mda_journal):
        running_journal = self.running_journal_id
        account_payment = self.env['account.payment']
        vals = {
            'is_internal_transfer': True, 
            'payment_type': 'outbound' if debit else 'inbound', 
            'amount': debit or credit,
            'narration': narration,
            'journal_id': running_journal.id if debit else mda_journal.id,
            'destination_journal_id': mda_journal.id if debit else running_journal.id,
            'payment_date': date_of_payment
        }
        payment = account_payment.create(vals) 
        payment.create_generate_statement_line(payment)
        
            
    def confirm_notification(self,popup_message):
        view = self.env.ref('plateau_addons.pl_import_wizard_form_view')
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['message'] = popup_message
        return {
                'name':'Message!',
                'type':'ir.actions.act_window',
                'view_type':'form',
                'res_model':'pl.confirm.dialog',
                'views':[(view.id, 'form')],
                'view_id':view.id,
                'target':'new',
                'context':context,
                }


class PLDialogModel(models.TransientModel):
    _name="pl.confirm.dialog"

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False 

    name = fields.Text(string="Message",readonly=True,default=get_default)
