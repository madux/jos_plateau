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
 

class ImportPLCharts(models.TransientModel):
    _name = 'pl.import.wizard'

    data_file = fields.Binary(string="Upload File (.xls)")
    filename = fields.Char("Filename")
    index = fields.Integer("Sheet Index", default=0)

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
        required=True,
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
                    'vat': code,
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
        
    def create_analytic_account(self, name, partner, branch):
        analytic_account = self.env['account.analytic.account'].sudo()
        if partner:
            plan_id = self.generate_analytic_plan(partner)
            account_existing = analytic_account.search([('code', '=',partner.vat)], limit = 1)
            account = analytic_account.create({
                        "name": name, #partner.name.strip().title() +' - '+ partner.vat,
                        "partner_id": partner.id,
                        "branch_id": branch.id,
                        "company_id": self.env.user.company_id.id,
                        "plan_id": plan_id.id if plan_id else False,
                    }) if not account_existing else account_existing
            return account
        else:
            return None
        
    def create_chart_of_account(self, name, code, type=False):
        account_chart_obj = self.env['account.account']
        if name and code:
            account_existing = account_chart_obj.search([('code', '=', code)], limit = 1)
            account = account_chart_obj.create({
                        "name": name.strip().upper(),
                        "code": code,
                        'is_migrated': True,
                        "reconcile": True,
                        "account_type": self.account_type if not type else type,
                    }) if not account_existing else account_existing
            return account
        else:
            return None
        
    def create_journal(self, code, name, branch, journal_type, default_account_id, other_accounts):
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
                'default_account_id': default_account_id,
                'loss_account_id': other_accounts.get('loss_account_id') if journal_type in ['bank'] else False,
                'profit_account_id': other_accounts.get('profit_account_id') if journal_type in ['bank'] else False,
            }) if not account_journal_existing else account_journal_existing
            return journal
        else:
            return None

    def create_vendor_bill(self, company_id, account_id, analytic_account_id, **kwargs):
        journal_id = self.env['account.journal'].search(
        [('type', '=', 'purchase'),
            ('code', '=', 'BILL')
            ], limit=1)
        account_move = self.env['account.move'].sudo()
        partner_id = company_id.partner_id
        inv = account_move.create({  
            'ref': self.code,
            'origin': kwargs.get('code'),
            'partner_id': partner_id.id,
            'company_id': company_id.id,
            'currency_id': self.env.user.company_id.currency_id.id,
            # Do not set default name to account move name, because it
            # is unique
            'name': f"{kwargs.get('code')}",
            'move_type': 'in_receipt',
            'invoice_date': fields.Date.today(),
            'date': fields.Date.today(),
            'journal_id': journal_id.id,
            'invoice_line_ids': [(0, 0, {
                    'name': kwargs.get('description'),
                    'ref': f"{kwargs.get('code')}",
                    'account_id': account_id.id,
                    'price_unit': f"{kwargs.get('amount')}",
                    'quantity': 1,
                    'discount': 0.0,
                    'code': kwargs.get('code'),
                    # 'product_uom_id': pr.product_id.uom_id.id if pr.product_id else None,
                    # 'product_id': pr.product_id.id if pr.product_id else None,
            })],
        })
        return inv
          
    def import_records_action(self):
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
                code = str(int(row[0])) if type(row[0]) == float else str(int(row[0]))
                partner = self.create_contact(row[1].strip(), code)
                branch = self.create_branch(row[1].strip(), code)
                # Creating the main charts of accounts id for main company account 
                account_code = str(int(row[2])) if type(row[2]) == float else str(int(row[2])) # CONVERTING IT FROM FLOAT TO INTEGER, THEN TO STRING
                account_id = self.create_chart_of_account(row[5], account_code, self.account_type)
                _logger.info(
                    f"Surviving this game {row} and {account_id.name} and code {account_code}"
                )
                journal_type_items = ['bank', 'sale', 'purchase']
                default_journal_expense_account_id = self.create_chart_of_account(f"Expense Account for {str(row[1])}", f"EXJ{code}", "expense")
                default_journal_income_account_id = self.create_chart_of_account(f"INCOME for {str(row[1])}", f'INC{code}', "income")
                default_journal_bank_cash_account_id = self.create_chart_of_account(f"BNK/CASH for {str(row[1])}",f'BC{code}', "asset_cash")
                # creating the three tiers of journals (bank/cash/sale/purchase) for the journals and creating the respective accounts i.e expense, income, asset cash and bank
                for journal_type in journal_type_items:
                    default_account_dict = {
                    'loss_account_id': default_journal_expense_account_id.id if default_journal_expense_account_id else False,
                    'profit_account_id': default_journal_income_account_id.id if default_journal_income_account_id else False,
                    'bank_account_id': default_journal_bank_cash_account_id.id if default_journal_bank_cash_account_id else False
                    } 
                    default_account_id = default_account_dict.get('loss_account_id') if journal_type == 'purchase' else \
                    default_account_dict.get('profit_account_id') if journal_type == 'sale' else default_account_dict.get('bank_account_id')
                    journal = self.create_journal(
                        f"{journal_type[0:2].capitalize()} - {code}", # B009901, S009993, P332222 
                        f" {journal_type.capitalize()} - {str(row[1])}", 
                        branch,
                        journal_type,
                        default_account_id = default_account_id,
                        other_accounts = default_account_dict,
                        )
                    account_id.update({
                        'allowed_journal_ids': [(4, journal.id)],
                        'branch_id': branch,
                    })
                    default_journal_expense_account_id.update({
                        'allowed_journal_ids': [(4, journal.id)],
                        'branch_id': branch,
                    })
                    default_journal_income_account_id.update({
                        'allowed_journal_ids': [(4, journal.id)],
                        'branch_id': branch,
                    })
                    default_journal_bank_cash_account_id.update({
                        'allowed_journal_ids': [(4, journal.id)],
                        'branch_id': branch,
                    })
                self.create_analytic_account(row[3], partner, branch)
                _logger.info(f'data artifacts generated: {account_id.name}')
                count += 1
                success_records.append(row[0])
            else:
                unsuccess_records.append(row[0])
        errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
        errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
        if len(errors) > 1:
            message = '\n'.join(errors)
            # return self.confirm_notification(message)

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
