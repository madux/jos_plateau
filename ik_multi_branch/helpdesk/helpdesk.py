# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HelpdeskTeam(models.Model):
    _inherit = 'helpdesk.team'
    branch_id = fields.Many2one('multi.branch', 'MDA Sector', default=lambda self: self.env['res.partner']._branch_default_get(), index=True)

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'
    branch_id = fields.Many2one('multi.branch', string='MDA Sector', readonly=True, default=lambda self: self.env['res.partner']._branch_default_get(), index=True)
class HelpdeskSLA(models.Model):
    _inherit = "helpdesk.sla"
    branch_id = fields.Many2one('multi.branch', string='MDA Sector', readonly=True, default=lambda self: self.env['res.partner']._branch_default_get())