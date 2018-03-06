# -*- coding: utf-8 -*-
from openerp import _, fields, models, api
from datetime import datetime
import calendar
import uuid
import urlparse
import logging
_logger = logging.getLogger(__name__)


class event_event(models.Model):
    _inherit = 'event.event'

    @api.model
    def _default_course_id(self):
        events = self.env['event.event'].search([])
        qwarie_course_id = max([event['qwarie_course_id'] for event in events] or [0, ])
        return qwarie_course_id + 1

    @api.one
    @api.depends('exam_survey_id')
    def _get_exam_participants(self):
        self.exam_survey_participants_ids = self.exam_survey_id.user_input_ids.search([
            ('event_id', '=', self.id), ('survey_id', '=', self.exam_survey_id.id)
        ])

    @api.one
    @api.depends('feedback_survey_id')
    def _get_feedback_participants(self):
        self.feedback_survey_participants_ids = self.feedback_survey_id.user_input_ids.search([
            ('event_id', '=', self.id), ('survey_id', '=', self.feedback_survey_id.id)
        ])

    @api.one
    @api.depends('certificate_id')
    def _get_certificate_participants(self):
        self.certificate_id = self.exam_survey_id
        self.certificate_participants_ids = self.exam_survey_participants_ids

    @api.one
    @api.depends('address_id')
    def _get_training_customer(self):
        self.customer_id = self.address_id.parent_id or self.address_id

    trainer_id = fields.Many2one('res.users', string='Trainer', default=lambda self: self.env.user)
    assistant_id = fields.Many2one('res.users', string='Assistant Trainer')
    delegate_quota = fields.Char(string='Delegate Quota', track_visibility='onchange')
    available_seats = fields.Char(string='Available Seats', track_visibility='onchange')
    training_leader = fields.Char(string='Training Leader', track_visibility='onchange')
    customer_id = fields.Many2one('res.partner', string='Customer', compute='_get_training_customer')

    # custom Print fields
    printing_company = fields.Char(string='Printing company (URL)', track_visibility='onchange')
    ordered_date = fields.Date(string='Order date', track_visibility='onchange')
    ordered_by = fields.Many2one('res.partner', string='Ordered by', track_visibility='onchange')
    price = fields.Monetary(string='Order price', track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', track_visibility='onchange')
    order_number = fields.Char(string='Purchase order number', track_visibility='onchange')
    order_copies_number = fields.Integer(string='Number of copies ordered', track_visibility='onchange')
    billed_to = fields.Selection([
        ('0', 'Wess International'),
        ('1', 'Qwarie Ltd'),
        ('2', 'Qwarie EMEA')], string='Billed to', track_visibility='onchange')
    proposed_delivery_date = fields.Date(string='Proposed delivery date', track_visibility='onchange')
    delivered_to = fields.Many2one('res.partner', string='Delivery to', track_visibility='onchange')
    delivery_confirmed = fields.Datetime(string='Delivery confirmation', track_visibility='onchange')
    event_service = fields.Many2one('product.template', 'Product', track_visibility='onchange')
    qwarie_course_id = fields.Integer(string='Qwarie Course ID', default=_default_course_id)
    tracking_id = fields.Char(string='Tracking ID', track_visibility='onchange')
    tracking_link = fields.Char(string='Tracking Link', track_visibility='onchange')

    total_docs = fields.Integer(string='Total number of documents', track_visibility='onchange')
    paper_size = fields.Char(string='Paper Size', track_visibility='onchange')
    print_sides = fields.Selection([
        ('single', 'Single sided'),
        ('double', 'Double sided')], string='Printed Sides', track_visibility='onchange')
    ink_colour = fields.Selection([
        ('black', 'Black & White'),
        ('colour', 'Colour'),
        ('both', ('Colour and Black & White'))], string='Ink colour', track_visibility='onchange')
    paper_colour = fields.Char(string='Paper Colour', track_visibility='onchange')
    paper_finish = fields.Char(string='Paper Finish', track_visibility='onchange')
    paper_weight = fields.Char(string='Paper Weight', track_visibility='onchange')
    binding_type = fields.Char(string='Binding type', track_visibility='onchange')
    binding_color = fields.Char(string='Binding Colour', track_visibility='onchange')
    binding_position = fields.Char(string='Binding Position', track_visibility='onchange')
    hole_punching = fields.Char(string='Hole Punching', track_visibility='onchange')
    folding = fields.Char(string='Folding', track_visibility='onchange')
    protection = fields.Char(string='Protection', track_visibility='onchange')
    cover = fields.Char(string='Cover', track_visibility='onchange')
    print_material_url = fields.Char(string='Print material URL', track_visibility='onchange')
    responsible_person = fields.Char(string='Responsible person', track_visibility='onchange')
    responsible_email = fields.Char(string='Responsible email', track_visibility='onchange')
    day_begin = fields.Char(string='Start Day', compute='get_day_begin')
    day_end = fields.Char(string='End Day', compute='get_day_end')
    month_begin = fields.Char(string='Training Month', compute='get_month_begin')
    month_end = fields.Char(string='Training Month', compute='get_month_end')
    year_begin = fields.Char(string='Training year', compute='get_year_begin')
    year_end = fields.Char(string='Training year', compute='get_year_end')
    month = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    duration = fields.Integer('Duration', required=True, compute='get_duration')
    duration_h = fields.Integer('Course Duration', compute='_get_duration')
    training_subject = fields.Char('Training Subject')

    @api.one
    @api.depends('date_begin', 'date_end')
    def _get_duration(self):
        self.duration_h = self.duration * 7
    @api.one
    @api.depends('date_begin', 'date_end')
    def get_duration(self):
        start_date = fields.Date.from_string(self.date_begin)
        end_date = fields.Date.from_string(self.date_end)
        if start_date and end_date:
            duration = end_date - start_date
            self.duration = duration.days
    @api.model
    def get_day_begin(self):
        self.day_begin = self.date_begin.split(' ')[0]
        self.day_begin = self.day_begin.split('-')[2]
        return self.day_begin  
    @api.model
    def get_day_end(self):
        self.day_end = self.date_end.split(' ')[0]
        self.day_end = self.day_end.split('-')[2]
        return self.day_end
    @api.model
    def get_month_begin(self):
        self.month_begin = self.date_begin.split(' ')[0]
        self.month_begin = self.month_begin.split('-')[1]
        self.month_begin = self.month[int(self.month_begin)-1]
        return self.month_begin
    @api.model
    def get_month_end(self):
        self.month_end = self.date_end.split(' ')[0]
        self.month_end = self.month_end.split('-')[1]
        self.month_end = self.month[int(self.month_end)-1]
        return self.month_end
    @api.model
    def get_year_begin(self):
        self.year_begin = self.date_begin.split(' ')[0]
        self.year_begin = self.year_begin.split('-')[0]
        return self.year_begin
    @api.model
    def get_year_end(self):
        self.year_end = self.date_end.split(' ')[0]
        self.year_end = self.year_end.split('-')[0]
        return self.year_end
    
    attachment_ids = fields.Many2many('ir.attachment', 'events_ir_attachments_rel', 'event_id', 'attachment_id', 'Attachments')

    #custom CTU fields
    site_survey = fields.Selection([
        ('not_required', 'Not Required'),
        ('ordered', 'Ordered'),
        ('performed', 'Performed')], string='Site Survey', track_visibility='onchange')
    ctu_order = fields.Selection([
        ('ctu_not_required', 'CTU not required'),
        ('ctu_without_internet', 'CTU without internet'),
        ('ctu_with_internet', 'CTU with internet'),
        ('mi-fi_only', 'Mi-Fi only')], string='CTU Order', default='ctu_not_required', track_visibility='onchange')
    ctu_number = fields.Selection([
        ('none', '0'), ('1', '1'), ('2', '2'),
        ('3', '3'), ('4', '4'), ('5', '5'),
        ('6', '6'), ('7', '7'), ('8', '8'),
        ('9', '9'), ('10', '10')], string='CTU Number', default="none", track_visibility='onchange')
    ctu_status = fields.Selection([
        ('unknown', 'Not known'), ('progress', 'In progress'),
        ('ready', 'Ready to dispatch'), ('transit', 'In Transit'),
        ('delivered', 'Delivered')], default='unknown', string='Status', track_visibility='onchange')

    #survey links
    exam_survey_id = fields.Many2one('survey.survey', string='Training Exam', track_visibility='onchange')
    exam_survey_participants_ids = fields.One2many('survey.user_input', string='Participants', compute='_get_exam_participants', readonly=False)
    feedback_survey_id = fields.Many2one('survey.survey', string='Training Feedback', track_visibility='onchange')
    feedback_survey_participants_ids = fields.One2many('survey.user_input', string='Participants', compute='_get_feedback_participants', readonly=False)
    certificate_id = fields.Many2one('survey.survey', string='Training Certificate', track_visibility='onchange')
    certificate_participants_ids = fields.One2many('survey.user_input', string='Participants', compute='_get_certificate_participants', readonly=False)

    travel_ids = fields.One2many('event.travel', 'event_id', string='Travel Arrangements', track_visibility='onchange')
    accommodation_ids = fields.One2many('event.accommodation', 'event_id', string='Accommodation', track_visibility='onchange')
    note_ids = fields.One2many('event.notes', 'event_id', string='Notes', track_visibility='onchange')


    @api.model
    def _default_event_mail_ids(self):
        return False
        # return [(0, 0, {
        #     'interval_unit': 'now',
        #     'interval_type': 'after_sub',
        #     'template_id': self.env.ref('qwarie_customization.training_subscription')
        # })]

    @api.multi
    @api.depends('name', 'date_begin', 'date_end')
    def name_get(self):
        result = []
        for event in self:
            date_begin = fields.Datetime.from_string(event.date_begin)
            date_end = fields.Datetime.from_string(event.date_end)
            dates = [fields.Date.to_string(fields.Datetime.context_timestamp(event, dt)) for dt in [date_begin, date_end] if dt]
            dates = sorted(set(dates))
            dates = [fields.Datetime.from_string(date).strftime('%a, %d %b %Y') for date in dates]
            result.append((event.id, '{course} {dates}'.format(course=event.name, dates=' - '.join(dates))))
        return result

    @api.model
    def create(self, vals):
        res = super(event_event, self).create(vals)
        if res.organizer_id:
            res.message_unsubscribe([res.organizer_id.id])
        return res

    @api.multi
    def write(self, vals):
        # exam and feedback ids are computed one2many fields
        # they are not store(allows for a more dynamic domain)
        # unlink operations must be done manually
        if vals.get('feedback_survey_participants_ids'):
            for survey in vals.get('feedback_survey_participants_ids'):
                operation, input_id, boolVal = survey
                if operation == 2: # unlink operation id
                    user_input = self.env['survey.user_input'].browse(input_id)
                    user_input.unlink()
        if vals.get('exam_survey_participants_ids'):
            for survey in vals.get('exam_survey_participants_ids'):
                operation, input_id, boolVal = survey
                if operation == 2: # unlink operation id
                    user_input = self.env['survey.user_input'].browse(input_id)
                    user_input.unlink()
        if vals.get('certificate_participants_ids'):
            for survey in vals.get('certificate_participants_ids'):
                operation, input_id, boolVal = survey
                if operation == 2: # unlink operation id
                    user_input = self.env['survey.user_input'].browse(input_id)
                    user_input.unlink()
        # when changing the course exam
        if vals.get('exam_survey_id'):
            for delegate in self.registration_ids:
                # remove delagetes from the previous survey
                delegate_survey = self.env['survey.user_input'].search([
                    ('survey_id', '=', self.exam_survey_id.id),
                    ('event_id', '=', self.id),
                    ('participant_name', '=', delegate.name),
                    ('email', '=', delegate.email)])
                if delegate_survey:
                    delegate_survey.unlink()

                # create new entry for delegate to the new survey
                token = uuid.uuid4().__str__()
                self.env['survey.user_input'].create({
                    'survey_id': vals['exam_survey_id'],
                    'event_id': self.id,
                    'date_create': datetime.now(),
                    'type': 'link',
                    'state': 'new',
                    'token': token,
                    'participant_name': delegate.name,
                    'email': delegate.email
                })
        # when changing the course feedback
        if vals.get('feedback_survey_id'):
            for delegate in self.registration_ids:
                # remove delagetes from the previous survey
                delegate_survey = self.env['survey.user_input'].search([
                    ('survey_id', '=', self.feedback_survey_id.id),
                    ('event_id', '=', self.id),
                    ('participant_name', '=', delegate.name),
                    ('email', '=', delegate.email)])
                if delegate_survey:
                    delegate_survey.unlink()

                # create new entry for delegate to the new survey
                token = uuid.uuid4().__str__()
                self.env['survey.user_input'].create({
                    'survey_id': vals['feedback_survey_id'],
                    'event_id': self.id,
                    'date_create': datetime.now(),
                    'type': 'link',
                    'state': 'new',
                    'token': token,
                    'participant_name': delegate.name,
                    'email': delegate.email
                })

        # when changing the course feedback
        if vals.get('certificate_id'):
            for delegate in self.registration_ids:
                # remove delagetes from the previous survey
                delegate_survey = self.env['survey.user_input'].search([
                    ('survey_id', '=', self.certificate_id.id),
                    ('event_id', '=', self.id),
                    ('participant_name', '=', delegate.name),
                    ('email', '=', delegate.email)])
                if delegate_survey:
                    delegate_survey.unlink()

                # create new entry for delegate to the new survey
                token = uuid.uuid4().__str__()
                self.env['survey.user_input'].create({
                    'survey_id': vals['certificate_id'],
                    'event_id': self.id,
                    'date_create': datetime.now(),
                    'type': 'link',
                    'state': 'new',
                    'token': token,
                    'participant_name': delegate.name,
                    'email': delegate.email
                })
        res = super(event_event, self).write(vals)
        return res

    @api.one
    def email_survey(self):
        survey_type = self.env.context.get('survey_type')
        if survey_type == 'exam':
            survey_id = self.exam_survey_id.id
        else:
            survey_id = self.feedback_survey_id.id
            
        # send survey via email to every enrolled delegate
        for delegate in self.registration_ids:
            delegate_survey = self.env['survey.user_input'].search([
                        ('survey_id', '=', survey_id),
                        ('event_id', '=', self.id),
                        ('participant_name', '=', delegate.name),
                        ('email', '=', delegate.email)], limit=1, order="id desc")
            if delegate_survey and delegate_survey.token:
                delegate_survey.email_survey()

    @api.multi
    def view_exam_results(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '{url}/{id}'.format(url=self.exam_survey_id.result_url, id=self.id)
        }

    @api.multi
    def view_feedback_results(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': 'Course Feedback Results',
            'target': 'new',
            'url': '{url}/{id}'.format(url=self.feedback_survey_id.result_url, id=self.id)
        }


class event_registration(models.Model):
    _inherit = 'event.registration'

    email = fields.Char(string='E-mail', readonly=False)
    name = fields.Char(string='Attendee Name', index=True)
    event_id = fields.Many2one(
        'event.event', string='Event', required=False,
        readonly=True, states={'draft': [('readonly', False)]})

    @api.model
    def create(self, vals):
        # strip spaces from front and back... people are lazy
        if vals.get('email'):
            vals['email'] = vals['email'].strip()
        if vals.get('name'):
            vals['name'] = vals['name'].strip()

        # when adding delegate, also add them as participants to exam
        res = super(event_registration, self).create(vals)
        # nameParts = res.name.split(' ')
        # [firstName, lastName] = [nameParts[0], nameParts[len(nameParts) - 1] if len(nameParts) > 1  else False]
        # registration = self.env['mail.mass_mailing.contact'].search([('name', '=', firstName), ('last_name', '=', lastName),('email', '=', res.email), ('list_id', '=', 2)])
        # if len(registration) == 0:
        #     self.env['mail.mass_mailing.contact'].create({
        #         'list_id': 2,
        #         'name': firstName,
        #         'last_name': lastName,
        #         'email': res.email,
        #     })
        if res.event_id.exam_survey_id:
            token = uuid.uuid4().__str__()
            self.env['survey.user_input'].create({
                'survey_id': res.event_id.exam_survey_id.id,
                'event_id': res.event_id.id,
                'date_create': datetime.now(),
                'type': 'link',
                'state': 'new',
                'token': token,
                'participant_name': res.name,
                'email': res.email
            })
        if res.event_id.feedback_survey_id:
            token = uuid.uuid4().__str__()
            self.env['survey.user_input'].create({
                'survey_id': res.event_id.feedback_survey_id.id,
                'event_id': res.event_id.id,
                'date_create': datetime.now(),
                'type': 'link',
                'state': 'new',
                'token': token,
                'participant_name': res.name,
                'email': res.email
            })
        return res

    @api.multi
    def unlink(self):
        # when removing delegates also remove them as participants to exam and feedback
        for delegate in self:
            if (delegate.event_id.exam_survey_id):
                delegate_survey = self.env['survey.user_input'].search([
                        ('survey_id', '=', delegate.event_id.exam_survey_id.id),
                        ('event_id', '=', delegate.event_id.id),
                        ('participant_name', '=', delegate.name),
                        ('email', '=', delegate.email)])
                if (delegate_survey):
                    delegate_survey.unlink()

            if (delegate.event_id.feedback_survey_id):
                delegate_survey = self.env['survey.user_input'].search([
                        ('survey_id', '=', delegate.event_id.feedback_survey_id.id),
                        ('event_id', '=', delegate.event_id.id),
                        ('participant_name', '=', delegate.name),
                        ('email', '=', delegate.email)])
                if (delegate_survey.id):
                    delegate_survey.unlink()
            registration = self.env['event.registration'].search([('name', '=', delegate.name), ('email', '=', delegate.email)])
            nameParts = delegate.name.split(' ')
            [firstName, lastName] = [nameParts[0], nameParts[len(nameParts) - 1] if len(nameParts) > 1  else False]
            subscription = self.env['mail.mass_mailing.contact'].search([('name', '=', firstName), ('last_name', '=', lastName), ('email', '=', delegate.email), ('list_id', '=', 2)])
            if len(subscription) > 0 and len(registration) == 1:
                subscription.unlink()
        return super(event_registration, self).unlink()

    @api.multi
    def write(self, vals):
        # when modifying delegates name/email also modify their entry in the to exam and feedback
        if vals.get('name') or vals.get('email'):
            change = {}
            if vals.get('name'):
                change['participant_name'] = vals['name']
                nameParts = self.name.split(' ')
                [firstName, lastName] = [nameParts[0], nameParts[len(nameParts) - 1] if len(nameParts) > 1  else False]
                newNameParts = vals.get('name').split(' ')
                [newFirstName, newLastName] = [nameParts[0], newNameParts[len(newNameParts) - 1] if len(newNameParts) > 1  else False]
                subscription = self.env['mail.mass_mailing.contact'].search([('name', '=', firstName), ('last_name', '=', lastName), ('email', '=', self.email), ('list_id', '=', 2)])
                if subscription:
                    subscription.write({
                        'name': newFirstName,
                        'last_name': newLastName,
                        'email': vals.get('email') or self.email,
                    })
            if vals.get('email'):
                change['email'] = vals['email']
            if (self.event_id.exam_survey_id):
                delegate_survey = self.env['survey.user_input'].search([
                        ('survey_id', '=', self.event_id.exam_survey_id.id),
                        ('event_id', '=', self.event_id.id),
                        ('participant_name', '=', self.name),
                        ('email', '=', self.email)
                ])
                if delegate_survey:
                    delegate_survey.write(change)
            if (self.event_id.feedback_survey_id):
                delegate_survey = self.env['survey.user_input'].search([
                    ('survey_id', '=', self.event_id.feedback_survey_id.id),
                    ('event_id', '=', self.event_id.id),
                    ('participant_name', '=', self.name),
                    ('email', '=', self.email)
                ])
                if delegate_survey:
                    delegate_survey.write(change)
        res = super(event_registration, self).write(vals)
        return res

class event_travel(models.Model):
    _name = 'event.travel'
    _description = 'Travel Arrangement'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    event_id = fields.Many2one('event.event', string='Event', ondelete='cascade', required=True)
    name = fields.Text(string='Name')
    travel_by = fields.Selection([
                    ('air', 'Airplane'),
                    ('rail', 'Rail'),
                    ('car_private', 'Private Car'),
                    ('car_rental', 'Rental Car')
                ], string='Travel form', track_visibility='onchange')
    travel_type = fields.Selection([('one_way', "One Way Trip"), ('round', 'Round Trip')], string='Status', track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    travel_cost = fields.Monetary(string='Cost of travel', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', required=True, store=True)

    # Outbound
    travel_departure_time = fields.Datetime(string='Departure time', track_visibility='onchange')
    travel_arrival_time = fields.Datetime(string='Arrival time', track_visibility='onchange')
    outbound_from = fields.Char(string='Leaving From', track_visibility='onchange')
    outbound_to = fields.Char(string='Going to', track_visibility='onchange')
    outbound_carrier = fields.Char(string='Carrier', track_visibility='onchange')
    outbound_flight_number = fields.Char(string='Flight number', track_visibility='onchange')
    outbound_last_checkin = fields.Datetime(string='Last check-in', track_visibility='onchange')

    # Inbound
    inbound_travel_departure_time = fields.Datetime(string='Departure time', track_visibility='onchange')
    inbound_travel_arrival_time = fields.Datetime(string='Arrival time', track_visibility='onchange')
    inbound_from = fields.Char(string='Leaving From', track_visibility='onchange')
    inbound_to = fields.Char(string='Going to', track_visibility='onchange')
    inbound_carrier = fields.Char(string='Carrier', track_visibility='onchange')
    inbound_flight_number = fields.Char(string='Flight number', track_visibility='onchange')
    inbound_last_checkin = fields.Datetime(string='Last check-in', track_visibility='onchange')

    # type: air
    outbound_departure_airport_id = fields.Many2one('airport.airport', string='Departure airport')#, track_visibility='onchange')
    outbound_arrival_airport_id = fields.Many2one('airport.airport', string='Arrival airport')#, track_visibility='onchange')
    inbound_departure_airport_id = fields.Many2one('airport.airport', string='Departure airport')#, track_visibility='onchange')
    inbound_arrival_airport_id = fields.Many2one('airport.airport', string='Arrival airport')#, track_visibility='onchange')

    # type: rail
    outbound_rail_class = fields.Char(string='Class', track_visibility='onchange')
    inbound_rail_class = fields.Char(string='Class', track_visibility='onchange')
    rail_discount = fields.Char(string='Railcards Discount', track_visibility='onchange')

    #type: ride
    car_type = fields.Char(string='Car type', track_visibility='onchange')
    car_company = fields.Char(string='Rental car company', track_visibility='onchange')

    travel_notes = fields.Text(string='Notes', track_visibility='onchange')

    @api.model
    def create(self, vals):
        event = self.env['event.event'].browse(vals['event_id'])
        vals['name'] = '{course} ({date_start} - {date_end}) Travel Arrangement'.format(
                            course=event.name,
                            date_start=fields.Datetime.from_string(event.date_begin).strftime('%a, %d %b %Y'),
                            date_end=fields.Datetime.from_string(event.date_end).strftime('%a, %d %b %Y'))
        res = super(event_travel, self).create(vals)
        event.message_post(type="comment", subtype='mail.mt_note', notify=True, body='Travel Arrangement added')
        for follower in event.message_follower_ids:
            res.message_subscribe(partner_ids=[follower.partner_id.id], subtype_ids=[subtype.id for subtype in follower.subtype_ids])
        return res


class event_accommodation(models.Model):
    _name = 'event.accommodation'
    _description = 'Event Accommodation'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    event_id = fields.Many2one('event.event', string='Event', ondelete='cascade', required=True)
    name = fields.Text(string='Name')
    accommodation_type = fields.Selection([
            ('5star', '5 star Hotel'),
            ('4star', '4 star Hotel'),
            ('3star', '3 star Hotel'),
            ('2star', '2 star Hotel'),
            ('1star', '1 star Hotel'),
            ('airbnb', 'Airbnb')
        ], string='Accommodation type', track_visibility='onchange')
    accommodation_name = fields.Char(string='Property name', track_visibility='onchange')
    accommodation_check_in = fields.Datetime(string='Check In', track_visibility='onchange')
    accommodation_check_out = fields.Datetime(string='Check Out', track_visibility='onchange')
    accommodation_price = fields.Monetary(string='Price', track_visibility='onchange')
    accommodation_status = fields.Selection([('booked', "Only Booked"), ('paid', 'Paid')], string='Status', track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', required=True, store=True)
    accommodation_notes = fields.Text(string='Notes', track_visibility='onchange')

    @api.model
    def create(self, vals):
        event = self.env['event.event'].browse(vals['event_id'])
        vals['name'] = '{course} ({date_start} - {date_end}) Accommodation'.format(
                            course=event.name,
                            date_start=fields.Datetime.from_string(event.date_begin).strftime('%a, %d %b %Y'),
                            date_end=fields.Datetime.from_string(event.date_end).strftime('%a, %d %b %Y'))
        res = super(event_accommodation, self).create(vals)
        event.message_post(type="comment", subtype='mail.mt_note', notify=True, body='Accommodation added')
        for follower in event.message_follower_ids:
            res.message_subscribe(partner_ids=[follower.partner_id.id], subtype_ids=[subtype.id for subtype in follower.subtype_ids])
        return res


class event_notes(models.Model):
    _name = 'event.notes'
    _description = 'Event Note'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Text(string='Name')
    event_id = fields.Many2one('event.event', string='Event', ondelete='cascade', required=True)
    description = fields.Text(string="Description", required=True, track_visibility='onchange')

    @api.model
    def create(self, vals):
        event = self.env['event.event'].browse(vals['event_id'])
        vals['name'] = '{course} ({date_start} - {date_end}) Note'.format(
                            course=event.name,
                            date_start=fields.Datetime.from_string(event.date_begin).strftime('%a, %d %b %Y'),
                            date_end=fields.Datetime.from_string(event.date_end).strftime('%a, %d %b %Y'))
        res = super(event_notes, self).create(vals)
        event.message_post(type="comment", subtype='mail.mt_note', notify=True, body='Note added')
        for follower in event.message_follower_ids:
            res.message_subscribe(partner_ids=[follower.partner_id.id], subtype_ids=[subtype.id for subtype in follower.subtype_ids])
        return res

class calendar_event(models.Model):
    _inherit = 'calendar.event'

    qw_event_id = fields.Many2one('event.event', string='Related Event', track_visibility='onchange')
