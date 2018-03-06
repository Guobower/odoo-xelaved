# -*- coding: utf-8 -*-
import datetime
import random
import re
import string

from lxml import html
from urllib2 import urlopen
from urlparse import urljoin
from urlparse import urlparse
from werkzeug import url_encode, unescape

from openerp import models, fields, api, _
from openerp.tools import ustr

URL_REGEX = r'(\bhref=[\'"](?!mailto:)([^\'"]+)[\'"])'

class link_tracker(models.Model):
    _inherit = 'link.tracker'

    @api.one
    @api.depends('url')
    def _compute_redirected_url(self):
        parsed = urlparse(self.url)

        utms = {}
        for key, field, cook in self.env['utm.mixin'].tracking_fields():
            attr = getattr(self, field).name
            if attr:
                utms[key] = attr

        self.redirected_url = '%s://%s%s' % (parsed.scheme, parsed.netloc, parsed.path)
        if url_encode(utms):
            self.redirected_url = '%s?%s' % (self.redirected_url, url_encode(utms))
        if parsed.query:
            self.redirected_url = '%s&%s' % (self.redirected_url, parsed.query)
        if parsed.fragment:
            self.redirected_url = '%s#%s' % (self.redirected_url, parsed.fragment)