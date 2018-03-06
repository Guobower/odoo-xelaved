# -*- coding: utf-8 -*-
from openerp import fields, models
from HTMLParser import HTMLParser
import re
import urlparse
import werkzeug.urls

from openerp import tools
from openerp import SUPERUSER_ID

URL_REGEX = r'(\bhref=[\'"]([^\'"]+)[\'"])'

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

class ir_mail_server(models.Model):
    _inherit = "ir.mail_server"

    def _get_default_bounce_address(self, cr, uid, context=None):
        address = super(ir_mail_server, self)._get_default_bounce_address(cr, uid, context)
        if 'postmaster-odoo' in address:
            address = 'postmaster@qwarie.com'
        return address

class MassMailingContact(models.Model):
    _inherit = 'mail.mass_mailing.contact'

    name = fields.Char('First Name')
    last_name = fields.Char('Last Name')

    def add_to_mailing_list(self, cr, uid, ids, context=None):
        contact = self.browse(cr, uid, ids, context=context) # mass mailing contact created
        email = contact.message_ids[0] # the email read that trigger the contact's creation
        subjects_list = [
            # {'text': 'Investigation Instruction', 'list_id': 1, },
            # {'text': 'Bulk Purchasing', 'list_id': 1, }, 
            # {'text': 'Procedural Advice', 'list_id': 1, },
            # {'text': 'OSINT Training Info', 'list_id': 2, },
            # {'text': 'Public Speaking Request', 'list_id': 1, },
            # {'text': 'General Enquiry', 'list_id': 2, },
            {'text': 'Newsletter Subscription', 'list_id': 2, }]
        match = [subject for subject in subjects_list if subject['text'] in email.subject] or False
        if match:
            mail_lines = strip_tags(email.body).splitlines()
            vals = {}
            for line in mail_lines:
                if len(line.split(':')) == 2:
                    key, value = line.split(':')
                    if key and value:
                        if key == 'Your name':
                            nameParts = value.strip().split(' ')
                            vals['name'] = nameParts[0]
                            vals['last_name'] = nameParts[len(nameParts) - 1] if len(nameParts) > 1  else False
                        if key == 'Your e-mail address':
                            vals['email'] = value.strip()
            if vals:
                vals['list_id'] = match[0]['list_id']
                duplicates = self.search(cr, uid, [
                        ('name', '=', vals['name']), ('last_name', '=', vals['last_name']), ('email', '=', vals['email']), ('list_id', '=', match[0]['list_id'])
                    ], context=context)
                if duplicates:
                    contact.unlink() # contact is already subscribed
                else:
                    contact.write(vals) # update email and name of the mass mailing contact
        else:
            # email is not fit for mailing list subscription
            contact.unlink()

class MassMailing(models.Model):
    _inherit = ['mail.mass_mailing']

    def convert_links(self, cr, uid, ids, context=None):
        res = {}
        for mass_mailing in self.browse(cr, uid, ids, context=context):
            utm_mixin = mass_mailing.mass_mailing_campaign_id if mass_mailing.mass_mailing_campaign_id else mass_mailing
            html = mass_mailing.body_html if mass_mailing.body_html else ''

            vals = {'mass_mailing_id': mass_mailing.id}

            if mass_mailing.mass_mailing_campaign_id:
                vals['mass_mailing_campaign_id'] = mass_mailing.mass_mailing_campaign_id.id
            if utm_mixin.campaign_id:
                vals['campaign_id'] = utm_mixin.campaign_id.id
            if utm_mixin.source_id:
                vals['source_id'] = utm_mixin.source_id.id
            if utm_mixin.medium_id:
                vals['medium_id'] = utm_mixin.medium_id.id

            res[mass_mailing.id] = self.pool['link.tracker'].convert_links(cr, uid, html, vals, blacklist=['/unsubscribe_from_list', '/view_in_browser'], context=context)

        return res

class MailMail(models.Model):
    _inherit = ['mail.mail']

    def _get_browser_url(self, cr, uid, mail, email_to, context=None):
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        url = urlparse.urljoin(
            base_url, 'mail/mailing/%(mailing_id)s/view?%(params)s' % {
                'mailing_id': mail.mailing_id.id,
                'params': werkzeug.url_encode({'db': cr.dbname, 'res_id': mail.res_id, 'email': email_to})
            }
        )
        return url

    def send_get_mail_body(self, cr, uid, ids, partner=None, context=None):
        """ Override to add the tracking URL to the body and to add
        Statistic_id in shorted urls """
        # TDE: temporary addition (mail was parameter) due to semi-new-API
        mail = self.browse(cr, uid, ids[0], context=context)
        body = mail.body_html or ''

        links_blacklist = ['/unsubscribe_from_list', '/view_in_browser']

        if mail.mailing_id and body and mail.statistics_ids:
            for match in re.findall(URL_REGEX, mail.body_html):

                href = match[0]
                url = match[1]

                if not [s for s in links_blacklist if s in href]:
                    new_href = href.replace(url, url + '/m/' + str(mail.statistics_ids[0].id))
                    body = body.replace(href, new_href)

        # prepend <base> tag for images using absolute urls
        domain = self.pool.get("ir.config_parameter").get_param(cr, uid, "web.base.url", context=context)
        base = "<base href='%s'>" % domain
        body = tools.append_content_to_html(base, body, plaintext=False, container_tag='div')
        # resolve relative image url to absolute for outlook.com
        def _sub_relative2absolute(match):
            return match.group(1) + urlparse.urljoin(domain, match.group(2))
        body = re.sub('(<img(?=\s)[^>]*\ssrc=")(/[^/][^"]+)', _sub_relative2absolute, body)
        body = re.sub(r'(<[^>]+\bstyle="[^"]+\burl\(\'?)(/[^/\'][^\'")]+)', _sub_relative2absolute, body)

        # generate tracking URL
        if mail.statistics_ids:
            tracking_url = self._get_tracking_url(cr, uid, mail, partner, context=context)
            if tracking_url:
                body = tools.append_content_to_html(body, tracking_url, plaintext=False, container_tag='div')
        return body

    def send_get_email_dict(self, cr, uid, ids, partner=None, context=None):
        # TDE: temporary addition (mail was parameter) due to semi-new-API
        res = super(MailMail, self).send_get_email_dict(cr, uid, ids, partner, context=context)
        mail = self.browse(cr, uid, ids[0], context=context)
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        if mail.mailing_id and res.get('body') and res.get('email_to'):
            emails = tools.email_split(res.get('email_to')[0])
            email_to = emails and emails[0] or False
            browser_url = self._get_browser_url(cr, uid, mail, email_to, context=context)
            link_to_replace =  base_url+'/view_in_browser'
            if link_to_replace in res['body']:
                res['body'] = res['body'].replace(link_to_replace, browser_url if browser_url else '#')
        return res
