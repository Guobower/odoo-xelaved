from openerp import http, SUPERUSER_ID
from openerp.http import request
import urlparse
import werkzeug.utils
import logging
_logger = logging.getLogger(__name__)

class MassMailController(http.Controller):
    
    @http.route(['/view_in_browser'], type='http', website=True, auth='public')
    def mailing_simple4(self):
        mailing = request.env['mail.mass_mailing'].sudo().browse(17)
        if mailing.exists():
            if mailing.mailing_model == 'mail.mass_mailing.contact':
                body_html = mailing.body_html
                if "${object.name or ''|safe}" in body_html:
                    body_html = body_html.replace("${object.name or ''|safe}", '')
                res = {
                    'body_html': body_html,
                    'subject': mailing.name,
                    'mailing_id': 17
                }
                return request.website.render('qwarie_customization.page_view_email', res)
            else:
                super(MassMailController, self).mailing(17, email=email, res_id=res_id, **post)
                return request.website.render('qwarie_customization.page_view_email')

    @http.route(['/mail/mailing/<int:mailing_id>/view'], type='http', website=True, auth='public')
    def mailing(self, mailing_id, email=None, res_id=None, **post):
        mailing = request.env['mail.mass_mailing'].sudo().browse(mailing_id)
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        if mailing.exists():
            if mailing.mailing_model == 'mail.mass_mailing.contact':
                body_html = mailing.body_html
                contacts = request.env['mail.mass_mailing.contact'].sudo().search([('email', '=', email)])
                unsubscribe_url = urlparse.urljoin(
                    base_url, 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                        'mailing_id': mailing_id,
                        'params': werkzeug.url_encode({'db': request.cr.dbname, 'res_id': res_id, 'email': email})
                    }
                )
                browser_url = urlparse.urljoin(
                    base_url, 'mail/mailing/%(mailing_id)s/view?%(params)s' % {
                        'mailing_id': mailing_id,
                        'params': werkzeug.url_encode({'db': request.cr.dbname, 'res_id': res_id, 'email': email})
                    }
                )
                
                if '/unsubscribe_from_list' in body_html:
                    body_html = body_html.replace(base_url+'/unsubscribe_from_list', unsubscribe_url)
                if '/view_in_browser' in body_html:
                    body_html = body_html.replace(base_url+'/view_in_browser', browser_url)
                if "${object.name or ''|safe}" in body_html:
                    if contacts and contacts[0].name:
                        body_html = body_html.replace("${object.name or ''|safe}", contacts[0].name)
                    else:
                        body_html = body_html.replace("${object.name or ''|safe}", '')
                res = {
                    'body_html': body_html,
                    'subject': mailing.name,
                    'email': email,
                    'mailing_id': mailing_id
                }
                return request.website.render('qwarie_customization.page_view_email', res)
            else:
                super(MassMailController, self).mailing(mailing_id, email=email, res_id=res_id, **post)
                return request.website.render('qwarie_customization.page_view_email')