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


_logger = logging.getLogger(__name__)

class Memo_Consignmentype(models.Model):
    _name = "memo.consignment.type"
    
    name = fields.Char(string="Consignment type")
    
class Memo_TransportMode(models.Model):
    _name = "memo.transport.mode"
    
    name = fields.Char("Transport mode")
    
class MemoHAZMAT(models.Model):
    _name = "memo.hazmat"
    
    name = fields.Char("HAZMAT")
    
    
class MemoOOG(models.Model):
    _name = "memo.oog"
    
    name = fields.Char("OOG")
    
class MemoCargoType(models.Model):
    _name = "memo.cargotype"
    
    name = fields.Char("Name")
     
class MemoTravelType(models.Model):
    _name = "memo.travel.type"
    
    name = fields.Char("Name")
    
    
class MemoLicenseType(models.Model):
    _name = "memo.license.type"
    
    name = fields.Char("Name")
    
    
class MemoModel(models.Model):
    _inherit = "memo.model"
    
    # CONSIGNMENT CFWD
    consignment_type = fields.Many2one(
        'memo.consignment.type', 
        'Consignment type'
        )
    transport_mode = fields.Many2one(
        'memo.transport.mode', 
        'Transport Mode'
        )
    # no of items
    hazmat = fields.Many2one(
        'memo.hazmat', 
        'Hazmat'
        )
    # Pickup location
    # dropoff location
    
    oog = fields.Many2one(
        'memo.oog', 
        'OOG'
        )
    
    ### CONSIGNMENT AGENCY
    
    cargo_type_id = fields.Many2one(
        'memo.cargotype', 
        'Cargo type'
        )
    vessel_name = fields.Char(
        string="Vessel Name"
    )
    
    port_of_origin = fields.Char(
        string="Port of Origin"
    )
    
    discharge_port = fields.Char(
        string="Discharge Port"
    )
    
    discharge_terminal = fields.Char(
        string="Discharge Terminal"
    )
    
    vessel_etd = fields.Date(
        string="Vessel ETD"
    )
    vessel_eta = fields.Date(
        string="Vessel ETA"
    )
    
    ## consginment travel
    
    no_of_passenger = fields.Char(
        string="No of Passenger(s)"
    )
    # pick up location 
    # drop off location
    hotel = fields.Char(
        string="Hotel"
    )
    # arrival_date
    
    
    # consignment transport
    #truck_company
    package_type = fields.Char(
        string="Package type"
    )
    gross_weight = fields.Char(
        string="Gross Weight"
    )
    # drivers details
    # truck details
    # TRANSPORT
    # truck_company_name = fields.Many2one('res.partner', string='Truck company Name')
    # truck_reg = fields.Char(string='Truck registration No.')
    # truck_type = fields.Char(string='Truck Type')
    # truck_driver = fields.Many2one('res.partner', string='Driver details')
    # truck_driver_phone = fields.Char(string='Driver Phone')
    # waybill_ids = fields.One2many(
    #     'memo.transport.waybill', 
    #     'memo_id',
    #     string='Waybill details'
    #     ) 

    
    # consignment license
    consignment_type = fields.Many2one(
        'memo.license.type', 
        'license type'
        )
     