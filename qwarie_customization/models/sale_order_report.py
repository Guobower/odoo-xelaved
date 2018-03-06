# -*- coding: utf-8 -*-
from openerp import fields, models, tools, api, _
from openerp.exceptions import UserError
from openerp import SUPERUSER_ID

class sale_order_report(models.Model):
    _name = "sale.order.report"
    _description = "Commission Statistics"
    _order = 'date_order2 desc'
    _auto = False
    # _inherit = ["utm.mixin"]
    #Sale order report (Pivot and graph view)
    partner2_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    company2_id = fields.Many2one('res.company', string='Company', readonly=True)
    user2_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    sale_commission_store2 = fields.Float(string='Sale Commission', readonly=True)
    date_order2 = fields.Datetime(string='Order Date', readonly=True)
    team2_id = fields.Many2one('crm.team', string='Team', readonly=True)
    country2_id = fields.Many2one('res.country', 'Country', readonly=True)
    customer_type2 = fields.Char(string='Customer Type', readonly=True)
    amount_total2 = fields.Float(string='Total Amount', readonly=True)
    amount_untaxed2 = fields.Float(string='Untaxed Total Amount', readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'sale_order_report')
        cr.execute(""" CREATE VIEW sale_order_report AS (
            SELECT
                sale.id AS id,
                sale.user_id AS user2_id,
                sale.partner_id AS partner2_id,
                sale.company_id AS company2_id,
                sale.sale_commission_store AS sale_commission_store2,
                sale.date_order AS date_order2,
                sale.team_id AS team2_id,
                sale.customer_type_store AS customer_type2,
                sale.amount_total AS amount_total2,
                sale.amount_untaxed AS amount_untaxed2,
                r.country_id AS country2_id
            FROM
                sale_order sale
                LEFT JOIN res_partner r ON (r.id=sale.partner_id)
                LEFT JOIN res_users u ON (u.id=sale.user_id)

            GROUP BY
                partner2_id,
                company2_id,
                user2_id,
                sale_commission_store2,
                date_order2,
                team2_id,
                country2_id,
                customer_type2,
                amount_total2,
                amount_untaxed2,
                sale.id
        )
        """)