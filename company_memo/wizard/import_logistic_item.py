# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import fields, models, api, _
import io
import xlwt
from datetime import datetime, timedelta
import base64
from dateutil.parser import parse
import ast 
import xlrd
from xlrd import open_workbook
import logging
_logger = logging.getLogger(__name__)


class ImportLogisticsWizard(models.Model):
    _name = "import.logistic_wizard"
    _description = 'Model used to import logistic items'

    name = fields.Char(string="Title")
    schedule_date = fields.Date(
        'Schedule Date', 
        )
    import_date = fields.Date(
        'Import Date', 
        default=fields.Date.today()
        )
    assigned_user = fields.Many2one(
        'res.users', 
        string="Responsible User"
        )
    picking_type_id = fields.Many2one(
        'stock.picking.type', 
        string="Move type"
        )
    memo_id = fields.Many2one(
        'memo.model', 
        string="Related Project"
        )
    partner_recieved_from = fields.Many2one(
        'res.partner', 
        string="Recieved from?"
        )
    active = fields.Boolean(
        string="Active",
        default=True
        )
    index = fields.Integer(
        string="Index",
        default=1
        )
    excel_file = fields.Binary('Download Excel file', readonly=False)
    filename = fields.Char('Excel File')

    def import_logistic_items(self):
        if self.excel_file:
            file_datas = base64.b64decode(self.excel_file)
            workbook = xlrd.open_workbook(file_contents=file_datas)
            sheet_index = int(self.index) if self.index else 0
            sheet = workbook.sheet_by_index(1)
            data = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
            data.pop(0)
            file_data = data
        else:
            raise ValidationError('Please select .xls file')
        
        errors = ['The Following messages occurred']
        unimport_count, count = 0, 0
        success_records = []
        unsuccess_records = [] 

        def get_location_id(location_code):
            location = self.env['stock.location'].search([
                    '|', ('code', '=', location_code), ('name', '=', location_code)], limit=1)
            return location or False

        stock_picking = self.env['stock.picking'].search({
                'scheduled_date': self.schedule_date,
                'picking_type_id': self.picking_type_id.id,
                'origin': self.memo_id.code,
                'memo_id': self.id,
                'partner_id': self.partner_recieved_from.id
        })
        def get_product_id(code, name=False):
            if code or name: 
                product_id = self.env['product.product'].search([
                    '|', ('default_code', '=', code),
                    ('name', '=', name),
                ])
                return product_id if product_id else False
            else:
                return False
         
        stock_picking = self.env['stock.picking'].search({
                'scheduled_date': self.schedule_date,
                'picking_type_id': self.picking_type_id.id,
                'origin': self.memo_id.code,
                'memo_id': self.id,
                'partner_id': self.partner_recieved_from.id
        })
        for cnt, row in enumerate(file_data, 1):  
            product_id = get_product_id(row[1],row[2])
            source_location_id = get_location_id(row[4])
            dest_location_id = get_location_id(row[5])
            if not any([source_location_id, dest_location_id, product_id]):
                unsuccess_records.append(f'Product Code {str(row[1])} or name {str(row[2])}/ Source / destination location with code {str(row[4])}, {str(row[5])} not found')
            else:
                headers = [
                'S/N', # 0
                'Product code', # 1
                'Product Name', # 2
                'Quantity moved', # 3
                'Source Warehouse Code / Name', # 4
                'Destination Warehouse Code / Name', # 5
                ]
                # stock_picking_type_out = self.env.ref('stock.picking_type_out')
                stock_line = stock_picking.write({'move_ids_without_package': [(0, 0, {
                                'name': self.memo_id.code, 
                                'picking_type_id': self.picking_type_id.id,
                                'location_id': source_location_id.id,
                                'location_dest_id': dest_location_id.id,
                                'product_id': product_id.id,
                                'product_uom_qty': row[3],
                                'date_deadline': self.schedule_date or fields.Date.today(),
                            })]
                }) 
                self.memo_id.write({
                    'logistic_item_ids': [(0, 0, 
                                           {'product_id': product_id.id,
                                            'memo_id': self.memo_id.id,
                                            'source_location_id': source_location_id.id,
                                            'destination_location_id': dest_location_id.id,
                                            'stock_picking_id': stock_picking.id
                                            }
                                        )]
                })
                count += 1
                success_records.append(f'Line {cnt} - {stock_line.product_id.name}')
        errors.append('Successful Import(s): '+str(count)+' Record(s): See Records Below \n {}'.format(success_records))
        errors.append('Unsuccessful Import(s): '+str(unsuccess_records)+' Record(s)')
        if len(errors) > 1:
            message = '\n'.join(errors)
            return self.confirm_notification(message)
    
def confirm_notification(self,popup_message):
    view = self.env.ref('company_memo.memo_confirmation_dialog_view')
    view_id = view and view.id or False
    context = dict(self._context or {})
    context['message'] = popup_message
    return {
            'name':'Message!',
            'type':'ir.actions.act_window',
            'view_type':'form',
            'res_model':'memo.confirmation.dialog',
            'views':[(view.id, 'form')],
            'view_id':view.id,
            'target':'new',
            'context':context,
            }



    