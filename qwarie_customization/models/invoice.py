# -*- coding: utf-8 -*-
from openerp import fields, models, api
from dateutil.relativedelta import relativedelta
import json
from openerp.exceptions import UserError

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.one
    @api.depends('payment_move_line_ids.amount_residual')
    def _get_payment_date(self):
        payment = json.loads(self.payments_widget)
        if payment:
            self.payment_date = payment['content'][0]['date']
    
    @api.model
    def _default_currency(self):
        journal = self._default_journal()
        return journal.currency_id or journal.company_id.currency_id or self.env.user.company_id.currency_id
        
    @api.one
    def _get_vat_name(self):
        for invoice_line_ids in self.invoice_line_ids:
            for invoice_line_tax_ids in invoice_line_ids.invoice_line_tax_ids:
                vat_name = invoice_line_tax_ids.name
                self.vat_name = vat_name
    
    @api.one
    @api.depends('state')
    def _compute_my_number(self):
        if self.state == 'draft':
                self.my_number = 'DRAFT'
        elif self.state == 'open':
                self.my_number = self.number
        elif self.state == 'paid':
                self.my_number = self.number

    my_number = fields.Char(store=True, compute='_compute_my_number')
    responsible_id = fields.Many2one('res.partner', string='Responsible', change_default=True,
        required=False, readonly=False, states={'draft': [('readonly', False)]},
        track_visibility='always')
    payment_date = fields.Date('Payment Date', compute='_get_payment_date', store=True)
    purchase_order = fields.Char(string='Purchase Order', readonly=True, states={'draft': [('readonly', False)]})
    supplier_id = fields.Char(string='Supplier ID', readonly=True, states={'draft': [('readonly', False)]})
    invoice_line_ids = fields.One2many('account.invoice.line', 'invoice_id', string='Invoice Lines', oldname='invoice_line',
        readonly=False, copy=True)
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True,
        required=True, readonly=False, states={'draft': [('readonly', False)]},
        track_visibility='always')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', oldname='payment_term',
        readonly=False, states={'draft': [('readonly', False)]},
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. If you keep the payment term and the due date empty, it means direct payment. "
             "The payment term may compute several due dates, for example 50% now, 50% in one month.")
    date_invoice = fields.Date(string='Invoice Date',
        readonly=False, states={'draft': [('readonly', False)]}, index=True,
        help="Keep empty to use the current date", copy=False)
    date_due = fields.Date(string='Due Date',
        readonly=False, states={'draft': [('readonly', False)]}, index=True, copy=False,
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. The payment term may compute several due dates, for example 50% "
             "now and 50% in one month, but if you want to force a due date, make sure that the payment "
             "term is not set on the invoice. If you keep the payment term and the due date empty, it "
             "means direct payment.")
    tax_line_ids = fields.One2many('account.invoice.tax', 'invoice_id', string='Tax Lines', oldname='tax_line',
        readonly=False, states={'draft': [('readonly', False)]}, copy=True)
    state = fields.Selection([
            ('draft','Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('open', 'Unpaid'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used the invoice does not have an invoice number.\n"
             " * The 'Unpaid' status is used when user create invoice, an invoice number is generated. Its in unpaid status till user does not pay invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    name = fields.Char(string='Reference/Description', index=True,
        readonly=False, states={'draft': [('readonly', False)]}, copy=False, help='The name that will be used on account move lines')
    # currency_id = fields.Many2one('res.currency', string='Currency',
    #     required=True, readonly=False, states={'draft': [('readonly', False)]},
    #     default=_default_currency, track_visibility='always')
    customer_vat = fields.Char('Customer VAT')
    vat_name = fields.Char(string='vat name', invisible='1', compute=_get_vat_name)
    comment = fields.Text('Additional Information', readonly=False, states={'draft': [('readonly', False)]})
    po_number = fields.Char(string="PO Number")

    @api.onchange('payment_term_id', 'date_invoice', 'date_due')
    def _onchange_payment_term_date_invoice(self):
        date_invoice = self.date_invoice
        date_due = self.date_due
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        if not self.payment_term_id:
            # When no payment term defined
            self.date_due = self.date_due or self.date_invoice
        else:
            pterm = self.payment_term_id
            if self.payment_term_id.id in [4, 8, 15, ]:
                pterm_list = pterm.with_context(currency_id=self.currency_id.id).compute(value=1, date_ref=date_invoice, date_ref2=date_due)[0]
            else:
                pterm_list = pterm.with_context(currency_id=self.currency_id.id).compute(value=1, date_ref=date_invoice)[0]
            self.date_due = max(line[0] for line in pterm_list)


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    @api.one
    def compute(self, value, date_ref=False, date_ref2=False):
        date_ref = date_ref or fields.Date.today()
        amount = value
        result = []
        if self.env.context.get('currency_id'):
            currency = self.env['res.currency'].browse(self.env.context['currency_id'])
        else:
            currency = self.env.user.company_id.currency_id
        prec = currency.decimal_places
        for line in self.line_ids:
            if line.value == 'fixed':
                amt = round(line.value_amount, prec)
            elif line.value == 'percent':
                amt = round(value * (line.value_amount / 100.0), prec)
            elif line.value == 'balance':
                amt = round(amount, prec)
            if amt:
                if date_ref2:
                    next_date = fields.Date.from_string(date_ref2)
                else:
                    next_date = fields.Date.from_string(date_ref)
                if line.option == 'day_after_invoice_date' or 'custom_due_date':
                    next_date += relativedelta(days=line.days)
                elif line.option == 'fix_day_following_month':
                    next_first_date = next_date + relativedelta(day=1, months=1) # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days - 1)
                elif line.option == 'last_day_following_month':
                    next_date += relativedelta(day=31, months=1) # Getting last day of next month
                elif line.option == 'last_day_current_month':
                    next_date += relativedelta(day=31, months=0) # Getting last day of next month
                result.append((fields.Date.to_string(next_date), amt))
                amount -= amt
        amount = reduce(lambda x, y: x + y[1], result, 0.0)
        dist = round(value - amount, prec)
        if dist:
            last_date = result and result[-1][0] or fields.Date.today()
            result.append((last_date, dist))
        return result


class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    option = fields.Selection([
        ('day_after_invoice_date', 'Day(s) after the invoice date'),
        ('fix_day_following_month', 'Fixed day of the following month'),
        ('last_day_following_month', 'Last day of following month'),
        ('last_day_current_month', 'Last day of current month'),
        ('custom_due_date', 'Custom Due Date'),
    ], default='day_after_invoice_date', required=True, string='Options')
