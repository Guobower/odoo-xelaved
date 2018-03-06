# -*- coding: utf-8 -*-
import base64
import logging
import werkzeug

from openerp.addons.web import http
from openerp.exceptions import AccessError, UserError
from openerp.http import request
from openerp.addons.website_slides.controllers.main import website_slides
from openerp.addons.link_tracker.controller.main import link_tracker
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class website_slides(website_slides):

    #Send Upload video URL and Slide type to website render
    @http.route(
        '''/slides/slide/<model("slide.slide", "[('channel_id.can_see', '=', True)]"):slide>''',
        type='http', auth="public", website=True)
    def slide_view(self, slide, **kwargs):
        values = self._get_slide_detail(slide)
        url = self._get_slide_detail(slide)['slide'].url
        slide_type = self._get_slide_detail(slide)['slide'].slide_type
        values.update({
            'url': url,
            'slide_type': slide_type
        })
        if not values.get('private'):
            self._set_viewed_slide(slide, 'slide')
        return request.website.render('website_slides.slide_detail_view', values)

    #Add "Uploaded Videos" to "Videos" Tab
    @http.route([
        '''/slides/<model("slide.channel", "[('can_see', '=', True)]"):channel>''',
        '''/slides/<model("slide.channel", "[('can_see', '=', True)]"):channel>/page/<int:page>''',

        '''/slides/<model("slide.channel", "[('can_see', '=', True)]"):channel>/<string:slide_type>''',
        '''/slides/<model("slide.channel", "[('can_see', '=', True)]"):channel>/<string:slide_type>/page/<int:page>''',

        '''/slides/<model("slide.channel", "[('can_see', '=', True)]"):channel>/tag/<model("slide.tag"):tag>''',
        '''/slides/<model("slide.channel", "[('can_see', '=', True)]"):channel>/tag/<model("slide.tag"):tag>/page/<int:page>''',

        '''/slides/<model("slide.channel", "[('can_see', '=', True)]"):channel>/category/<model("slide.category"):category>''',
        '''/slides/<model("slide.channel", "[('can_see', '=', True)]"):channel>/category/<model("slide.category"):category>/page/<int:page>''',

        '''/slides/<model("slide.channel", "[('can_see', '=', True)]"):channel>/category/<model("slide.category"):category>/<string:slide_type>''',
        '''/slides/<model("slide.channel", "[('can_see', '=', True)]"):channel>/category/<model("slide.category"):category>/<string:slide_type>/page/<int:page>'''],
        type='http', auth="public", website=True)
    def channel(self, channel, category=None, tag=None, page=1, slide_type=None, sorting='creation', search=None, **kw):
        user = request.env.user
        Slide = request.env['slide.slide']
        domain = [('channel_id', '=', channel.id)]
        pager_url = "/slides/%s" % (channel.id)
        pager_args = {}

        if search:
            domain += [
                '|', '|',
                ('name', 'ilike', search),
                ('description', 'ilike', search),
                ('index_content', 'ilike', search)]
            pager_args['search'] = search
        else:
            if category:
                domain += [('category_id', '=', category.id)]
                pager_url += "/category/%s" % category.id
            elif tag:
                domain += [('tag_ids.id', '=', tag.id)]
                pager_url += "/tag/%s" % tag.id
            if slide_type:
                if slide_type == 'video':
                    domain += [('slide_type', 'in', (u'video', u'upload_video'))]
                else:
                    domain += [('slide_type', '=', slide_type)]
                    pager_url += "/%s" % slide_type

        if not sorting or sorting not in self._order_by_criterion:
            sorting = 'date'
        order = self._order_by_criterion[sorting]
        pager_args['sorting'] = sorting

        pager_count = Slide.search_count(domain)
        pager = request.website.pager(url=pager_url, total=pager_count, page=page,
                                      step=self._slides_per_page, scope=self._slides_per_page,
                                      url_args=pager_args)

        slides = Slide.search(domain, limit=self._slides_per_page, offset=pager['offset'], order=order)
        values = {
            'channel': channel,
            'category': category,
            'slides': slides,
            'tag': tag,
            'slide_type': slide_type,
            'sorting': sorting,
            'user': user,
            'pager': pager,
            'is_public_user': user == request.website.user_id,
            'display_channel_settings': not request.httprequest.cookies.get('slides_channel_%s' % (channel.id), False) and channel.can_see_full,
        }
        if search:
            values['search'] = search
            return request.website.render('website_slides.slides_search', values)

        # Display uncategorized slides
        if not slide_type and not category:
            category_datas = []
            for category in Slide.read_group(domain, ['category_id'], ['category_id']):
                category_id, name = category.get('category_id') or (False, _('Uncategorized'))
                category_datas.append({
                    'id': category_id,
                    'name': name,
                    'total': category['category_id_count'],
                    'slides': Slide.search(category['__domain'], limit=4, offset=0, order=order)
                })
            values.update({
                'category_datas': category_datas,
            })
        return request.website.render('website_slides.home', values)

class link_tracker(link_tracker):
    @http.route(
        '''/r/<string:code>''',
        type='http', auth='public', website=True)
    def full_url_redirect(self, code, **post):
        # user_code = request.session.uid
        # request.env['link.tracker.user'].add_user(code, request.httprequest.remote_addr, user_code, stat_id=False)
        redirect_url = request.env['link.tracker'].get_url_from_code(code)
        return werkzeug.utils.redirect(redirect_url or '', 301)

    @http.route(
        '''/slides/slide/<model("slide.slide", "[('channel_id.can_see', '=', True)]"):slide>''',
        type='http', auth="public", website=True)
    def long_url_redirect(self, slide, **kwargs):
        short_url = slide._website_url(slide.name, slide)[slide.id]
        code = str(short_url)[-3:]
        user_code = request.session.uid
        request.env['link.tracker.user'].add_user(code, request.httprequest.remote_addr, user_code, stat_id=False)
        redirect_url = str(request.env['link.tracker'].get_url_from_code(code)) + "#forward"

        values = website_slides()._get_slide_detail(slide)
        url = website_slides()._get_slide_detail(slide)['slide'].url
        slide_type = website_slides()._get_slide_detail(slide)['slide'].slide_type
        values.update({
            'url': url,
            'slide_type': slide_type
        })
        if not values.get('private'):
            website_slides()._set_viewed_slide(slide, 'slide')
        return request.website.render('website_slides.slide_detail_view', values)
