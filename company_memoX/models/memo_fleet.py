from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime


class MemoFleetMaintenance(models.Model):
    _name = 'memo.fleet.maintenance'
    _description = "FLEET MAINTANACE MODEL"


    vehicle_id = fields.Many2one(
        'product.product',
        string="Vehicle Assigned",
        required=False,
        domain=[('is_vehicle_product', '=', True)]
        )
    fleet_id = fields.Many2one(
        'memo.fleet',
        string="Fleet id",
        required=False,
        )
    requested_by = fields.Many2one(
        'hr.employee',
        string="Request by",
        )
    serviced_by = fields.Many2one(
        'res.partner',
        string="Serviced by",
        required=False,
        )
    start_time = fields.Datetime(
        string="Start time")
    end_time = fields.Datetime(
        string="End time")
    state_maintenace_required = fields.Text(
        string="Maintenace description",
        )
    service_resolution = fields.Text(
        string="Service resolution",
        )
    next_service_date = fields.Datetime(
        string="Next service date",
        )
    
    status = fields.Selection(
        [
            ("Active", "Active"),
            ("Faulty", "Faulty"),
            ("Salvaged", "Salvaged"),
            ("Long_used", "Long used"),
            ("Deprecated", "Deprecated"),
            ("Damaged", "Damaged"),
            
        ], 
        readonly=False,
        string="Decide action?",
        default="Active",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"), 
            ("confirm", "Confirm"),

        ], 
        readonly=False,
        string="State",
        default="none",
        store=True,
    )

    def button_confirm_service_action(self):
        if self.status:
            self.vehicle_id.vehicle_status = self.status
            self.vehicle_id.is_available = False
            self.vehicle_id.last_service_by = self.serviced_by.name
            self.vehicle_id.not_to_be_moved = True if self.status in ['Damaged', 'Damaged', 'Faulty'] else False
            self.state = 'confirm'
    def button_reverse_confirmed_service_action(self):
        if self.status:
            self.vehicle_id.vehicle_status = 'Active'
            self.vehicle_id.is_available = True
            self.vehicle_id.last_service_by = ""
            self.vehicle_id.not_to_be_moved = False
            self.state = 'draft'



class MemoFleet(models.Model):
    _name = 'memo.fleet'
    _description = '''This model holds the fleet transaction on a timely basis:'''
    ''' 
    When employee books for a fleet, the fleet is then become unavailable.
    When the driver returns the vehicle - the fleet becomes available
    The also shows the driver responsible and the distances covered on a daily
    basis. (a table should hold the current trip where the driver starts and ends the trip: 
    this table contains the following fileds;
    start time - end time, 
    start location - destination location
    distance covered (mileage, trips, km/h), 
    vfs - volume of fuel currently assigned
    vefu - volume of extra fuel used
    Total number of fuel in litres used, (computated as = vfs - vefu) 

    map widget to show real time: not necessary)
    Computation of this distances determines the estimated mileage covered
    '''
    _order = 'code'

    code = fields.Char(
        'Ref#')
    
    vehicle_assigned = fields.Many2one(
        'product.product',
        string="Vehicle Assigned",
        required=False,
        domain=[('is_vehicle_product', '=', True)]
        )
    memo_id = fields.Many2one(
        'memo.model',
        string="Memo ID",
        )
    
    maintenance_ids = fields.One2many(
        'memo.fleet.maintenance',
        'fleet_id',
        string="Memo ID",
        )
    
    driver_assigned = fields.Many2one(
        'hr.employee',
        string="Driver Assigned",
        )
    requested_by = fields.Many2one(
        'hr.employee',
        string="Requested by",
        )
    source_location_id = fields.Char(
        string="Start location",
        required=False
        )
    source_destination_id = fields.Char(
        string="Destination",
        required=True
        )
    distance_covered = fields.Char(
        string="Distance Covered",
        )
    distance_measured = fields.Selection([
        ('mile', 'Mile'),
        ('trip', 'Trips'),
        ('km', 'KM/PH'),
        ],
        string="Distance Measure", default="mile")
    
    start_time = fields.Datetime(
        string="Start time")
    
    end_time = fields.Datetime(
        string="End time")

    number_of_days_covered = fields.Char(
        string="Number of hours/Days/Weeks", 
        compute="compute_number_of_days_covered"
    )
    
    volume_of_current_fuel = fields.Char(
        string="Current fuel volume",
        required=False
        )
    volume_of_extra_fuel_used = fields.Char(
        string="Extra fuel volume Used",
        )
    
    total_fuel_used = fields.Char(
        string="Total fuel volume Used",
        compute="compute_total_fuel_used"
        )
    
    incident_report = fields.Text(
        string="Incident encountered",
        )
    
    require_maintenance = fields.Boolean(
        string="Required Maintenace",
        )
    
    state_maintenace_required = fields.Text(
        string="Maintenace description",
        )
    active = fields.Boolean(
        string="Active",
        )
    trip_started = fields.Boolean(
        string="Trip Started",
        )
    
    def action_generate_maintenance_line(self):
        maintenance = self.env['memo.fleet.maintenance']
        vals = {
            'vehicle_assigned': self.vehicle_id.id,
            'requested_by': self.requested_by.id,
            'fleet_id': self.id,
            'start_time': self.start_time,
            'end_time': False,
        }
        maintenance_line = self.maintenance_ids[0] if self.maintenance_ids else False
        if maintenance_line:
            maintenance_line.update(vals)
        else:
            maintenance.create({
                'vehicle_assigned': self.vehicle_id.id,
                'requested_by': self.requested_by.id,
                'fleet_id': self.id,
                'start_time': self.start_time,
                'end_time': False,
            })

    def action_end_fleet(self):
        Fleet = self.env['memo.fleet'].search([('code', '=', self.code)], limit=1)
        if Fleet:
            Fleet.end_time = fields.Datetime.now()

    def action_start_fleet(self):
        if not self.driver_assigned.user_id.id == self.env.uid:
            pass # raise ValidationError("You are not responsible to start thois trip. Only the assigned driver can proceed with this action")
        self.fleet_component(
            code=self.code,
            volume_of_current_fuel=self.volume_of_current_fuel,
            vehicle_assigned=self.vehicle_assigned,
            driver_assigned=self.driver_assigned,
            source_location_id=self.source_location_id,
            source_destination_id=self.source_destination_id,
            website=False,
            )
    
    def fleet_component(self, **kwargs):
        code, volume_of_current_fuel = kwargs.get('code'), kwargs.get('volume_of_current_fuel')
        vehicle_assigned, driver_assigned = kwargs.get('vehicle_assigned'), kwargs.get('driver_assigned')
        source_location_id, source_destination_id = kwargs.get('source_location_id'), \
            kwargs.get('source_destination_id')
        if not any([
            code, volume_of_current_fuel, 
            vehicle_assigned, driver_assigned, 
            source_location_id, source_destination_id
            ]):
            ValidationErrordata =  {
                    'data': """
                        please provide the following parameteres: Vehicle assigned, 
                        code ,volume of current fuels location or destination must be provided
                        """,
                    }
            if kwargs.get('website'):
                return ValidationErrordata
            else:
                raise ValidationError(f"Error !! {ValidationErrordata.get('data')}")
            
        else:
            Fleet = self.env['memo.fleet'].search([('code', '=', code)], limit=1)
            if Fleet:
                Fleet.start_time = fields.Datetime.now()
                Fleet.trip_started = True
            else:
                if kwargs.get('website'):
                    return {
                        'No fleet record found with the code provided'
                    }
                else:
                    raise ValidationError(
                        "Error !! No fleet record found with the code provided"
                        )
    
    @api.depends('start_time', 'end_time')
    def compute_number_of_days_covered(self):
        if self.start_time and self.end_time:
            self.number_of_days_covered = (self.end_time + self.start_time).days
        else:
            self.number_of_days_covered = False

    @api.depends(
            'volume_of_current_fuel', 
            'volume_of_extra_fuel_used'
            )
    def compute_total_fuel_used(self):
        if self.start_time and self.end_time:
            self.total_fuel_used = (
                self.volume_of_current_fuel + self.volume_of_extra_fuel_used
                )
        else:
            self.total_fuel_used = False
