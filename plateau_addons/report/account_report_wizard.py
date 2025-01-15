from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.parser import parse
import logging 

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
            ("fs", "Excel"),
            ("tab", "Tableau"),
            ("bank", "Power BI"),
            ("others", "Others"),
        ],
        string="Format", tracking=True,
        required=False, default="pdf"
    )
    
    branch_ids = fields.Many2many('multi.branch', string='MDA')
    moveline_ids = fields.Many2many('account.move.line', string='Dummy move lines')
    budget_id = fields.Many2one('crossovered.budget', string='Budget')
    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')
    partner_id = fields.Many2one('res.partner', string='Partner')
 

    def action_print_report(self):
        move_records = []
        search_domain = []
        if self.journal_ids:
            search_domain.append(('move_id.journal_id.id', 'in', [j.id for j in self.journal_ids]))
        if self.branch_ids:
            search_domain.append(('move_id.branch_id.id', 'in', [j.id for j in self.branch_ids]))
        if self.account_ids:
            search_domain.append(('account_id.id', 'in', [j.id for j in self.account_ids]))
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
        for acc in list(set(account_ids)):
            all_move_line_with_account_ids = self.mapped('moveline_ids').filtered(lambda s: s.account_id.id == acc.id)
            account_data = {
                'account_obj': None,
                }
            account_data['account_obj'] = {
                'account_name': f"{acc.code} {acc.name}",
                # 'current_balance': f"{acc.currency_id.symbol or self.env.user.company_id.currency_id.symbol} {acc.current_balance}",
                'current_balance': abs(acc.current_balance),
                'budget_amount': self.get_budget_amount(acc),
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
                move_item = {
                            'move_description': f"{jl.name}",#jl.name,
                            'journal': f"{jl.journal_id.code}",# {jl.journal_id.name}",
                            'move_debit': jl.debit,
                            'move_credit': jl.credit,
                            'move_balance': jl.credit - jl.debit,
                            'account_and_journal_budget': self.get_account_and_journal_budget(acc, jl.journal_id, )[0],
                            'account_and_journal_budget_utilization': self.get_account_and_journal_budget(acc, jl.journal_id)[1],
                            'account_and_journal_budget_variance': self.get_account_and_journal_budget(acc, jl.journal_id)[2]
                            },
                account_data['account_obj']['account_move_line'] += move_item
            data.append(account_data)
        # for move in move_records:
        #     total_debit += move.debit 
        #     total_credit += move.credit 
        # total_balance = total_credit - total_debit
        data = {
            # 'move_records': move_records,
            # 'total_balance': total_balance,
            'data': data,
        }
        _logger.info(data)
        return self.env.ref('plateau_addons.print_account_report').report_action(self, data)
    
    def get_account_and_journal_budget(self, account_id, journal_id):
        relatd_budgets = self.env['ng.account.budget'].search([
            ('general_account_id', '=', account_id.id), ('general_account_id', '=', journal_id.id)], limit=1)
        utilized_budget, budget,variance = 0, 0, 0
        for rec in relatd_budgets:
            utilized_budget += rec.budget_used_amount
            budget += rec.budget_amount
            variance += rec.budget_variance
        return budget, abs(utilized_budget), abs(variance)
    
    def get_budget_amount(self, account_id):
        budget_line = self.env['ng.account.budget'].search([('general_account_id', '=', account_id.id)])
        budget_amount = 0
        for rec in budget_line:
            budget_amount += rec.budget_amount
        return budget_amount

    # def action_print_report(self):
    #     move_records = []
    #     search_domain = []
    #     if self.journal_ids:
    #         search_domain.append(('move_id.journal_id.id', 'in', [j.id for j in self.journal_ids]))
    #     if self.branch_ids:
    #         search_domain.append(('move_id.branch_id.id', 'in', [j.id for j in self.branch_ids]))
    #     if self.account_ids:
    #         search_domain.append(('account_id.id', 'in', [j.id for j in self.account_ids]))
    #     if self.branch_ids:
    #         search_domain.append(('account_id.id', 'in', [j.id for j in self.account_ids]))

    #     # if self.date_from and self.date_to:
    #     #     search_domain += [('date', '=>', self.date_from), ('date', '=>', self.date_from)]
    #     account_move_line = self.env['account.move.line'].search(search_domain)
    #     account_ids, journal_ids = [], []
    #     for record in account_move_line:
    #         if self.date_from and self.date_to:
    #             if record.date <= self.date_from and self.date_to >= record.date:
    #                 move_records.append(record)
    #                 self.moveline_ids = [(4, record.id)]
    #                 account_ids.append(record.account_id)
    #                 journal_ids.append(record.journal_id)
    #         else:
    #             move_records.append(record)
    #             self.moveline_ids = [(4, record.id)]
    #             account_ids.append(record.account_id)
    #             journal_ids.append(record.journal_id)
    #     total_debit, total_credit = 0, 0
    #     data = []
    #     for acc in list(set(account_ids)):
    #         all_move_line_with_account_ids = self.mapped('moveline_ids').filtered(lambda s: s.account_id.id == acc.id)
    #         account_data = {
    #             'account_obj': None,
    #             }
    #         account_data['account_obj'] = {
    #             'account_name': f"{acc.code} {acc.name}",
    #             'account_journals': [],
    #             } 
    #         ''' {
    #             'account_obj': {
    #                 'account_name': 'Tax', 
    #                 'account_journals': [
    #                     {
    #                         'journal_name': 'Office Account General', 
    #                         'journal_code': '001010220', 
    #                         'journal_move_line': [
    #                             {
    #                                 'move_description': 'Trip to london',
    #                                 'move_debit': 455000
    #                                 'move_credit': 0
    #                                 'move_balance': 455000,
    #                                 }, {}, {}, 
    #                         ],
    #                     }
    #                 ],
    #             }
    #         }
    #         '''
    #         move_journals = [re.move_id.journal_id for re in all_move_line_with_account_ids]
    #         journals = list(set(move_journals))
    #         for jrl in journals:
    #             j_info = {}
    #             j_info['journal_name'] = f"{jrl.code} {jrl.name}" 
    #             j_info['journal_code'] = jrl.code
    #             all_move_line_with_journals_ids = self.mapped('moveline_ids').filtered(lambda s: s.account_id.id == acc.id and s.move_id.journal_id.id == jrl.id)
    #             j_info['journal_move_line'] = []
    #             for jl in all_move_line_with_journals_ids:
    #                 j_item = {
    #                             'move_description': jl.name,
    #                             'move_debit': jl.debit,
    #                             'move_credit': jl.credit,
    #                             'move_balance': jl.balance,
    #                             },
    #                 j_info['journal_move_line'].append(j_item)
    #             account_data['account_obj']['account_journals'].append(j_info)
    #         data.append(account_data)
    #     for move in move_records:
    #         total_debit += move.debit 
    #         total_credit += move.credit 
    #     total_balance = total_credit - total_debit
    #     data = {
    #         'move_records': move_records,
    #         'total_balance': total_balance,
    #         'data': data,
    #     }
    #     _logger.info(data)
    #     return self.env.ref('plateau_addons.print_account_report').report_action(self, data)
        

    
    
     