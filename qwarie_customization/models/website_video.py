# -*- coding: utf-8 -*-
import datetime
import io
import json
from PIL import Image
import re
from urllib import urlencode
import urllib2
from urlparse import urlparse
import logging
from lxml import html
from urllib2 import urlopen
from urlparse import urljoin
from urlparse import urlparse
from werkzeug import url_encode, unescape
from openerp import api, fields, models, SUPERUSER_ID, _
from openerp.tools import image
from openerp.exceptions import Warning
from openerp.http import request
from openerp.addons.website.models.website import slug
from openerp.addons.website.models.ir_http import ir_http
from openerp.exceptions import AccessError, UserError
_logger = logging.getLogger(__name__)

URL_REGEX = r'(\bhref=[\'"](?!mailto:)([^\'"]+)[\'"])'

def VALIDATE_URL(url):
    if urlparse(url).scheme not in ('http', 'https', 'ftp', 'ftps'):
        return 'http://' + url

    return url

#Attachment Check inherit for Users Access Rules
class ir_attachment_check(models.Model):
    _inherit = 'ir.attachment'

    def check(self, cr, uid, ids, mode, context=None, values=None):
        res_ids = {}
        if ids:
            if isinstance(ids, (int, long)):
                ids = [ids]
            cr.execute('SELECT DISTINCT res_model, res_id, create_uid FROM ir_attachment WHERE id = ANY (%s)', (ids,))
            for rmod, rid, create_uid in cr.fetchall():
                if not (rmod and rid):
                    continue
                res_ids.setdefault(rmod,set()).add(rid)
        if values:
            if values.get('res_model') and values.get('res_id'):
                res_ids.setdefault(values['res_model'],set()).add(values['res_id'])
        ima = self.pool.get('ir.model.access')
        for model, mids in res_ids.items():
            # ignore attachments that are not attached to a resource anymore when checking access rights
            # (resource was deleted but attachment was not)
            if not self.pool.get(model):
                continue
            existing_ids = self.pool[model].exists(cr, uid, mids)
            ima.check(cr, uid, model, mode)
            self.pool[model].check_access_rule(cr, uid, existing_ids, mode, context=context)

class Slide(models.Model):
    _inherit = 'slide.slide'
    _description = 'Slides'
    #add attachment field
    attachment_ids = fields.Many2many(
        'ir.attachment', 'video_ir_attachments_rel', 
        'video_id', 'attachment_id', string='Attachments')
    slide_type = fields.Selection([
        ('infographic', 'Infographic'),
        ('presentation', 'Presentation'),
        ('document', 'Document'),
        ('video', 'Youtube Video'),
        ('upload_video', 'Uploaded Video')],
        string='Type', required=True,
        help="Document type will be set automatically depending on file type, height and width.")
    url = fields.Char('Document URL', help="Youtube or Google Document URL")
    image = fields.Binary('Image', attachment=True, readonly=False)
    track_user_ids = fields.One2many('link.tracker.user', 'slide_id', string='Users')


    @api.model
    def create(self, values):
        if not values.get('index_content'):
            values['index_content'] = values.get('description')
        if values.get('slide_type') == 'infographic' and not values.get('image'):
            values['image'] = values['datas']
        if values.get('website_published') and not values.get('date_published'):
            values['date_published'] = datetime.datetime.now()
        if values.get('url') and not values.get('document_id'):
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.iteritems():
                values.setdefault(key, value)
        if values.get('attachment_ids'):
            expr = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            arg = expr.match(values.get('url'))
            document_id = arg or False
            values['slide_type'] = 'upload_video'
            values['document_id'] = document_id
        # Do not publish slide if user has not publisher rights
        if not self.user_has_groups('base.group_website_publisher'):
            values['website_published'] = False
        slide = super(Slide, self).create(values)
        slide.channel_id.message_subscribe_users()
        slide._post_publication()
        return slide

    @api.multi
    def write(self, values):
        if values.get('url') and values['url'] != self.url:
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.iteritems():
                values.setdefault(key, value)
        if values.get('channel_id'):
            custom_channels = self.env['slide.channel'].search([('custom_slide_id', '=', self.id), ('id', '!=', values.get('channel_id'))])
            custom_channels.write({'custom_slide_id': False})
        res = super(Slide, self).write(values)
        if values.get('website_published'):
            self.date_published = datetime.datetime.now()
            self._post_publication()
        if values.get('slide_type') == 'upload_video':
            values['slide_type'] = 'upload_video'
        return res

    @api.one
    @api.onchange('attachment_ids')
    def _get_url(self):
        #Create Uploaded Video URL
        if self.attachment_ids:
            self.url = "http://192.168.0.112:8069/web/content/%s" % self.attachment_ids.id
        return self.url

    def _find_document_data_from_url(self, url):
        expr = re.compile(r'^.*((youtu.be/)|(v/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#\&\?]*).*')
        arg = expr.match(url)
        document_id = arg and arg.group(7) or False
        if document_id:
            return ('youtube', document_id)

        expr = re.compile(r'(^https:\/\/docs.google.com|^https:\/\/drive.google.com).*\/d\/([^\/]*)')
        arg = expr.match(url)
        document_id = arg and arg.group(2) or False
        if document_id:
            return ('google', document_id)

        expr = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        arg = expr.match(url)
        document_id = arg or False
        if document_id:
            if 'video' in str(self.attachment_ids.mimetype):
                return ('upload_video', document_id)
            elif 'image' in str(self.attachment_ids.mimetype):
                return ('image', document_id)

        return (None, False)

    def _parse_upload_video_document(self, document_id, only_preview_fields):
        values = {
            'slide_type': 'upload_video', 
            'document_id': document_id
            }
        
        values.update({
            'name': self.attachment_ids.name,
        })
        return {'values': values}

    def _parse_image_document(self, document_id, only_preview_fields):
        values = {'slide_type': 'infographic', 'document_id': document_id}
        return {'values': values}

    @api.depends('slide_views', 'embed_views')
    def _compute_total(self):
        view_id = self.env['link.tracker.user'].search([('slide_id', '=', self.id)])
        for record in view_id:
            self.total_views += 1

class Channel(models.Model):
    """ A channel is a container of slides. It has group-based access configuration
    allowing to configure slide upload and access. Slides can be promoted in
    channels. """
    _inherit = 'slide.channel'

    @api.depends('slide_ids.slide_type', 'slide_ids.website_published')
    def _count_presentations(self):
        result = dict.fromkeys(self.ids, dict())
        res = self.env['slide.slide'].read_group(
            [('website_published', '=', True), ('channel_id', 'in', self.ids)],
            ['channel_id', 'slide_type'], ['channel_id', 'slide_type'],
            lazy=False)
        for res_group in res:
            result[res_group['channel_id'][0]][res_group['slide_type']] = result[res_group['channel_id'][0]].get(res_group['slide_type'], 0) + res_group['__count']
        for record in self:
            record.nbr_presentations = result[record.id].get('presentation', 0)
            record.nbr_documents = result[record.id].get('document', 0)
            record.nbr_videos = result[record.id].get('video', 0) + result[record.id].get('upload_video', 0)
            record.nbr_infographics = result[record.id].get('infographic', 0)
            record.total = record.nbr_presentations + record.nbr_documents + record.nbr_videos + record.nbr_infographics

class link_tracker(models.Model):
    _inherit = 'link.tracker'

    track_user_ids = fields.One2many('link.tracker.user', 'link_id', string='Users')

    @api.one
    def _compute_code(self):
        record = self.env['link.tracker.code'].search([('link_id', '=', self.id)], limit=1, order='id DESC')
        self.code = record.code

    @api.multi
    def action_visit_page(self):
        return {
            'name': _("Visit Webpage"),
            'type': 'ir.actions.act_url',
            'url': self.url,
            'target': 'new',
        }
    
    @api.model
    def create(self, vals):
        create_vals = vals.copy()
        if 'url' not in create_vals:
            raise ValueError('URL field required')
        else:
            create_vals['url'] = VALIDATE_URL(vals['url'])
        search_domain = []
        for fname, value in create_vals.iteritems():
            search_domain.append((fname, '=', value))
        result = self.search(search_domain, limit=1)
        if result:
            return result
        if not create_vals.get('title'):
            create_vals['title'] = self._get_title_from_url(create_vals['url'])
        # Prevent the UTMs to be set by the values of UTM cookies
        for (key, fname, cook) in self.env['utm.mixin'].tracking_fields():
            if fname not in create_vals:
                create_vals[fname] = False
        link = super(link_tracker, self).create(create_vals)
        code = self.env['link.tracker.code'].get_random_code_string()
        self.env['link.tracker.code'].create({'code': code, 'link_id': link.id})
        return link

class link_tracker_user(models.Model):
    _name = 'link.tracker.user'

    link_id = fields.Many2one('link.tracker', 'Link', required=True, ondelete='cascade')
    click_date = fields.Datetime(string='Click Date')
    user_id = fields.Many2one('res.users', 'Users')
    ip = fields.Char(string='Internet Protocol')
    slide_id = fields.Many2one('slide.slide', 'Slide', required=True, ondelete='cascade')

    @api.model
    def add_user(self, code, ip, user_code, stat_id=False):
        self = self.sudo()
        code_rec = self.env['link.tracker.code'].search([('code', '=', code)])
        if not code_rec:
            return None
        again = self.search_count([('link_id', '=', code_rec.link_id.id), ('ip', '=', ip)])
        user_record = self.env['res.users'].search([('id', '=', user_code)], limit=1)
        slide_id = self.env['slide.slide'].search([('name', '=', code_rec.link_id.title)])
        vals = {
            'link_id': code_rec.link_id.id,
            'click_date': datetime.datetime.now(),
            'ip': ip,
            'user_id': user_record.id,
            'slide_id': slide_id.id
        }
        self.create(vals)
