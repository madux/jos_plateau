from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError
from odoo import fields

from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class TestLogin(TransactionCase):

    def setUp(self, *args, **kwargs):
        super_class = super().setUp(*args, **kwargs)