import logging
import odoo
from odoo.tools.translate import _
from odoo.addons.web.controllers.main import Home, ensure_db
from odoo import http
from odoo.http import request, SessionExpiredException

_logger = logging.getLogger(__name__)


class HomeExtension(Home):
    @http.route('/web/login', type='http', auth="none", sitemap=False)
    def web_login(self, redirect=None, **kw):
        ensure_db()
        request.params['login_success'] = False
        order = request.website.sale_get_order()
        if order:
            for line in order.website_order_line:
                line.unlink()

        if request.httprequest.method == 'GET' and request.session.uid:
            return http.redirect_with_hash('/web/session/logout')

        if not request.uid:
            # request.uid = odoo.SUPERUSER_ID
            request.update_env(user=odoo.SUPERUSER_ID, context=None, su=None)

        values = request.params.copy()
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            selected_branch = request.params['branch_id']

            if not selected_branch:
                values['error'] = _("Please select a login branch")

            try:
                uid = request.session.authenticate(request.session.db, request.params['login'],
                                                   request.params['password'])
                request.params['login_success'] = True
                request.env['ir.rule'].clear_caches()
                branch = request.env['multi.branch'].search([('name', '=', selected_branch)])
                user = request.env['res.users'].browse([uid])
                user.sudo().write({'branch_id': branch.id})  # branch_id = branch.id
                return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))
            except odoo.exceptions.AccessDenied as e:
                # request.uid = old_uid
                request.update_env(user=old_uid, context=None, su=None)

                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employee can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        # otherwise no real way to test debug mode in template as ?debug =>
        # values['debug'] = '' but that's also the fallback value when
        # missing variables in qweb
        if 'debug' in values:
            values['debug'] = True

        response = request.render('web.login', values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response
