# -*- coding: utf-8 -*-
from openerp import _, fields, models, api

from collections import OrderedDict
from openerp.addons.website.models.website import slug
import uuid
import urlparse
import time
from datetime import datetime
from openerp.exceptions import UserError
import json
import logging
from email.Utils import formataddr
_logger = logging.getLogger(__name__)

class survey_survey(models.Model):
    _inherit = 'survey.survey'

    @api.one
    def get_l1_total_score(self):
        l1_score = 0
        if not self.quizz_mode and not self._has_questions:
            self.l1_total_score = 0
        for page in self.page_ids:
            for question in page.question_ids:
                if question.max_score == 1:
                    l1_score += question.max_score
        self.l1_total_score = l1_score

    @api.one
    def get_l2_total_score(self):
        l2_score = 0
        if not self.quizz_mode and not self._has_questions:
            self.l2_total_score = 0
        for page in self.page_ids:
            for question in page.question_ids:
                if question.max_score == 2:
                    l2_score += question.max_score
        self.l2_total_score = l2_score

    title2 = fields.Char('Exam Title', related="title")
    type = fields.Selection([
        ('exam', 'Exam'),
        ('feedback', 'Feedback'),
        ('recruitment', 'Recruitment'),
        ('preliminary', 'PTAMS'),
        ('other', 'Other')], string='Type', default=lambda self: 'preliminary' if self.env.user.partner_id.customer == True else 'exam', required=True)
    is_active = fields.Boolean(string='Is Active', default=True)
    customer_id = fields.Many2one('res.partner', string='Customer', default=lambda self: self.env.user.partner_id.parent_id)
    user_input_ids = fields.One2many('survey.user_input', 'survey_id', 'User responses', readonly=False)
    l1_total_score = fields.Integer(string='L1 Total Score', compute='get_l1_total_score')
    l2_total_score = fields.Integer(string='L2 Total Score', compute='get_l2_total_score')
    duration = fields.Char('Exam duration')

    @api.one
    def email_survey(self):
        # send survey via email to every enrolled delegate
        for delegate in self.user_input_ids:
            if not delegate.email_sent:
                delegate.email_survey()

    def prepare_result(self, cr, uid, question, current_filters=None, context=None):
        result_summary = super(survey_survey, self).prepare_result(cr, uid, question, current_filters, context)
        # Calculate and return statistics for choice
        if question.type in ['simple_choice', 'multiple_choice']:
            answers = OrderedDict()
            comments = []
            for label in question.labels_ids:
                answers.update({label.id: {'text': label.value, 'count': 0, 'answer_id': label.id}})
            for input_line in question.user_input_line_ids:
                if input_line.answer_type == 'suggestion' and answers.get(input_line.value_suggested.id) and (not(current_filters) or input_line.user_input_id.id in current_filters):
                    answers[input_line.value_suggested.id]['count'] += 1
                if input_line.answer_type == 'text' and (not(current_filters) or input_line.user_input_id.id in current_filters):
                    comments.append(input_line)
            result_summary = {'answers': answers.values(), 'comments': comments}
        return result_summary

    @api.onchange('title2')
    def _onchange_title(self):
        self.title = self.title2
        
    @api.model
    def create(self, vals):
        if vals.get('type') in ['exam', 'preliminary']:
            vals['quizz_mode'] = True
        res = super(survey_survey, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        if vals.get('type') in ['exam', 'preliminary']:
            vals['quizz_mode'] = True
        res = super(survey_survey, self).write(vals)
        return res

    def action_result_survey(self, cr, uid, ids, context=None):
        ''' Open the website page with the survey results view '''
        context = dict(context or {}, relative_url=True)
        return {
            'type': 'ir.actions.act_url',
            'name': "Results of the Survey",
            'target': 'new',
            'url': self.read(cr, uid, ids, ['result_url'], context=context)[0]['result_url']
        }

class mail_compose_message(models.Model):
    _inherit = 'mail.compose.message'

    def send_mail(self, cr, uid, ids, context=None):
        context = context or {}
        if context.get('default_model') == 'addition' and context.get('default_res_id') and context.get('mark_so_as_sent'):
            context = dict(context, mail_post_autofollow=True)
        return super(mail_compose_message, self).send_mail(cr, uid, ids, context=context)

class survey_user_input(models.Model):
    _inherit = "survey.user_input"

    #create training function
    @api.multi
    @api.model
    def action_create_training(self):
        res = self.env['event.event'].sudo().create({
                'name': self[0].survey_id.customer_id.name,
                'date_begin': datetime.now(),
                'date_end': datetime.now(),
                'ctu_order': 'ctu_not_required',
                # 'address_id': self.survey_id.customer_id,
                })  
        for stat in self:
            self.env['event.registration'].create({
                'name': stat.participant_name,
                'email': stat.email,
                'event_id': res.id      
            })
            event = [attendee.id for attendee in stat.attendee_ids]
            event.append(res.id)
            stat.write({'attendee_ids': [(6, 0, event)]})
        res_id = res.id
        return res_id

    #adding an participant to a specific training
    @api.multi
    @api.model
    def add_participant(self):
        list1 = [x.id for x in self.attendee_ids]
        if len(list1) > 1:
            while len(list1) > 1:
                list2 = list1[len(list1)-1]
                res = self.env['event.registration'].search([('event_id', '=', list2)])      
                names = [participant.name for participant in res]
                if (self.participant_name in names):
                    list1.pop()
                else:
                    res = self.env['event.registration'].search([('event_id', '=', list2)])
                    names = [participant.id for participant in res]
                    if not (self.id in names):
                        for stat in self:
                            self.env['event.registration'].create({
                                'name': stat.participant_name,
                                'email': stat.email,
                                'event_id': list2
                            })
                            res_id = list2
                        break
            else:
                raise UserError('Attendee is already participating at this trainings!')
        elif len(list1) == 1:
            for selfie in self.attendee_ids:
                res = self.env['event.registration'].search([('event_id', '=', list1)])
                names = [participant.name for participant in res]
                if not (self.participant_name in names):
                    for stat in self:
                        self.env['event.registration'].create({
                            'name': stat.participant_name,
                            'email': stat.email,
                            'event_id': selfie.id
                        })
                        res_id = selfie.id
                else:
                    raise UserError("Attendee is already participating at this training!")
        else:
            raise UserError('Select a training!')

    @api.multi
    def certificate_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        self.state = 'done'
        return self.env['report'].get_action(self, 'qwarie_customization.training_certificate')

    
    @api.multi
    def email_certificate(self):
        """ Open a window to compose an email, with the certificate template
            message loaded by default
        """
        self.ensure_one()
        template = self.env.ref('qwarie_customization.email_template_certificate', False)
        self.env['mail.template'].browse(template.id).send_mail(self.id)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='survey.user_input',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            mark_invoice_as_sent=True,
        )
        # raise UserError(default_model)
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
       }

    @api.model
    def message_get_reply_to(self, res_ids, default=None):
        """ Returns the preferred reply-to email address that is basically the
        alias of the document, if it exists. Override this method to implement
        a custom behavior about reply-to for generated emails. """
        model_name = self.env.context.get('thread_model') or self._name
        alias_domain = self.env['ir.config_parameter'].get_param("mail.catchall.domain")
        res = dict.fromkeys(res_ids, False)

        # alias domain: check for aliases and catchall
        aliases = {}
        doc_names = {}
        if alias_domain:
            if model_name and model_name != 'mail.thread' and res_ids:
                mail_aliases = self.env['mail.alias'].sudo().search([
                    ('alias_parent_model_id.model', '=', model_name),
                    ('alias_parent_thread_id', 'in', res_ids),
                    ('alias_name', '!=', False)])
                # take only first found alias for each thread_id, to match
                # order (1 found -> limit=1 for each res_id)
                for alias in mail_aliases:
                    if alias.alias_parent_thread_id not in aliases:
                        aliases[alias.alias_parent_thread_id] = '%s@%s' % (alias.alias_name, alias_domain)
                doc_names.update(
                    dict((ng_res[0], ng_res[1])
                         for ng_res in self.env[model_name].sudo().browse(aliases.keys()).name_get()))
            # left ids: use catchall
            left_ids = set(res_ids).difference(set(aliases.keys()))
            if left_ids:
                catchall_alias = self.env['ir.config_parameter'].get_param("mail.catchall.alias")
                if catchall_alias:
                    aliases.update(dict((res_id, '%s@%s' % (catchall_alias, alias_domain)) for res_id in left_ids))
            # compute name of reply-to
            company_name = self.env.user.company_id.name
            for res_id in aliases.keys():
                email_name = '%s%s' % (company_name, doc_names.get(res_id) and (' ' + doc_names[res_id]) or '')
                email_addr = aliases[res_id]
                res[res_id] = formataddr((email_name, email_addr))
        left_ids = set(res_ids).difference(set(aliases.keys()))
        if left_ids:
            res.update(dict((res_id, default) for res_id in res_ids))
        return res

    @api.one
    def _get_max_score(self):
        total_score = 0
        for page in self.survey_id.page_ids:
            total_score += sum([question.max_score for question in page.question_ids])
        self.max_total_score = total_score

    @api.one
    @api.depends('max_total_score', 'quizz_score')
    def _get_survey_score(self):
       if self.max_total_score < 100:
            if self.quizz_score > 0:
                self.quizz_score_percentage = "{score:.0f}%".format(score=(int(self.quizz_score) * 100)/int(self.max_total_score))
            else:
                self.quizz_score_percentage = "0%"

    @api.one
    def _get_l1_score(self):
        if self.survey_id.l1_total_score == 0 or self.state == 'new':
            self.l1_score = '-'
            return
        l1_score = 0
        for user_input in [input_line for input_line in self.user_input_line_ids if input_line.quizz_mark == 1]:
           l1_score += user_input.quizz_mark
        percentage = "{score:.0f}%".format(score=l1_score * 100 / self.survey_id.l1_total_score)
        self.l1_score = "{score} out of {total} points ({percentage})".format(score=int(l1_score), total=self.survey_id.l1_total_score, percentage=percentage)
    
    @api.one
    def _get_l2_score(self):
        if self.survey_id.l2_total_score == 0 or self.state == 'new':
            self.l2_score = '-'
            return
        l2_score = 0
        for user_input in [input_line for input_line in self.user_input_line_ids if input_line.quizz_mark == 2]:
           l2_score += user_input.quizz_mark
        percentage = "{score:.0f}%".format(score=l2_score * 100 / self.survey_id.l2_total_score)
        self.l2_score = "{score} out of {total} points ({percentage})".format(score=int(l2_score), total=self.survey_id.l2_total_score, percentage=percentage)

    
    @api.one
    def get_weighted_average(self):
        average = 0
        l1_weight, l2_weight = [40, 60]
        l1_score, l2_score = [0, 0]

        if self.l1_score == '-':
            l2_weight = 100
        if self.l2_score == '-':
            l1_weight = 100
        
        if self.l1_score != '-':
            percentage = self.l1_score[self.l1_score.find("(")+1:self.l1_score.find("%")]
            l1_score = int(percentage) * l1_weight / 100

        if self.l2_score != '-':
            percentage = self.l2_score[self.l2_score.find("(")+1:self.l2_score.find("%")]
            l2_score = int(percentage) * l2_weight / 100

        self.weighted_average = "{score:.0f}%".format(score=l1_score+l2_score)
        

    survey_interrupted = fields.Boolean('Survey interrupted', default=False, readonly=True)
    participant_name = fields.Char('Participant Name', readonly=False, store=True)
    email_sent = fields.Boolean('Email Sent', default=False, readonly=True)
    event_id = fields.Many2one('event.event', string='Course')
    survey_event_trainer = fields.Many2one(string="Course Trainer", related="event_id.trainer_id", store=False)
    survey_url = fields.Char(string='Survey Url', related='survey_id.public_url', store=False)
    survey_type = fields.Selection(string='Survey Type', related='survey_id.type', store=False)
    max_total_score = fields.Integer(string='Maximum Score achievable', compute='_get_max_score', store=False)
    quizz_score_percentage = fields.Char(string="Score for the quiz", compute='_get_survey_score', store=False)
    email = fields.Char('E-mail', readonly=False)
    l1_score = fields.Char('L1 Score', compute="_get_l1_score")
    l2_score = fields.Char('L2 Score', compute="_get_l2_score")
    weighted_average = fields.Char(string='Weighted Average', compute='get_weighted_average')
    start_exam = fields.Datetime('Exam starting time')
    promoted_condition = fields.Char(string='Status', compute='_get_promoted_condition', required=True)
    attendee_ids = fields.Many2many('event.event', 'survey_user_input_rel', 'event_event_id', 'survey_id', string='Scheduled Trainings')
    participant_ids = fields.Many2many('event.event', 'event_user_input_rel', 'event_event_id', 'survey_id', string='Add to training')
    question_ids = fields.Many2many('survey.question', relation='survey_user_questions', column1='user_input', column2='question_id', string="Questions", readonly=True)

    @api.one
    def _get_promoted_condition(self):
        for note in self:
            if note.quizz_score_percentage in ['1%','2%','3%','4%','5%','6%','7%','8%','9%'] and self.state == 'done':
                self.promoted_condition = ('Failed')
            elif note.quizz_score_percentage >= '70%' and self.state == 'done':
                self.promoted_condition = ('Promoted')
            elif note.quizz_score_percentage == '100%' and self.state == 'done':
                self.promoted_condition = ('Promoted')
            elif note.quizz_score_percentage < '70%' and self.state == 'done':
                self.promoted_condition = ('Failed')
            else:
                self.promoted_condition = ('Not yet started')
        return self.promoted_condition

    @api.model
    def create(self, vals):
        if vals.get('participant_name'):
            vals['participant_name'] = vals.get('participant_name').strip()
        if vals.get('email'):
            vals['email'] = vals.get('email').lower().strip()
        res = super(survey_user_input, self).create(vals)
        question_ids = []
        for page in res.survey_id.page_ids:
            for question in page.question_ids:
                if question.is_active:
                    question_ids.append(question.id)
        res.question_ids = [(6, 0, question_ids)]
        return res

    @api.multi
    def write(self, vals):
        if vals.get('participant_name'):
            vals['participant_name'] = vals.get('participant_name').strip()
        if vals.get('email'):
            vals['email'] = vals.get('email').lower().strip()
        res = super(survey_user_input, self).write(vals)
        return res

    @api.multi
    def action_course_survey_results(self):
        ''' Open the website page with the course survey results '''
        survey_url = self.survey_id.result_url.replace('survey/', '{type}/'.format(type='exam' if self.survey_id.type == 'preliminary' else self.survey_id.type))
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '{url}/{id}'.format(url=survey_url, id=self.event_id.id)
        }


    @api.multi
    def print_results(self):
        print_url = self.print_url.replace('survey/', '{type}/'.format(type='exam' if self.survey_id.type == 'preliminary' else self.survey_id.type))
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '{url}\{token}'.format(url=print_url, token=self.token)
        }

    @api.one
    def email_survey(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if self.token:
            url = self.survey_id.public_url
            survey_type = 'exam' if self.survey_id.type == 'preliminary' else self.survey_id.type
            url = urlparse.urlparse(url).path[1:].replace('survey/', '{type}/'.format(type=survey_type))
            url = '{base_url}/{url}/{token}'.format(base_url=base_url, url=url, token=self.token)
            participant = u''.join(self.participant_name).encode('utf-8').strip()
            if self.survey_id.type == 'exam':
                subject = '{course} Examination'.format(course=self.event_id.name)
                email_body = """
                    Hello {name},<br/><br/>
                    To start the OSINT exam, please click on the link below.<br/><br/>
                    <a href="{url}">{url}</a><br/>
                    {signature}
                """.format(name=participant, url=url, signature=self.event_id.user_id.signature)
            elif self.survey_id.type == 'preliminary':
                subject = 'Preliminary OSINT Exam'
                email_body = """
                    Hello {name},<br/><br/>
                    To start the "Preliminary" OSINT Exam, please click on the link below.<br/><br/>
                    <a href="{url}">{url}</a><br/>
                    {signature}
                """.format(name=participant, url=url, signature=self.env.user.signature)
            else:
                subject = '{course} Feedback'.format(course=self.event_id.name)
                email_body = """
                    Hi {name},<br/><br/>
                    Thank you for your participation on the {course}.<br/><br/>
                    Your feedback would be appreciated.<br/><br/>
                    To start the survey, please click on the link below.<br/><br/>
                    <a href="{url}">{url}</a><br/>
                    {signature}
                """.format(name=participant, course=self.event_id.name, url=url, signature=self.event_id.user_id.signature)
            values = {
                'model': None,
                'res_id': None,
                'subject': subject,
                'body': email_body,
                'body_html': email_body,
                'parent_id': None,
                'attachment_ids': None,
                'email_from': 'training@qwarie.com',
                'reply_to': 'training@qwarie.com',
                'auto_delete': True,
                'email_to': self.email
            }
            mail = self.env['mail.mail'].create(values)
            mail.send()
            self.write({'email_sent': True})
    @api.multi
    def unlink(self):
        return super(survey_user_input, self).unlink()

    @api.one
    @api.onchange('user_input_line_ids')
    def email_survey_again(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if self.token:
            url = self.survey_id.public_url
            survey_type = 'exam' if self.survey_id.type == 'preliminary' else self.survey_id.type
            url = urlparse.urlparse(url).path[1:].replace('survey/', '{type}/'.format(type=survey_type))
            url = '{base_url}/{url}/{token}'.format(base_url=base_url, url=url, token=self.token)
            self.start_exam = False
            #make state Not started yet
            self.state = 'new'
            #unlink last answers
            for find_id in self.user_input_line_ids:
                find_id.unlink()
            if self.survey_id.type == 'exam':
                subject = '{course} Examination'.format(course=self.event_id.name)
                email_body = """
                    Hello {name},<br/><br/>
                    To restart the OSINT exam, please click on the link below.<br/><br/>
                    <a href="{url}">{url}</a><br/>
                    {signature}
                """.format(name=self.participant_name, url=url, signature=self.event_id.user_id.signature)
            elif self.survey_id.type == 'preliminary':
                subject = 'Preliminary OSINT Exam'
                email_body = """
                    Hello {name},<br/><br/>
                    To restart the "Preliminary" OSINT Exam, please click on the link below.<br/><br/>
                    <a href="{url}">{url}</a><br/>
                    {signature}
                """.format(name=self.participant_name, url=url, signature=self.env.user.signature)
            values = {
                'model': None,
                'res_id': None,
                'subject': subject,
                'body': email_body,
                'body_html': email_body,
                'parent_id': None,
                'attachment_ids': None,
                'email_from': 'training@qwarie.com',
                'reply_to': 'training@qwarie.com',
                'auto_delete': True,
                'email_to': self.email
            }
            mail = self.env['mail.mail'].create(values)
            mail.send()
            self.write({'email_sent': True})

#inherit question_mark to change it from float to integer
class survey_user_input_line(models.Model):
    _inherit = 'survey.user_input_line'

    quizz_mark = fields.Float("Score given for this choice", digits=(16,0))

class survey_question(models.Model):
    _inherit = 'survey.question'

    #create survey function
    @api.multi
    @api.model
    def action_create_survey(self):
        survey = self.env['survey.survey'].sudo().create({
                'title': 'NewQwarieSurvey',
                'type': 'preliminary',
                })  
        page = self.env['survey.page'].create({
            'title': 'Page1',
            'survey_id': survey.id      
        })
        for stat in self:
            question = self.env['survey.question'].create({
                'question': stat.question,
                'type': stat.type,
                'page_id': page.id,
            })
            for label in stat.labels_ids:
                self.env['survey.label'].create({
                    'value': label.value,
                    'quizz_mark': label.quizz_mark,
                    'question_id': question.id
                })
        res_id = survey.id
        return res_id

    @api.one
    @api.depends('labels_ids')
    def _get_max_score(self):
        if self.type == 'multiple_choice':
            self.max_score = sum([label['quizz_mark'] or 0 for label in self.labels_ids] or [0])
        else:
            self.max_score = max([label['quizz_mark'] or 0 for label in self.labels_ids] or [0])
    
    #get autonumbering
    @api.one
    @api.model
    def _get_order_number(self):
        list1 = [x.question for x in self.page_id.question_ids]
        i = 1
        while i <= len(list1):
            if self.page_id.question_ids[i-1].question == list1[i-1]:
                self.page_id.question_ids[i-1].order_number = i
                i += 1

    constr_show_ids = fields.Many2many('survey.question.constraints', 'question_constr_rel', 'question_id', 'constraint_id', string='Show Question if')
    max_score = fields.Integer(string='Maximum Score achievable', compute='_get_max_score', store=False)
    is_active = fields.Boolean(string='Is Active', default=True)
    order_number = fields.Integer(string="#", compute='_get_order_number', default='1', store=False)
    question = fields.Char(string='Question Name')

#inherit question_mark to change it from float to integer
class survey_label(models.Model):
    _inherit = 'survey.label'

    quizz_mark = fields.Float('Score for this choice', digits=(16,0), help="A positive score indicates a correct choice; a negative or null score indicates a wrong answer")

class survey_question_constraints(models.Model):
    _name = 'survey.question.constraints'
    _description = 'Survey Question Constraints'

    @api.one
    @api.depends('name')
    def _constraint_name_to_tag(self):
        if self.name:
            self.constr_tag = self.name.lower().replace(' ', '_')

    name = fields.Char(string="Name", required=True)
    constr_tag = fields.Char(string="Constraint Tag", compute='_constraint_name_to_tag', store=True, required=True, readonly=False)
