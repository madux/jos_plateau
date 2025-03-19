from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.parser import parse
import logging 
from bs4 import BeautifulSoup
import io
import xlwt
from datetime import datetime, timedelta
import base64

_logger = logging.getLogger(__name__)


class AccountDynamicReport(models.Model):
    _name = "account.dynamic.report"

    journal_ids = fields.Many2many(
        'account.journal',
        string='Journals'
        )
    
    account_ids = fields.Many2many(
        'account.account',
        string='Accounts'
        )
    name = fields.Char(
        string='Report Name'
        )
    account_analytics_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts'
        )
    report_type = fields.Selection(
        selection=[
            ("all", "All Statement"),
            ("fs", "Financial Statement"),
            ("cf", "CashFlow Statement"),
            ("bank", "Trial Balance"),
            ("cash", "General Ledger"),
        ],
        string="Report Type", tracking=True,
        required=False, default="all"
    )
    format = fields.Selection(
        selection=[
            ("pdf", "PDF"),
            ("html", "Html"),
            ("xls", "Excel"),
            ("tab", "Tableau"),
            ("powerBi", "Power BI"),
            ("dashboard", "Dashboard"),
        ],
        string="Format", tracking=True,
        required=False, default="pdf"
    )
    
    branch_ids = fields.Many2many('multi.branch', string='MDA')
    moveline_ids = fields.Many2many('account.move.line', string='Dummy move lines')
    # budget_id = fields.Many2one('crossovered.budget', string='Budget')
    budget_id = fields.Many2one('ng.account.budget.line', string='Budget')
    fiscal_year = fields.Date(string='Fiscal Year', default=fields.Date.today())
    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')
    partner_id = fields.Many2one('res.partner', string='Partner')
    account_head_type = fields.Selection(
        [
        ("Revenue", "Revenue"), 
        ("Personnel", "Personnel"),
        ("Overhead", "Overhead"), 
        ("Expenditure", "Expenditure"), 
        ("Capital", "Capital"),
        ("Other", "Others"),
        ], string="Budget Type", 
    )
    excel_file = fields.Binary('Download Excel file', readonly=True)
    filename = fields.Char('Excel File')

    def action_print_report(self):
        move_records = []
        search_domain = []
        if self.journal_ids:
            search_domain.append(('move_id.journal_id.id', 'in', [j.id for j in self.journal_ids]))
        if self.branch_ids:
            search_domain.append(('move_id.branch_id.id', 'in', [j.id for j in self.branch_ids]))
        if self.account_ids:
            search_domain.append(('account_id.id', 'in', [j.id for j in self.account_ids]))
        if self.account_head_type:
            search_domain.append(('account_id.account_head_type', '=', self.account_head_type))
        # if self.branch_ids:
        #     search_domain.append(('account_id.id', 'in', [j.id for j in self.account_ids]))

        # if self.date_from and self.date_to:
        #     search_domain += [('date', '=>', self.date_from), ('date', '=>', self.date_from)]
        account_move_line = self.env['account.move.line'].search(search_domain)
        account_ids, journal_ids = [], []
        for record in account_move_line:
            if self.date_from and self.date_to:
                if record.date <= self.date_from and self.date_to >= record.date:
                    move_records.append(record)
                    self.moveline_ids = [(4, record.id)]
                    account_ids.append(record.account_id)
                    journal_ids.append(record.journal_id)
            else:
                move_records.append(record)
                self.moveline_ids = [(4, record.id)]
                account_ids.append(record.account_id)
                journal_ids.append(record.journal_id)
        total_debit, total_credit = 0, 0
        data = []
        fiscal_year = self.fiscal_year
        for acc in list(set(account_ids)):
            # budget_properties = self.get_account_and_journal_budget(acc)
            all_move_line_with_account_ids = self.mapped('moveline_ids').filtered(lambda s: s.account_id.id == acc.id)
            account_data = {
                'account_obj': None,
                }
            account_data['account_obj'] = {
                'fiscal_year': fiscal_year.strftime('%Y'),
                'account_name': f"{acc.code} {acc.name}",
                # 'current_balance': f"{acc.currency_id.symbol or self.env.user.company_id.currency_id.symbol} {acc.current_balance}",
                # 'current_balance': 0, # abs(acc.current_balance),
                'actual_amount': 0, # abs(acc.current_balance),
                'budget_utilized': 0,
                'budget_amount': 0,
                'budget_balance': 0,
                'account_move_line': [],
                } 
            # account_data = {
            #     'account_name': f"{acc.code} {acc.name}",
            #     'current_balance': f"{acc.currency_id.symbol or self.env.user.company_id.currency_id.symbol} {acc.current_balance}",
            #     'budget_amount': self.get_budget_amount(acc),
            #     'account_move_line': [],
            #     } 
            ''' {
                'account_obj': {
                    
                    'account_name': 'Tax',
                    'actual_amount': abs(acc.price_subtotal),
                    'budget_utilized': 43320,
                    'budget_amount': 2000,
                    'budget_balance': 90000,
                    'account_move_line': [
                                {
                                    'move_description': 'Trip to london',
                                    'journal': '2345555 BANK',
                                    'move_debit': 455000
                                    'move_credit': 0
                                    'move_balance': 455000,
                                    }, {}, {}, 
                    ],
                }  
            
            }
            '''
             
            for jl in all_move_line_with_account_ids:
                BudgetAmount = jl.ng_budget_line_id.allocated_amount if jl.ng_budget_line_id else 0
                BudgetUtilization = jl.price_subtotal
                ActualAmount = jl.price_subtotal
                BudgetBalance = jl.ng_budget_line_id.allocated_amount - jl.price_subtotal if jl.ng_budget_line_id else 0
                move_item = {
                            'move_description': BeautifulSoup(jl.name.capitalize() if jl.name else "", features="lxml").get_text(),
                            'journal': f"{jl.journal_id.code}",# {jl.journal_id.name}",
                            'move_debit': jl.debit,
                            'move_credit': jl.credit,
                            'move_balance': abs(jl.credit - jl.debit),
                            'account_and_journal_budget': BudgetAmount,
                            'account_and_journal_budget_utilization': BudgetUtilization,
                            'account_and_journal_budget_variance': BudgetBalance,
                            },
                account_data['account_obj']['actual_amount'] += abs(ActualAmount)
                account_data['account_obj']['budget_amount'] += BudgetAmount
                account_data['account_obj']['budget_utilized'] += BudgetUtilization
                account_data['account_obj']['budget_balance'] += BudgetBalance
                account_data['account_obj']['account_move_line'] += move_item
            data.append(account_data)
        data = {
            'data': data,
        }
        '''data = [
                    'account_obj': {
                        'account_name': 'Tax',
                        'current_balance': abs(acc.current_balance),
                        'budget_utilized': 43320,
                        'budget_amount': 2000,
                        'budget_balance': 90000,
                        'account_move_line': [
                                    {
                                        'move_description': 'Trip to london',
                                        'journal': '2345555 BANK',
                                        'move_debit': 455000
                                        'move_credit': 0
                                        'move_balance': 455000,
                                        }, {}, {}, 
                        ],
                    }  
            
            }, {}, {}]'''
        _logger.info(data)
        if self.format == 'pdf':
            return self.env.ref('plateau_addons.print_account_report').report_action(self, data)
        elif self.format == 'xls':
            return self.action_export_as_excel(data)
        else:
            raise ValidationError("Ops.. Sorry, for now only PDF and excel is enabled")
    def get_account_and_journal_budget(self, account_id, fiscal_year=False):
        domain = [('account_id', '=', account_id.id)]
        if not fiscal_year:
            fiscal_year = fields.Date.today() 
        else:
            fiscal_year = fiscal_year
        domain += [('budget_allocation_date', '>=', fiscal_year), ('allocation_date', '<=', fiscal_year)]
        related_budgets = self.env['ng.account.budget.line'].search(domain)
        utilized_budget, budget_amount, variance = 0, 0, 0
        for rec in related_budgets:
            utilized_budget += rec.utilized_amount
            budget_amount += rec.allocated_amount
            variance += rec.budget_balance
        return budget_amount, abs(utilized_budget), abs(variance)
     
    def action_export_as_excel(self, data):
        data = data.get('data')
        if data:
            headers = [
                'S/N', 
                'Economic Code', 
                'Details/Narration', 
                'Actual (NGN)', 
                f"Budget {data[0].get('account_obj').get('fiscal_year')}", 
                'Utilization(NGN)', 
                'Variance (NGN)', 
                'Remark'
                ]
            style0 = xlwt.easyxf('font: name Times New Roman, color-index red, bold on',
                    num_format_str='#,##0.00')
            wb = xlwt.Workbook()
            ws = wb.add_sheet(self.name, cell_overwrite_ok=True)
            colh = 0
            ws.write(0, 6, 'RECORDS GENERATED: %s - On %s' %(self.name, datetime.strftime(fields.Date.today(), '%Y-%m-%d')), style0)
            for head in headers:
                ws.write(1, colh, head)
                colh += 1
            rowh = 2
            for dt in data:
                dynamic_column = 0
                ws.write(rowh, dynamic_column, '')
                ws.write(rowh, dynamic_column + 1, dt.get('account_obj').get('account_name'))
                ws.write(rowh, dynamic_column + 2, "-")
                ws.write(rowh, dynamic_column + 3,  '{0:,}'.format(float(dt.get('account_obj').get('actual_amount'))))
                ws.write(rowh, dynamic_column + 4, '{0:,}'.format(float(dt.get('account_obj').get('budget_amount'))))
                ws.write(rowh, dynamic_column + 5, '{0:,}'.format(float(dt.get('account_obj').get('budget_utilized'))))
                ws.write(rowh, dynamic_column + 6, '{0:,}'.format(float(dt.get('account_obj').get('budget_balance'))))
                ws.write(rowh, dynamic_column + 7, '-')
                account_move_line = dt.get('account_obj').get('account_move_line')
                
                rowh += 1
                # dynamic_column += 1
                for count, ml in enumerate(account_move_line, 1):
                    ws.write(rowh, dynamic_column, count)
                    ws.write(rowh, dynamic_column + 1, '')
                    ws.write(rowh, dynamic_column + 2, ml.get('move_description'))
                    ws.write(rowh, dynamic_column + 3,  '{0:,}'.format(float(ml.get('move_balance') or 0)))
                    ws.write(rowh, dynamic_column + 4, '{0:,}'.format(float(ml.get('account_and_journal_budget') or 0)))
                    ws.write(rowh, dynamic_column + 5, '{0:,}'.format(float(ml.get('account_and_journal_budget_utilization') or 0)))
                    ws.write(rowh, dynamic_column + 6, '{0:,}'.format(float(ml.get('account_and_journal_budget_variance') or 0)))
                    ws.write(rowh, dynamic_column + 7, '-')
                    rowh += 1
            rowh += 1 # added extra row to give space for each account lines
            fp = io.BytesIO()
            wb.save(fp)
            
            # buffered = io.BytesIO()
            # img.save(buffered, format="PNG")
            # img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
            filename = "{} ON {}.xls".format(
                self.name, datetime.strftime(fields.Date.today(), '%Y-%m-%d'), style0)
            # self.excel_file = base64.encodestring(fp.getvalue())
            self.excel_file = base64.b64encode(fp.getvalue())
            
            # attachementObj = self.attachment_render(self.name, base64.encodestring(fp.getvalue()), 'application/vnd.ms-excel')
            # self.send_mail([attachementObj])
            self.filename = filename
            attachment = self.attachment_render(self.name, base64.b64encode(fp.getvalue()), 'application/vnd.ms-excel')
            fp.close()
            _logger.info(f"THISSS IS LINK {'/web/content/%s/%s?download=true' % (attachment.id, attachment.name)}"),
            return {
                'type': 'ir.actions.act_url',
                'name': 'REPORT',
                'url': '/web/content/%s/%s?download=true' % (attachment.id, attachment.name),
            }
            # return { 
            #         'url': '/web/content/%s/%s?download=true' % (attachment.id, attachment.name),
            #         'type': 'ir.actions.act_url',
            #         'url': '/web/content/?model=account.dynamic.report&download=true&field=excel_file&id={}&filename={}'.format(self.id, self.filename),
            #         'target': 'new',
            #         'nodestroy': True,
            # }
        else:
            raise ValidationError('No data found to generate excel report')
    
    def attachment_render(self, attachment_name, report_binary, mimetype):
        attachmentObj = self.env['ir.attachment'].create({
            'name': attachment_name,
            'type': 'binary',
            'datas': report_binary,
            'store_fname': attachment_name,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': mimetype
        })
        return attachmentObj