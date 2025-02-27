# -*- coding: utf-8 -*-
import requests
import json
import re
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
from odoo.exceptions import UserError,ValidationError
from odoo.tools.safe_eval import safe_eval

import logging
_logger = logging.getLogger(__name__)


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'
    branch_id = fields.Many2one(
        'multi.branch', 'MDA Sector', default=lambda self: self.env.user.branch_id.id)


class AccountAccount(models.Model):
    _inherit = "account.account"
    branch_id = fields.Many2one('multi.branch', string='MDA Sector',
                                default=lambda self: self.env.user.branch_id.id, required=False)

class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"
    branch_id = fields.Many2one('multi.branch', related='debit_move_id.branch_id', string='MDA Sector',
                                store=True, default=lambda self: self.env.user.partner_id.branch_id.id)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    branch_id = fields.Many2one(
        'multi.branch', 'MDA Sector', default=lambda self: self.env['multi.branch']._branch_default_get(), required=False)

    allowed_branch_ids = fields.Many2many(
        'multi.branch', string='MDA Sectors', required=False) 


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    branch_id = fields.Many2one(
        'multi.branch', 'MDA Sector', default=lambda self: self.env['multi.branch']._branch_default_get(), required=False)


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    branch_id = fields.Many2one(
        'multi.branch', 'MDA Sector', default=lambda self: self.env.user.partner_id.branch_id.id, required=False)


class AccountInvoice(models.Model):
    _inherit = 'account.move'
    branch_id = fields.Many2one('multi.branch', 'MDA Sector', default=lambda self: self.env.user.branch_id.id)
    
    # @api.depends('company_id', 'invoice_filter_type_domain', 'branch_id')
    # def _compute_suitable_journal_ids(self):
    #     for m in self:
    #         journal_type = m.invoice_filter_type_domain or 'general'
    #         company_id = m.company_id.id or self.env.company.id
    #         branch_ids = [rec.id for rec in self.env.user.branch_ids if rec] + [self.env.user.branch_id.id]
    #         domain = [('company_id', '=', company_id), ('type', '=', journal_type), ('branch_id', 'in', branch_ids)]
    #         m.suitable_journal_ids = self.env['account.journal'].search(domain)
      
    # def action_move_create(self):
    #     """ Creates invoice related analytics and financial move lines """
    #     account_move = self.env['account.move']

    #     for inv in self:
    #         if not inv.journal_id.sequence_id:
    #             raise UserError(
    #                 _('Please define sequence on the journal related to this invoice.'))
    #         if not inv.invoice_line_ids.filtered(lambda line: line.account_id):
    #             raise UserError(_('Please add at least one invoice line.'))
    #         if inv.move_id:
    #             continue
    #         if not inv.date_invoice:
    #             inv.write({'date_invoice': fields.Date.context_today(self)})
    #         if not inv.date_due:
    #             inv.write({'date_due': inv.date_invoice})
    #         company_currency = inv.company_id.currency_id

    #         # create move lines (one per invoice line + eventual taxes and analytic lines)
    #         iml = inv.invoice_line_move_line_get()
    #         iml += inv.tax_line_move_line_get()

    #         diff_currency = inv.currency_id != company_currency
    #         # create one move line for the total and possibly adjust the other lines amount
    #         total, total_currency, iml = inv.compute_invoice_totals(
    #             company_currency, iml)

    #         name = inv.name or ''
    #         if inv.payment_term_id:
    #             totlines = inv.payment_term_id.with_context(
    #                 currency_id=company_currency.id).compute(total, inv.date_invoice)[0]
    #             res_amount_currency = total_currency
    #             for i, t in enumerate(totlines):
    #                 if inv.currency_id != company_currency:
    #                     amount_currency = company_currency._convert(
    #                         t[1], inv.currency_id, inv.company_id, inv._get_currency_rate_date() or fields.Date.today())
    #                 else:
    #                     amount_currency = False

    #                 # last line: add the diff
    #                 res_amount_currency -= amount_currency or 0
    #                 if i + 1 == len(totlines):
    #                     amount_currency += res_amount_currency

    #                 iml.append({
    #                     'type': 'dest',
    #                     'name': name,
    #                     'price': t[1],
    #                     'account_id': inv.account_id.id,
    #                     'branch_id': inv.branch_id.id,
    #                     'date_maturity': t[0],
    #                     'amount_currency': diff_currency and amount_currency,
    #                     'currency_id': diff_currency and inv.currency_id.id,
    #                     'invoice_id': inv.id
    #                 })
    #         else:
    #             iml.append({
    #                 'type': 'dest',
    #                 'name': name,
    #                 'price': total,
    #                 'account_id': inv.account_id.id,
    #                 'branch_id': inv.branch_id.id,
    #                 'date_maturity': inv.date_due,
    #                 'amount_currency': diff_currency and total_currency,
    #                 'currency_id': diff_currency and inv.currency_id.id,
    #                 'invoice_id': inv.id
    #             })
    #         # To achieve direct billing without affecting parent partnet ledger, use the invoice payer_id field if it is set.
    #         # Using the invoice payer field instead of the commercial partner will ensure the invoice will not be billed to parent partner
    #         part = inv.payer_id if inv.payer_id else self.env['res.partner']._find_accounting_partner(
    #             inv.partner_id)
    #         line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
    #         line = inv.group_lines(iml, line)
    #         line = inv.finalize_invoice_move_lines(line)
    #         date = inv.date or inv.date_invoice
    #         move_vals = {
    #             'ref': inv.reference,
    #             'line_ids': line,
    #             'journal_id': inv.journal_id.id,
    #             'date': date,
    #             'branch_id': inv.branch_id.id,
    #             'narration': inv.comment,
    #         }
    #         move = account_move.create(move_vals)
    #         for line in move.line_ids:
    #             if inv.branch_id.id:
    #                 line.branch_id = inv.branch_id.id
    #         # Pass invoice in method post: used if you want to get the same
    #         # account move reference when creating the same invoice after a cancelled one:
    #         move.post(invoice=inv)
    #         # make the invoice point to that move
    #         vals = {
    #             'move_id': move.id,
    #             'date': date,
    #             'move_name': move.name,
    #         }
    #         inv.write(vals)
    #     return True


# class AccountInvoiceLine(models.Model):
#     _inherit = 'account.move.line'
#     branch_id = fields.Many2one('multi.branch', string='MDA Sector',
#                                 default=lambda self: self.invoice_id.branch_id.id)

#     def _prepare_invoice_line(self):
#         data = super(AccountInvoiceLine, self)._prepare_invoice_line()
#         data.update({'branch_id': self.branch_id.id})
#         return data


# class AccountInvoiceTax(models.Model):
#     _inherit = "account.move.tax"
#     branch_id = fields.Many2one('multi.branch', string='MDA Sector',
#                                 default=lambda self: self.env.user.branch_id.id, required=False)


 
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    branch_id = fields.Many2one('multi.branch', string='MDA Sector',
                                default=lambda self: self._get_move_branch(), required=False,)
     
    def _prepare_invoice_line(self):
        data = super(AccountMoveLine, self)._prepare_invoice_line()
        data.update({'branch_id': self.branch_id.id})
        return data
    
    # def reconcile(self):
    #     res = super(AccountMoveLine, self).reconcile()
    #     res.exchange_move_id.update({'branch_id' : self.branch_id.id})
    #     return res
    
    # def _prepare_exchange_difference_move_vals(self, amounts_list, company=None, exchange_date=None):
    #     res = super(AccountMoveLine, self)._prepare_exchange_difference_move_vals(amounts_list, company, exchange_date)
    #     res['move_vals']['branch_id'] = self.move_id.branch_id.id 
    #     # _logger.info(f" ttttttt si {self.move_id} {res['move_vals']}")
    #     # raise ValidationError(self.id)
    #     return res
    
    @api.model
    def _create_exchange_difference_move(self, exchange_diff_vals):
        """ Create the exchange difference journal entry on the current journal items.
        :param exchange_diff_vals:  The current vals of the exchange difference journal entry created by the
                                    '_prepare_exchange_difference_move_vals' method.
        :return:                    An account.move record.
        """
        move_vals = exchange_diff_vals['move_vals']
        # move_vals['branch_id'] = self.branch_id.id
        # raise ValidationError(self.branch_id.id)
        if not move_vals['line_ids']:
            return

        # Check the configuration of the exchange difference journal.
        journal = self.env['account.journal'].browse(move_vals['journal_id'])
        if not journal:
            raise UserError(_(
                "You should configure the 'Exchange Gain or Loss Journal' in your company settings, to manage"
                " automatically the booking of accounting entries related to differences between exchange rates."
            ))
        if not journal.company_id.expense_currency_exchange_account_id:
            raise UserError(_(
                "You should configure the 'Loss Exchange Rate Account' in your company settings, to manage"
                " automatically the booking of accounting entries related to differences between exchange rates."
            ))
        if not journal.company_id.income_currency_exchange_account_id.id:
            raise UserError(_(
                "You should configure the 'Gain Exchange Rate Account' in your company settings, to manage"
                " automatically the booking of accounting entries related to differences between exchange rates."
            ))

        # Create the move.
        exchange_move = self.env['account.move'].with_context(skip_invoice_sync=True).create(move_vals)
        exchange_move._post(soft=False)

        # Reconcile lines to the newly created exchange difference journal entry by creating more partials.
        for source_line, sequence in exchange_diff_vals['to_reconcile']:
            exchange_diff_line = exchange_move.line_ids[sequence]
            (exchange_diff_line + source_line).with_context(no_exchange_difference=True).reconcile()

        return exchange_move
 
    def _get_move_branch(self):
        branch_id = self.move_id.branch_id.id if self.move_id.branch_id else self.env.user.branch_id.id
        return branch_id

    # @api.model
    # def _query_get(self, domain=None):
    #     self.check_access_rights('read')

    #     context = dict(self._context or {})
    #     domain = domain or []
    #     if not isinstance(domain, (list, tuple)):
    #         domain = safe_eval(domain)

    #     date_field = 'date'
    #     if context.get('aged_balance'):
    #         date_field = 'date_maturity'
    #     branch_id = 'branch_id'
    #     if context.get('branch_id'):
    #         domain += [(branch_id, '=', context['branch_id'])]
    #     if context.get('date_to'):
    #         domain += [(date_field, '<=', context['date_to'])]
    #     if context.get('date_from'):
    #         if not context.get('strict_range'):
    #             domain += ['|', (date_field, '>=', context['date_from']),
    #                        ('account_id.user_type_id.include_initial_balance', '=', True)]
    #         elif context.get('initial_bal'):
    #             domain += [(date_field, '<', context['date_from'])]
    #         else:
    #             domain += [(date_field, '>=', context['date_from'])]

    #     if context.get('journal_ids'):
    #         domain += [('journal_id', 'in', context['journal_ids'])]

    #     state = context.get('state')
    #     if state and state.lower() != 'all':
    #         domain += [('move_id.state', '=', state)]

    #     if context.get('company_id'):
    #         domain += [('company_id', '=', context['company_id'])]

    #     if 'company_ids' in context:
    #         domain += [('company_id', 'in', context['company_ids'])]

    #     if context.get('reconcile_date'):
    #         domain += ['|', ('reconciled', '=', False), '|', ('matched_debit_ids.max_date', '>',
    #                                                           context['reconcile_date']), ('matched_credit_ids.max_date', '>', context['reconcile_date'])]

    #     if context.get('account_tag_ids'):
    #         domain += [('account_id.tag_ids', 'in',
    #                     context['account_tag_ids'].ids)]

    #     if context.get('account_ids'):
    #         domain += [('account_id', 'in', context['account_ids'].ids)]

    #     if context.get('analytic_tag_ids'):
    #         domain += [('analytic_tag_ids', 'in',
    #                     context['analytic_tag_ids'].ids)]

    #     if context.get('analytic_account_ids'):
    #         domain += [('analytic_account_id', 'in',
    #                     context['analytic_account_ids'].ids)]

    #     if context.get('partner_ids'):
    #         domain += [('partner_id', 'in', context['partner_ids'].ids)]

    #     if context.get('partner_categories'):
    #         domain += [('partner_id.category_id', 'in',
    #                     context['partner_categories'].ids)]

    #     where_clause = ""
    #     where_clause_params = []
    #     tables = ''
    #     if domain:
    #         query = self._where_calc(domain)

    #         # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
    #         self._apply_ir_rules(query)

    #         tables, where_clause, where_clause_params = query.get_sql()
    #     return tables, where_clause, where_clause_params




# class AccountAnalyticDefault(models.Model):
#     _inherit = "account.analytic.default"
#     branch_id = fields.Many2one(
#         'multi.branch', 'MDA Sector', default=lambda self: self.env.user.partner_id.branch_id.id)

    # @api.model
    # def account_get(self, product_id=None, partner_id=None, user_id=None, date=None, company_id=None, branch_id=None):
    #     domain = []
    #     if product_id:
    #         domain += ['|', ('product_id', '=', product_id)]
    #     domain += [('product_id', '=', False)]
    #     if partner_id:
    #         domain += ['|', ('partner_id', '=', partner_id)]
    #     domain += [('partner_id', '=', False)]
    #     if company_id:
    #         domain += ['|', ('company_id', '=', company_id)]
    #     domain += [('company_id', '=', False)]
    #     if branch_id:
    #         domain += ['|', ('branch_id', '=', branch_id)]
    #     domain += [('branch_id', '=', False)]
    #     if user_id:
    #         domain += ['|', ('user_id', '=', user_id)]
    #     domain += [('user_id', '=', False)]
    #     if date:
    #         domain += ['|', ('date_start', '<=', date), ('date_start', '=', False)]
    #         domain += ['|', ('date_stop', '>=', date), ('date_stop', '=', False)]
    #     best_index = -1
    #     res = self.env['account.analytic.default']
    #     for rec in self.search(domain):
    #         index = 0
    #         if rec.product_id: index += 1
    #         if rec.partner_id: index += 1
    #         if rec.company_id: index += 1
    #         if rec.user_id: index += 1
    #         if rec.date_start: index += 1
    #         if rec.date_stop: index += 1
    #         if index > best_index:
    #             res = rec
    #             best_index = index
    #     return res


# class AccountAssetAsset(models.Model):
#     _inherit = "account.asset.asset"
#     branch_id = fields.Many2one('multi.branch', string='MDA Sector', default=lambda self: self.env.user.partner_id.branch_id.id)


# class AccountVoucher(models.Model):
#     _inherit = "account.voucher"
#     branch_id = fields.Many2one('multi.branch', string='MDA Sector',
#                                 default=lambda self: self.env.user.partner_id.branch_id.id)

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    branch_id = fields.Many2one('multi.branch', string='MDA Sector',
                                required=False) 
    bank_partner_id = fields.Many2one(
        'res.partner', 
        string='Recipient Bank-', 
        domain="[('is_bank', '=', True)]",
        help="Select the bank to send payment schedule"
        )
    bank_partner_account = fields.Char(
        string='Recipient Account Number', 
        )   
    
    @api.depends('payment_type', 'company_id', 'can_edit_wizard')
    def _compute_available_journal_ids(self):
        # raise ValidationError('ebbuka')
        Journals = self.env['account.journal'].sudo()
        for wizard in self:
            # if wizard.can_edit_wizard:
            #     batch = wizard._get_batches()[0]
            #     wizard.available_journal_ids = wizard._get_batch_available_journals(batch)
            # else:
            domain =[
                ('company_id', '=', wizard.company_id.id),
                ('type', 'in', ('bank', 'cash')),
            ]
            account_major_user = self.env.user.has_group('ik_multi_branch.account_major_user')
            branch_ids = [rec.id for rec in self.env.user.branch_ids if rec] + [self.env.user.branch_id.id]
            journal_ids = []
            for journal in Journals.search([]):
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
                    ('company_id', '=', wizard.company_id.id),
                    ('type', 'in', ('bank','cash')),
                    ('id', 'in', journal_ids)
                ]
            wizard.available_journal_ids = self.env['account.journal'].search(domain)

    @api.model
    def get_move_branch(self):
        return {
            'branch_id': self.line_ids[0].move_id.branch_id.id
        }
    
    def action_create_payments(self):
        payments = self._create_payments()
        payments.update({
            'branch_id': self.branch_id.id 
        })

        if self._context.get('dont_redirect_to_payments'):
            return True

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action
    

class AccountPayment(models.Model):
    _inherit = "account.payment"

    branch_id = fields.Many2one('multi.branch', string='MDA Sector',
                                required=False, default=lambda self: self.env.user.branch_id.id)
    

    # def _get_move_branch(self):
    #     branch_ids = self.invoice_ids.mapped('branch_id')
    #     #branch_id = branch_ids[0] if len(branch_ids) else self.env.user.partner_id.branch_id.id
    #     return branch_ids[0]

    def _get_counterpart_move_line_vals(self, invoice=False):

        if self.payment_type == 'transfer':
            name = self.name
        else:
            name = ''
            if self.partner_type == 'customer':
                if self.payment_type == 'inbound':
                    name += _("Customer Payment")
                elif self.payment_type == 'outbound':
                    name += _("Customer Refund")
            elif self.partner_type == 'supplier':
                if self.payment_type == 'inbound':
                    name += _("Vendor Refund")
                elif self.payment_type == 'outbound':
                    name += _("Vendor Payment")
            if invoice:
                name += ': '
                for inv in invoice:
                    if inv.move_id:
                        name += inv.number + ', '
                name = name[:len(name)-2]
        return {
            'name': name,
            'account_id': self.destination_account_id.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
            'payment_id': self.id,
            'branch_id': self.branch_id.id or self.env.user.partner_id.branch_id.id,
        }

    def _get_liquidity_move_line_vals(self, amount):
        user_pool = self.env['res.users']
        res = super(AccountPayment, self)._get_liquidity_move_line_vals(amount)
        res.update({'branch_id': self.branch_id.id})
        return res


# class AccountInvoiceRefund(models.TransientModel):
#     _inherit = 'account.move.refund'
#
#     @api.model
#     def _get_invoice_refund_default_branch(self):
#         if self._context.get('active_id'):
#             ids = self._context.get('active_id')
#             user_pool = self.env['account.move']
#             branch_id = user_pool.browse(self.env.uid).branch_id and user_pool.browse(
#                 ids).branch_id.id or False
#             return branch_id
#
#     branch_id = fields.Many2one(
#         'multi.branch', 'MDA Sector', default=_get_invoice_refund_default_branch, required=False)
#

class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'
    branch_id = fields.Many2one('multi.branch', 'MDA Sector',
                                default=lambda self: self.env['res.partner']._branch_default_get())


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'
    branch_id = fields.Many2one(
        'multi.branch', 'MDA Sector', related='statement_id.branch_id')

    # def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
    #     """ Match statement lines with existing payments (eg. checks) and/or payables/receivables (eg. invoices and credit notes) and/or new move lines (eg. write-offs).
    #         If any new journal item needs to be created (via new_aml_dicts or counterpart_aml_dicts), a new journal entry will be created and will contain those
    #         items, as well as a journal item for the bank statement line.
    #         Finally, mark the statement line as reconciled by putting the matched moves ids in the column journal_entry_ids.

    #         :param self: browse collection of records that are supposed to have no accounting entries already linked.
    #         :param (list of dicts) counterpart_aml_dicts: move lines to create to reconcile with existing payables/receivables.
    #             The expected keys are :
    #             - 'name'
    #             - 'debit'
    #             - 'credit'
    #             - 'move_line'
    #                 # The move line to reconcile (partially if specified debit/credit is lower than move line's credit/debit)

    #         :param (list of recordsets) payment_aml_rec: recordset move lines representing existing payments (which are already fully reconciled)

    #         :param (list of dicts) new_aml_dicts: move lines to create. The expected keys are :
    #             - 'name'
    #             - 'debit'
    #             - 'credit'
    #             - 'account_id'
    #             - (optional) 'tax_ids'
    #             - (optional) Other account.move.line fields like analytic_account_id or analytics_id

    #         :returns: The journal entries with which the transaction was matched. If there was at least an entry in counterpart_aml_dicts or new_aml_dicts, this list contains
    #             the move created by the reconciliation, containing entries for the statement.line (1), the counterpart move lines (0..*) and the new move lines (0..*).
    #     """
    #     payable_account_type = self.env.ref('account.data_account_type_payable')
    #     receivable_account_type = self.env.ref('account.data_account_type_receivable')
    #     counterpart_aml_dicts = counterpart_aml_dicts or []
    #     payment_aml_rec = payment_aml_rec or self.env['account.move.line']
    #     new_aml_dicts = new_aml_dicts or []

    #     aml_obj = self.env['account.move.line']

    #     company_currency = self.journal_id.company_id.currency_id
    #     statement_currency = self.journal_id.currency_id or company_currency
    #     st_line_currency = self.currency_id or statement_currency

    #     counterpart_moves = self.env['account.move']

    #     # Check and prepare received data
    #     if any(rec.statement_id for rec in payment_aml_rec):
    #         raise UserError(_('A selected move line was already reconciled.'))
    #     for aml_dict in counterpart_aml_dicts:
    #         if aml_dict['move_line'].reconciled:
    #             raise UserError(_('A selected move line was already reconciled.'))
    #         if isinstance(aml_dict['move_line'], pycompat.integer_types):
    #             aml_dict['move_line'] = aml_obj.browse(aml_dict['move_line'])

    #     account_types = self.env['account.account.type']
    #     for aml_dict in (counterpart_aml_dicts + new_aml_dicts):
    #         if aml_dict.get('tax_ids') and isinstance(aml_dict['tax_ids'][0], pycompat.integer_types):
    #             # Transform the value in the format required for One2many and Many2many fields
    #             aml_dict['tax_ids'] = [(4, id, None) for id in aml_dict['tax_ids']]

    #         user_type_id = self.env['account.account'].browse(aml_dict.get('account_id')).user_type_id
    #         if user_type_id in [payable_account_type, receivable_account_type] and user_type_id not in account_types:
    #             account_types |= user_type_id
    #     if any(line.journal_entry_ids for line in self):
    #         raise UserError(_('A selected statement line was already reconciled with an account move.'))

    #     # Fully reconciled moves are just linked to the bank statement
    #     total = self.amount
    #     currency = self.currency_id or statement_currency
    #     for aml_rec in payment_aml_rec:
    #         balance = aml_rec.amount_currency if aml_rec.currency_id else aml_rec.balance
    #         aml_currency = aml_rec.currency_id or aml_rec.company_currency_id
    #         total -= aml_currency._convert(balance, currency, aml_rec.company_id, aml_rec.date)
    #         aml_rec.write({'branch_id': self.branch_id.id})
    #         aml_rec.with_context(check_move_validity=False).write({'statement_line_id': self.id})
    #         counterpart_moves = (counterpart_moves | aml_rec.move_id)
    #         if aml_rec.journal_id.post_at == 'bank_rec' and aml_rec.payment_id and aml_rec.move_id.state == 'draft':
    #             # In case the journal is set to only post payments when performing bank
    #             # reconciliation, we modify its date and post it.
    #             aml_rec.move_id.date = self.date
    #             aml_rec.payment_id.payment_date = self.date
    #             aml_rec.move_id.post()
    #             # We check the paid status of the invoices reconciled with this payment
    #             for invoice in aml_rec.payment_id.reconciled_invoice_ids:
    #                 self._check_invoice_state(invoice)

    #     # Create move line(s). Either matching an existing journal entry (eg. invoice), in which
    #     # case we reconcile the existing and the new move lines together, or being a write-off.
    #     if counterpart_aml_dicts or new_aml_dicts:
    #         st_line_currency = self.currency_id or statement_currency
    #         st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False

    #         # Create the move
    #         self.sequence = self.statement_id.line_ids.ids.index(self.id) + 1
    #         move_vals = self._prepare_reconciliation_move(self.statement_id.name)
    #         move_vals.update({'branch_id': self.branch_id.id})
    #         move = self.env['account.move'].create(move_vals)
    #         counterpart_moves = (counterpart_moves | move)

    #         # Create The payment
    #         payment = self.env['account.payment']
    #         partner_id = self.partner_id or (aml_dict.get('move_line') and aml_dict['move_line'].partner_id) or self.env['res.partner']
    #         if abs(total)>0.00001:
    #             partner_type = False
    #             if partner_id and len(account_types) == 1:
    #                 partner_type = 'customer' if account_types == receivable_account_type else 'supplier'
    #             if partner_id and not partner_type:
    #                 if total < 0:
    #                     partner_type = 'supplier'
    #                 else:
    #                     partner_type = 'customer'

    #             payment_methods = (total>0) and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
    #             currency = self.journal_id.currency_id or self.company_id.currency_id
    #             payment = self.env['account.payment'].create({
    #                 'payment_method_id': payment_methods and payment_methods[0].id or False,
    #                 'payment_type': total >0 and 'inbound' or 'outbound',
    #                 'partner_id': partner_id.id,
    #                 'branch_id': self.branch_id.id,
    #                 'partner_type': partner_type,
    #                 'journal_id': self.statement_id.journal_id.id,
    #                 'payment_date': self.date,
    #                 'state': 'reconciled',
    #                 'currency_id': currency.id,
    #                 'amount': abs(total),
    #                 'ref': self._get_communication(payment_methods[0] if payment_methods else False),
    #                 'name': self.statement_id.name or _("Bank Statement %s") %  self.date,
    #             })

    #         # Complete dicts to create both counterpart move lines and write-offs
    #         to_create = (counterpart_aml_dicts + new_aml_dicts)
    #         company = self.company_id
    #         date = self.date or fields.Date.today()
    #         for aml_dict in to_create:
    #             aml_dict['move_id'] = move.id
    #             aml_dict['branch_id'] = self.branch_id.id
    #             aml_dict['partner_id'] = self.partner_id.id
    #             aml_dict['statement_line_id'] = self.id
    #             if st_line_currency.id != company_currency.id:
    #                 aml_dict['amount_currency'] = aml_dict['debit'] - aml_dict['credit']
    #                 aml_dict['currency_id'] = st_line_currency.id
    #                 if self.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
    #                     # Statement is in company currency but the transaction is in foreign currency
    #                     aml_dict['debit'] = company_currency.round(aml_dict['debit'] / st_line_currency_rate)
    #                     aml_dict['credit'] = company_currency.round(aml_dict['credit'] / st_line_currency_rate)
    #                 elif self.currency_id and st_line_currency_rate:
    #                     # Statement is in foreign currency and the transaction is in another one
    #                     aml_dict['debit'] = statement_currency._convert(aml_dict['debit'] / st_line_currency_rate, company_currency, company, date)
    #                     aml_dict['credit'] = statement_currency._convert(aml_dict['credit'] / st_line_currency_rate, company_currency, company, date)
    #                 else:
    #                     # Statement is in foreign currency and no extra currency is given for the transaction
    #                     aml_dict['debit'] = st_line_currency._convert(aml_dict['debit'], company_currency, company, date)
    #                     aml_dict['credit'] = st_line_currency._convert(aml_dict['credit'], company_currency, company, date)
    #             elif statement_currency.id != company_currency.id:
    #                 # Statement is in foreign currency but the transaction is in company currency
    #                 prorata_factor = (aml_dict['debit'] - aml_dict['credit']) / self.amount_currency
    #                 aml_dict['amount_currency'] = prorata_factor * self.amount
    #                 aml_dict['currency_id'] = statement_currency.id

    #         # Create write-offs
    #         for aml_dict in new_aml_dicts:
    #             aml_dict['payment_id'] = payment and payment.id or False
    #             aml_obj.with_context(check_move_validity=False).create(aml_dict)

    #         # Create counterpart move lines and reconcile them
    #         for aml_dict in counterpart_aml_dicts:
    #             if aml_dict['move_line'].payment_id:
    #                 aml_dict['move_line'].write({'statement_line_id': self.id})
    #             if aml_dict['move_line'].partner_id.id:
    #                 aml_dict['partner_id'] = aml_dict['move_line'].partner_id.id
    #             aml_dict['account_id'] = aml_dict['move_line'].account_id.id
    #             aml_dict['payment_id'] = payment and payment.id or False

    #             counterpart_move_line = aml_dict.pop('move_line')
    #             new_aml = aml_obj.with_context(check_move_validity=False).create(aml_dict)

    #             (new_aml | counterpart_move_line).reconcile()

    #             self._check_invoice_state(counterpart_move_line.invoice_id)

    #         # Balance the move
    #         st_line_amount = -sum([x.balance for x in move.line_ids])
    #         aml_dict = self._prepare_reconciliation_move_line(move, st_line_amount)
    #         aml_dict['payment_id'] = payment and payment.id or False
    #         aml_obj.with_context(check_move_validity=False).create(aml_dict)

    #         move.post()
    #         #record the move name on the statement line to be able to retrieve it in case of unreconciliation
    #         self.write({'move_name': move.name})
    #         payment and payment.write({'payment_reference': move.name})
    #     elif self.move_name:
    #         raise UserError(_('Operation not allowed. Since your statement line already received a number (%s), you cannot reconcile it entirely with existing journal entries otherwise it would make a gap in the numbering. You should book an entry and make a regular revert of it in case you want to cancel it.') % (self.move_name))

    #     #create the res.partner.bank if needed
    #     if self.account_number and self.partner_id and not self.bank_account_id:
    #         # Search bank account without partner to handle the case the res.partner.bank already exists but is set
    #         # on a different partner.
    #         bank_account = self.env['res.partner.bank'].search([('acc_number', '=', self.account_number)])
    #         if not bank_account:
    #             bank_account = self.env['res.partner.bank'].create({
    #                 'acc_number': self.account_number, 'partner_id': self.partner_id.id
    #             })
    #         self.bank_account_id = bank_account

    #     counterpart_moves._check_balanced()
    #     return counterpart_moves

    def _check_invoice_state(self, invoice):
        if invoice.state == 'in_payment' and all([payment.state == 'reconciled' for payment in invoice.mapped('payment_move_line_ids.payment_id')]):
            invoice.write({'state': 'paid'})
