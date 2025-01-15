# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from collections import defaultdict
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    branch_id = fields.Many2one('multi.branch', 'MDA Sector', default=lambda self: self.env['res.partner']._branch_default_get())


class StockQuant(models.Model):
    _inherit = "stock.quant"
    branch_id = fields.Many2one('multi.branch', 'MDA Sector', default=lambda self: self.env['res.partner']._branch_default_get())


# class InventoryLine(models.Model):
#     _inherit = "stock.inventory.line"
#     branch_id = fields.Many2one('multi.branch', 'MDA Sector', default=lambda self: self.env['res.partner']._branch_default_get())

#     def _get_move_values(self, qty, location_id, location_dest_id, out):
#         res = super(InventoryLine, self)._get_move_values(qty, location_id, location_dest_id, out)
#         res.update({'branch_id':self.inventory_id.branch_id.id})
#         return res


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    branch_id = fields.Many2one('multi.branch', string='MDA Sector', default=lambda self: self.env.user.branch_id.id, required=False)
    state_ids = fields.Many2many('res.country.state', string='States')
    city = fields.Char(string="City", required=False, help="Warehouse location city")

    @api.constrains('state_ids')
    def _check_states(self):
        state_ids = self.state_ids.ids
        for warehouse in self.env['stock.warehouse'].sudo().search([]):
            w_states = warehouse.state_ids.ids
            if self.id != warehouse.id:
                for state_id in state_ids:
                    if state_id in w_states:
                        raise ValidationError('A state must be mapped to only one warehouse!')

    # def _get_global_route_rules_values(self):
    #     rec = super(StockWarehouse, self)._get_global_route_rules_values()
    #     rec['mto_pull_id']['create_values'].update({'branch_id': self.branch_id.id})
    #     return rec

    # def _get_routes_values(self):
    #     rec = super(StockWarehouse, self)._get_routes_values()
    #     rec['reception_route_id']['route_create_values'].update({'branch_id': self.branch_id.id})
    #     rec['delivery_route_id']['route_create_values'].update({'branch_id': self.branch_id.id})
    #     rec['crossdock_route_id']['route_create_values'].update({'branch_id': self.branch_id.id})
    #     return rec

    # def get_rules_dict(self):
    #     """ Define the rules source/destination locations, picking_type and
    #     action needed for each warehouse route configuration.
    #     """
    #     customer_loc, supplier_loc = self._get_partner_locations()
    #     return {
    #         warehouse.id: {
    #             'one_step': [],
    #             'two_steps': [self.Routing(warehouse.wh_input_stock_loc_id, warehouse.lot_stock_id, warehouse.int_type_id, 'pull_push')],
    #             'three_steps': [
    #                 self.Routing(warehouse.wh_input_stock_loc_id, warehouse.wh_qc_stock_loc_id, warehouse.int_type_id, 'pull_push'),
    #                 self.Routing(warehouse.wh_qc_stock_loc_id, warehouse.lot_stock_id, warehouse.int_type_id, 'pull_push')],
    #             'crossdock': [
    #                 self.Routing(warehouse.wh_input_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.int_type_id, 'pull'),
    #                 self.Routing(warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id, 'pull')],
    #             'ship_only': [self.Routing(warehouse.lot_stock_id, customer_loc, warehouse.out_type_id, 'pull')],
    #             'pick_ship': [
    #                 self.Routing(warehouse.lot_stock_id, warehouse.wh_output_stock_loc_id, warehouse.pick_type_id, 'pull'),
    #                 self.Routing(warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id, 'pull')],
    #             'pick_pack_ship': [
    #                 self.Routing(warehouse.lot_stock_id, warehouse.wh_pack_stock_loc_id, warehouse.pick_type_id, 'pull'),
    #                 self.Routing(warehouse.wh_pack_stock_loc_id, warehouse.wh_output_stock_loc_id, warehouse.pack_type_id, 'pull'),
    #                 self.Routing(warehouse.wh_output_stock_loc_id, customer_loc, warehouse.out_type_id, 'pull')],
    #             'company_id': warehouse.company_id.id,
    #             'branch_id': warehouse.branch_id.id,
    #         } for warehouse in self
    #     }
    
    def update_lot_stock_id(self):
        for rec in self:
            lot_stock = self.env['stock.location'].search([('id', '=', rec.lot_stock_id.id)], limit=1)
            lot_stock.write({'branch_id': rec.branch_id.id})

    # Update warehouse internal location with the warehouse current branch
    @api.model 
    def create(self, vals):
        res = super(StockWarehouse, self).create(vals)
        if self.branch_id:
            self.update_lot_stock_id()
        return res

    # Update warehouse internal location with the warehouse current branch
    def write(self, vals):
        res = super(StockWarehouse, self).write(vals)
        if self.branch_id:
            self.update_lot_stock_id()
        return res

    # def _create_or_update_route(self):
    #     """ Create or update the warehouse's routes.
    #     _get_routes_values method return a dict with:
    #         - route field name (e.g: crossdock_route_id).
    #         - field that trigger an update on the route (key 'depends').
    #         - routing_key used in order to find rules contained in the route.
    #         - create values.
    #         - update values when a field in depends is modified.
    #         - rules default values.
    #     This method do an iteration on each route returned and update/create
    #     them. In order to update the rules contained in the route it will
    #     use the get_rules_dict that return a dict:
    #         - a receptions/delivery,... step value as key (e.g  'pick_ship')
    #         - a list of routing object that represents the rules needed to
    #         fullfil the pupose of the route.
    #     The routing_key from _get_routes_values is match with the get_rules_dict
    #     key in order to create/update the rules in the route
    #     (_find_existing_rule_or_create method is responsible for this part).
    #     """
    #     # Create routes and active/create their related rules.
    #     routes = []
    #     rules_dict = self.get_rules_dict()
    #     for route_field, route_data in self._get_routes_values().items():
    #         # If the route exists update it
    #         if self[route_field]:
    #             route = self[route_field]
    #             if 'route_update_values' in route_data:
    #                 route.write(route_data['route_update_values'])
    #             route.rule_ids.write({'active': False})
    #         # Create the route
    #         else:
    #             if 'route_update_values' in route_data:
    #                 route_data['route_create_values'].update(route_data['route_update_values'])
    #             route = self.env['stock.route'].create(route_data['route_create_values'])
    #             self[route_field] = route
    #         # Get rules needed for the route
    #         routing_key = route_data.get('routing_key')
    #         rules = rules_dict.get(self.id).get(routing_key)
    #         if 'rules_values' in route_data:
    #             route_data['rules_values'].update({'route_id': route.id})
    #         else:
    #             route_data['rules_values'] = {'route_id': route.id}
    #         rules_list = self._get_rule_values(
    #             rules, values=route_data['rules_values'])
    #         # Create/Active rules
    #         self._find_existing_rule_or_create(rules_list)
    #         if route_data['route_create_values'].get('warehouse_selectable', False) or route_data['route_update_values'].get('warehouse_selectable', False):
    #             routes.append(self[route_field])
    #     return {
    #         'route_ids': [(4, route.id) for route in routes],
    #     }

    # def _get_rule_values(self, route_values, values=None, name_suffix=''):
    #     first_rule = True
    #     rules_list = []
    #     if route_values:
    #         for routing in route_values:
    #             route_rule_values = {
    #                 'name': self._format_rulename(routing.from_loc, routing.dest_loc, name_suffix),
    #                 'location_src_id': routing.from_loc.id,
    #                 'location_id': routing.dest_loc.id,
    #                 'action': routing.action,
    #                 'auto': 'manual',
    #                 'picking_type_id': routing.picking_type.id,
    #                 'procure_method': first_rule and 'make_to_stock' or 'make_to_order',
    #                 'warehouse_id': self.id,
    #                 'company_id': self.company_id.id,
    #                 'delay_alert': routing.picking_type.code == 'outgoing',
    #             }
    #             route_rule_values.update(values or {})
    #             rules_list.append(route_rule_values)
    #             first_rule = False
    #     if values and values.get('propagate_cancel') and rules_list:
    #         # In case of rules chain with cancel propagation set, we need to stop
    #         # the cancellation for the last step in order to avoid cancelling
    #         # any other move after the chain.
    #         # Example: In the following flow:
    #         # Input -> Quality check -> Stock -> Customer
    #         # We want that cancelling I->GC cancel QC -> S but not S -> C
    #         # which means:
    #         # Input -> Quality check should have propagate_cancel = True
    #         # Quality check -> Stock should have propagate_cancel = False
    #         rules_list[-1]['propagate_cancel'] = False
    #     return rules_list


# class Orderpoint(models.Model):
#     """ Defines Minimum stock rules. """
#     _inherit = "stock.warehouse.orderpoint"
#     branch_id = fields.Many2one('multi.branch', 'MDA Sector', readonly=True, store=True, default=lambda self: self.env['res.partner']._branch_default_get())

#     def _prepare_procurement_values(self, product_qty, date=False, group=False):
#         rec = super(Orderpoint, self)._prepare_procurement_values(product_qty, date, group)
#         rec.update({'branch_id': self.branch_id})
#         return rec


class StockLocation(models.Model):
    _inherit = 'stock.location'
    branch_id = fields.Many2one('multi.branch', 'MDA Sector',)

    
    @api.constrains('branch_id')
    def _check_branch(self):
        for location in self:
            warehouse_obj = self.env['stock.warehouse']
            warehouse_id = warehouse_obj.search(
                ['|', '|', ('wh_input_stock_loc_id', '=', location.id),
                 ('lot_stock_id', '=', location.id),
                 ('wh_output_stock_loc_id', '=', location.id)])
            for warehouse in warehouse_id:
                if location.branch_id != warehouse.branch_id:
                    raise UserError(_('Configuration error\nYou  must select same branch on a location as asssigned on a warehouse configuration.'))


class StockRoute(models.Model):
    _inherit = 'stock.route'
    branch_id = fields.Many2one('multi.branch', string='MDA Sector',)


class StockMove(models.Model):
    _inherit = 'stock.move'
    branch_id = fields.Many2one('multi.branch', string='MDA Sector',)

    def assign_picking(self):
        """ Try to assign the moves to an existing picking that has not been
        reserved yet and has the same procurement group, locations and picking
        type (moves should already have them identical). Otherwise, create a new
        picking to assign them to. """
        Picking = self.env['stock.picking']
        for move in self:
            recompute = False
            picking = Picking.search([
                ('group_id', '=', move.group_id.id),
                ('location_id', '=', move.location_id.id),
                ('location_dest_id', '=', move.location_dest_id.id),
                ('picking_type_id', '=', move.picking_type_id.id),
                ('printed', '=', False),
                ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
            if not picking:
                recompute = True
                picking = Picking.create(move._get_new_picking_values())
                picking.branch_id = move.branch_id.id
            move.write({'picking_id': picking.id})

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        # This method returns a dictionary to provide an easy extension hook to modify the valuation lines (see purchase for an example)
        self.ensure_one()
        debit_line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
            'balance': debit_value,
            'account_id': debit_account_id,
        }

        credit_line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
            'balance': -credit_value,
            'account_id': credit_account_id,
            'branch_id': self.branch_id.id,
        }

        rslt = {'credit_line_vals': credit_line_vals, 'debit_line_vals': debit_line_vals}
        if credit_value != debit_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = debit_value - credit_value
            price_diff_account = self.env.context.get('price_diff_account')
            if not price_diff_account:
                raise UserError(_('Configuration error. Please configure the price difference account on the product or its category to process this operation.'))

            rslt['price_diff_line_vals'] = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'balance': -diff_amount,
                'ref': description,
                'partner_id': partner_id,
                'account_id': price_diff_account.id,
                'branch_id': self.branch_id.id,
            }
        return rslt

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        self.ensure_one()
        AccountMove = self.env['account.move']
        quantity = self.env.context.get('forced_quantity', self.product_qty)
        quantity = quantity if self._is_in() else -1 * quantity

        # Make an informative `ref` on the created account move to differentiate between classic
        # movements, vacuum and edition of past moves.
        ref = self.picking_id.name
        if self.env.context.get('force_valuation_amount'):
            if self.env.context.get('forced_quantity') == 0:
                ref = 'Revaluation of %s (negative inventory)' % ref
            elif self.env.context.get('forced_quantity') is not None:
                ref = 'Correction of %s (modification of past move)' % ref

        move_lines = self.with_context(forced_ref=ref)._prepare_account_move_line(quantity, cost, credit_account_id, debit_account_id, description)
        if move_lines:
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            new_account_move = AccountMove.sudo().create({
                'journal_id': journal_id,
                'line_ids': move_lines,
                'date': date,
                'ref': ref,
                'stock_move_id': self.id,
                'branch_id': self.branch_id.id,
            })
            new_account_move.post()

    def _get_new_picking_values(self):
        rec = super(StockMove, self)._get_new_picking_values()
        rec.update({'branch_id':self.branch_id.id})
        return rec

    def _prepare_procurement_values(self):
        rec = super(StockMove, self)._prepare_procurement_values()
        rec.update({'branch_id':self.branch_id.id})
        return rec


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    branch_id = fields.Many2one('multi.branch', string='MDA Sector', default=lambda self: self.env.user.branch_id.id, required=False)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', compute='_compute_warehouse')
    sign_signature = fields.Binary(string="Digital Signature", compute='_compute_warehouse', groups="base.group_system")

    @api.depends('branch_id')
    def _compute_warehouse(self):
        for rec in self:
            sale_order = self.env['sale.order'].sudo().search([('name', '=', rec.origin)])
            warehouse = sale_order.warehouse_id
            if warehouse:
                rec.warehouse_id = warehouse.id
                user = self.env['res.users'].sudo().search([('partner_id', '=', rec.warehouse_id.partner_id.id)])
                if user:
                    rec.sign_signature = user.sign_signature
                else:
                    rec.sign_signature = False
            else:
                rec.sign_signature = False
                rec.warehouse_id = False


class StockRule(models.Model):
    _inherit = 'stock.rule'
    branch_id = fields.Many2one('multi.branch', 'MDA Sector', default=lambda self: self.env['res.partner']._branch_default_get())

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        rec = super(StockRule, self)._push_prepare_move_copy_values(move_to_copy, new_date)
        rec.update({'branch_id': self.branch_id.id})
        return rec

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
        rec = super(StockRule, self)._get_stock_move_values( product_id, product_qty, product_uom, location_id, name, origin, values, group_id)
        if 'branch_id' not in rec:
            rec.update({'branch_id': self.branch_id.id})
        return rec