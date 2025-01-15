# from odoo import models
# from odoo.http import request


# class IrHttp(models.AbstractModel):

#     _inherit = 'ir.http'

#     @classmethod
#     def _authenticate(cls, auth_method='user'):
#         res = super(IrHttp, cls)._authenticate(auth_method=auth_method)
#         if request and request.env and request.env.user:
#             #expire session if user does not belong to helpdesk user
#             if not request.env.user.has_group('helpdesk_extension.group_helpdesk_dashboard'):
#                 request.env.user._auth_timeout_check()
#         return res
