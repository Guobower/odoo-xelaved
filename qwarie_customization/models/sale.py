# -*- coding: utf-8 -*-
from openerp import fields, models, tools, api, _
from openerp.exceptions import UserError
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID as uid

class crm_lead(models.Model):
    _inherit = 'crm.lead'

    date_action = fields.Datetime('Next Activity Date', select=True)
    date_deadline = fields.Datetime('Expected Closing', help="Estimate of the date on which the opportunity will be won.")
    crm_activity_id2 = fields.Many2one('calendar.event', 'Related Activity', required=False)
    #When a user adds a "Next Activity" in sales, it is automatically added to Calendar
    @api.multi
    def write(self, vals): 
        res = super(crm_lead, self).write(vals)
        date_action = fields.Datetime.from_string(self.date_action)
        if self.date_action:
            if self.crm_activity_id2:
                self.crm_activity_id2.write({
                    'name'          :   self.title_action,
                    'start'         :   self.date_action,
                    'stop'          :   str(date_action + timedelta(minutes=30)),
                    })
                return res
            else:
                result = self.env['calendar.event'].create({
                    'name'          :   self.title_action,
                    'start'         :   self.date_action,
                    'stop'          :   str(date_action + timedelta(minutes=30)),
                    'allday'        :   False,
                    'partner_ids'   :   [(4,[self.partner_id.id])],
                    })
                self.write({ 'crm_activity_id2': result.id})
                return res
        return res

    def log_next_activity_done(self, cr, uid, ids, context=None, next_activity_name=False):
        to_clear_ids = []
        for lead in self.browse(cr, uid, ids, context=context):
            if not lead.next_activity_id:
                continue
            body_html = """<div><b>${object.next_activity_id.name}</b></div>
            %if object.title_action:
            <div>${object.title_action}</div>
            %endif"""
            body_html = self.pool['mail.template'].render_template(cr, uid, body_html, 'crm.lead', lead.id, context=context)
            msg_id = lead.message_post(body_html, subtype_id=lead.next_activity_id.subtype_id.id)
            to_clear_ids.append(lead.id)
            self.write(cr, uid, [lead.id], {'last_activity_id': lead.next_activity_id.id}, context=context)

        if to_clear_ids:
            self.write(cr, uid, ids,  {
                'next_activity_id': False,
                'date_action': False,
                'title_action': False,
                'crm_activity_id2': False,
            }, context=context)
        return True

    @api.multi
    def cancel_next_activity(self):
        res = super(crm_lead, self).cancel_next_activity()
        self.crm_activity_id2.unlink()
        self.write({'crm_activity_id2': False})
        return res

    """Added user sales commission performance in Sales Dashboard, and a Total Performance Row"""
    def retrieve_sales_dashboard(self, cr, uid, context=None):
        DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        res = {
            'meeting': {
                'today': 0,
                'next_7_days': 0,
            },
            'activity': {
                'today': 0,
                'overdue': 0,
                'next_7_days': 0,
            },
            'closing': {
                'today': 0,
                'overdue': 0,
                'next_7_days': 0,
            },
            'done': {
                'this_month': 0,
                'last_month': 0,
                'total': 0,
            },
            'won': {
                'this_month': 0,
                'last_month': 0,
                'total': 0,
            },
            'invoiced': {
                'this_month': 0,
                'last_month': 0,
                'total': 0,
            },
            'sales': {
                'this_month': 0,
                'last_month': 0,
                'total': 0,
            },
            'nb_opportunities': 0,
        }
        opportunities = self.search_read(
            cr, uid,
            [('type', '=', 'opportunity'), ('user_id', '=', uid)],
            ['date_deadline', 'next_activity_id', 'date_action', 'date_closed', 'planned_revenue'], context=context)
        for opp in opportunities:
            # Expected closing
            if opp['date_deadline']:
                date_deadline = datetime.strptime(opp['date_deadline'], DATETIME_FORMAT).date()
                if date_deadline == date.today():
                    res['closing']['today'] += 1
                if date_deadline >= date.today() and date_deadline <= date.today() + timedelta(days=7):
                    res['closing']['next_7_days'] += 1
                if date_deadline < date.today() and not opp['date_closed']:
                    res['closing']['overdue'] += 1
            # Next activities
            if opp['next_activity_id'] and opp['date_action']:
                date_action = datetime.strptime(opp['date_action'], DATETIME_FORMAT).date()
                if date_action == date.today():
                    res['activity']['today'] += 1
                if date_action >= date.today() and date_action <= date.today() + timedelta(days=7):
                    res['activity']['next_7_days'] += 1
                if date_action < date.today() and not opp['date_closed']:
                    res['activity']['overdue'] += 1
            # Won in Opportunities
            if opp['date_closed']:
                date_closed = datetime.strptime(opp['date_closed'], DATETIME_FORMAT).date()
                res['won']['total'] += opp['planned_revenue']
                if date_closed <= date.today() and date_closed >= date.today().replace(day=1):
                    if opp['planned_revenue']:
                        res['won']['this_month'] += opp['planned_revenue']
                elif date_closed < date.today().replace(day=1) and date_closed >= date.today().replace(day=1) - relativedelta(months=+1):
                    if opp['planned_revenue']:
                        res['won']['last_month'] += opp['planned_revenue']
        # crm.activity is a very messy model so we need to do that in order to retrieve the actions done.
        cr.execute("""
            SELECT
                m.id,
                m.subtype_id,
                m.date,
                l.user_id,
                l.type
            FROM
                "mail_message" m
            LEFT JOIN
                "crm_lead" l
            ON
                (m.res_id = l.id)
            INNER JOIN
                "crm_activity" a
            ON
                (m.subtype_id = a.subtype_id)
            WHERE
                (m.model = 'crm.lead') AND (l.user_id = %s) AND (l.type = 'opportunity')
        """, (uid,))
        activites_done = cr.dictfetchall()
        for act in activites_done:
            if act['date']:
                date_act = datetime.strptime(act['date'], DATETIME_FORMAT).date()
                res['done']['total'] += 1
                if date_act <= date.today() and date_act >= date.today().replace(day=1):
                        res['done']['this_month'] += 1
                elif date_act < date.today().replace(day=1) and date_act >= date.today().replace(day=1) - relativedelta(months=+1):
                    res['done']['last_month'] += 1
        
        # Meetings
        min_date = datetime.now().strftime(DATETIME_FORMAT)
        max_date = (datetime.now() + timedelta(days=8)).strftime(DATETIME_FORMAT)
        meetings_domain = [
            ('start', '>=', min_date),
            ('start', '<=', max_date)
        ]
        # We need to add 'mymeetings' in the context for the search to be correct.
        meetings = self.pool.get('calendar.event').search_read(cr, uid, meetings_domain, ['start'], context=context.update({'mymeetings': 1}) if context else {'mymeetings': 1})
        for meeting in meetings:
            if meeting['start']:
                start = datetime.strptime(meeting['start'], DATETIME_FORMAT).date()
                if start == date.today():
                    res['meeting']['today'] += 1
                if start >= date.today() and start <= date.today() + timedelta(days=7):
                    res['meeting']['next_7_days'] += 1
        res['nb_opportunities'] = len(opportunities)
        user = self.pool('res.users').browse(cr, uid, uid, context=context)
        res['done']['target'] = user.target_sales_done
        res['won']['target'] = user.target_sales_won
        res['currency_id'] = user.company_id.currency_id.id
        #invoice column in dashboard
        account_invoice_domain = [
            ('state', 'in', ['open', 'paid']),
            ('user_id', '=', uid),
            ('date', '>=', date.today().replace(day=1) - relativedelta(months=+1)),
            ('type', 'in', ['out_invoice', 'out_refund'])
        ]

        invoice_ids = self.pool.get('account.invoice').search_read(cr, uid, account_invoice_domain, ['date', 'amount_untaxed_signed'], context=context)
        for inv in invoice_ids:
            if inv['date']:
                inv_date = datetime.strptime(inv['date'], tools.DEFAULT_SERVER_DATE_FORMAT).date()
                res['invoiced']['total'] += inv['amount_untaxed_signed']
                if inv_date <= date.today() and inv_date >= date.today().replace(day=1):
                    res['invoiced']['this_month'] += inv['amount_untaxed_signed']
                elif inv_date < date.today().replace(day=1) and inv_date >= date.today().replace(day=1) - relativedelta(months=+1):
                    res['invoiced']['last_month'] += inv['amount_untaxed_signed']
        res['invoiced']['target'] = self.pool('res.users').browse(cr, uid, uid, context=context).target_sales_invoiced
        #commision column in dashboard
        sales_ids = self.pool.get('sale.order').search_read(cr, uid, context=context)
        for sale in sales_ids:
            if sale['date_order'] and sale['state'] in ['sale', 'done']:
                sale_date = datetime.strptime(sale['date_order'], DATETIME_FORMAT).date()
                res['sales']['total'] += sale['sale_commission_store']
                if sale_date <= date.today() and sale_date >= date.today().replace(day=1):
                    res['sales']['this_month'] += sale['sale_commission_store']
                elif sale_date < date.today().replace(day=1) and sale_date >= date.today().replace(day=1) - relativedelta(months=+1):
                    res['sales']['last_month'] += sale['sale_commission_store']
        res['sales']['target'] = user.target_sales_commission
        return res
    #Sales Dashboard Target Row
    def modify_target_sales_dashboard(self, cr, uid, target_name, target_value, context=None):
        if target_name in ['won', 'done', 'invoiced', 'commission']:
            # bypass rights (with superuser_id)
            self.pool('res.users').write(cr, uid, [uid], {'target_sales_' + target_name: target_value}, context=context)
        else:
            raise UserError(_('This target does not exist.'))

class res_users(models.Model):
    _inherit = 'res.users'
    #Commission percentage fields based on customer type: New/Recurrent/Loyal
    new_customer = fields.Float(string='New Customer', store=True, readonly=False)
    recurrent_customer = fields.Float(string='Recurrent Customer', store=True, readonly=False)
    loyal_customer = fields.Float(string='Loyal Customer', store=True, readonly=False)
    target_sales_commission = fields.Integer('Commission in sale Orders Target')

class SaleOrder(models.Model):
    _inherit = "sale.order"
    #Function to get sales commision based on seted percentage and total won in oportunities
    @api.one
    def _get_sale_commission(self):
        invoices = self.env['sale.order'].search([('partner_id', '=', self.partner_id.name), ('state', 'in', ['sale', 'done'])])
        last_payment = date.today() - timedelta(days=1)
        invoices_dates = sorted([invoice.date_order for invoice in invoices])
        customers_names = [customer.partner_id.name for customer in invoices]
        # raise UserError(customers_names)
        if len(customers_names) == 0:
            self.sale_commission = self.amount_total * self.user_id.new_customer / 100
        else:
            if self.partner_id.name in customers_names:
                invoice_date = fields.Date.from_string(invoices_dates[-1])
                if last_payment <= invoice_date:
                    self.sale_commission = self.amount_total * self.user_id.loyal_customer / 100
                else:
                    self.sale_commission = self.amount_total * self.user_id.recurrent_customer / 100
            else:
                raise UserError('Something bad happened!')

    @api.one
    def _get_customer_type(self):
        # raise UserError(self.sale_commission_store)
        if self.sale_commission_store * 100 / self.amount_total == self.user_id.loyal_customer:
            self.customer_type = 'Loyal Customer'
        elif self.sale_commission_store * 100 / self.amount_total == self.user_id.recurrent_customer:
            self.customer_type = 'Recurrent Customer'
        else:
            self.customer_type = 'New Customer'
            

    responsible_id = fields.Many2one('res.partner', string='Responsible', change_default=True,
        required=False, readonly=True, states={'draft': [('readonly', False)]},
        track_visibility='always')
    sale_commission = fields.Float(string='Sales Commission', compute=_get_sale_commission)
    sale_commission_store = fields.Float(string='Sales Commission', related='sale_commission', store=True, readonly=True, track_visibility='always')
    customer_type = fields.Char(string='Customer Type', compute=_get_customer_type)
    customer_type_store = fields.Char(string='Customer Type', related='customer_type', store=True, readonly=True, track_visibility='always')

    @api.multi
    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()
        journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
        if not journal_id:
            raise UserError(_('Please define an accounting sale journal for this company.'))
        invoice_vals = {
            'name'              : self.client_order_ref or '',
            'origin'            : self.name,
            'type'              : 'out_invoice',
            'account_id'        : self.partner_invoice_id.property_account_receivable_id.id,
            'partner_id'        : self.partner_invoice_id.id,
            'responsible_id'    : self.responsible_id.id,
            'journal_id'        : journal_id,
            'currency_id'       : self.pricelist_id.currency_id.id,
            'comment'           : self.note,
            'payment_term_id'   : self.payment_term_id.id,
            'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
            'company_id'        : self.company_id.id,
            'user_id'           : self.user_id and self.user_id.id,
            'team_id'           : self.team_id.id
        }
        return invoice_vals

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    #Create a lead from Contacts page, with customer details
    @api.multi
    def create_lead(self):
        res = self.env['crm.lead'].sudo().create({
            'name'          :   self.name+' Lead',
            'partner_id'    :   self.id,
            'partner_name'  :   self.name,
            'street'        :   self.street,
            'street2'       :   self.street2,
            'city'          :   self.city,
            'state_id'      :   self.state_id.id,
            'zip'           :   self.zip,
            'country_id'    :   self.country_id.id,
            'phone'         :   self.phone,
            'mobile'        :   self.mobile,
            'fax'           :   self.fax,
            'email_from'    :   self.email,
            'description'   :   self.comment,
            }) 
        return {
            'name'          :   ('Lead'),
            'type'          :   'ir.actions.act_window',
            'view_type'     :   'form',
            'view_mode'     :   'form',
            'target'        :   'current', 
            'res_model'     :   'crm.lead',
            'view_id'       :   False,
            'domain'        :   [('partner_id','=',[res.id])],
            'nodestroy'     :   True,
            'res_id'        :   res.id,
            'flags'         :   {'form': {'action_buttons': True, 'options': {'mode': 'edit'}}}
            }