# -*- coding: utf-8 -*-
{
    'name': "Qwarie Customization",
    'summary': """
        Odoo customization for Qwarie
    """,
    'description': """
        Changes to views, script and style for Qwarie
    """,
    'author': "Cirro Solutions",
    'website': "http://www.cirrosolutions.eu",
    'category': 'Customization',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base', 'base_setup', 'mail', 'web', 'website', 'account', 'project', 'event', 'hr', 'sale', 'survey', 'mass_mailing', 'report'],
    # always loaded
    'data': [
        # security
        'security/access_groups.xml',
        'security/ir.model.access.csv',
        # views
        'views/web.xml',
        'views/website.xml',
        'views/res_partner.xml',
        #'views/project.xml',
        'views/invoice.xml',
        'views/sale.xml',
        'views/survey_views.xml',
        'views/survey_templates.xml',
        'views/event.xml',
        'views/calendar.xml',
        'views/hr.xml',
        'views/menu.xml',
        'views/airport.xml',
        'views/inventory.xml',
        'views/mass_mailing.xml',
        'views/snippets_themes.xml',
        'views/certificate_email_temp.xml',
        'views/website_video.xml',
        # reports
        'views/report_invoice.xml',
        'views/report_sale.xml',
        'views/certificate_report.xml',
        'views/sale_order_report_view.xml',
        'views/report_sale_order.xml',
        # 'views/editor.xml',
    ],
    'qweb': [
        'static/xml/chatter.xml',
        'static/xml/web_base.xml',
        'static/xml/sale_dashboard.xml',
    ],
}
