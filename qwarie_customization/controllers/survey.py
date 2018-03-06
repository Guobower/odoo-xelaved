# -*- coding: utf-8 -*-
import unicodedata
from openerp import api, fields, SUPERUSER_ID
from openerp.addons.web import http
from openerp.exceptions import UserError
from openerp.addons.web.http import Controller, route, request
from openerp.addons.survey.controllers.main import WebsiteSurvey
from openerp.addons.report.controllers.main import ReportController

import json
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class SurveyControllerExtension(WebsiteSurvey):

    @http.route('/survey/get_user_results', type='json', auth="none", website=True)
    def get_user_results(self, user_token=False):
        if user_token:
            result = {}
            survey = request.env['survey.user_input'].search([('token', '=', user_token)])
            question_obj = request.env['survey.question']
            if survey.event_id:
                result = {
                    'user_id': survey.id,
                    'user_name': survey.participant_name,
                    'user_email': survey.email,
                    'event_name': survey.event_id.name,
                    'event_date_start': fields.Datetime.from_string(survey.event_id.date_begin).strftime('%a, %d %b %Y'),
                    'event_date_end': fields.Datetime.from_string(survey.event_id.date_end).strftime('%a, %d %b %Y'),
                    'event_trainer': survey.event_id.trainer_id.name,
                    'event_assistant': survey.event_id.assistant_id.name or None
                }

            result['total_score'] = survey.quizz_score
            result['max_total_score'] = survey.max_total_score
            result['is_quizz'] = survey.survey_id.quizz_mode
            result['scores'] = {}
            multiple = []
            if (survey.survey_id.type == 'preliminary'):
                result['l1_score'] = survey.l1_score
                result['l2_score'] = survey.l2_score
                result['weighted_average'] = survey.weighted_average
            for user_input in survey.user_input_line_ids:
                question_id = user_input.question_id.id
                x = 0
                if user_input.question_id.type == 'multiple_choice':
                    lalalist = [x.quizz_mark for x in user_input if user_input.quizz_mark > 0 and user_input.question_id.type == 'multiple_choice']
                    multiple += lalalist
                result['scores'][question_id] = {
                    'type': user_input.answer_type,
                    'score': user_input.quizz_mark,
                    'max_score': user_input.question_id.max_score,
                    'answer_type': user_input.question_id.type,
                    'multiple_score': len(multiple)
                }
            return result
        return False

    
    @http.route('/survey/get_user_test_time', type='json', auth="none", website=True)
    def get_user_test_time(self, user_token=False):
        if user_token:
            result = {}
            user_input = request.env['survey.user_input'].search([('token', '=', user_token)])
            result = {
                'start_exam': user_input.start_exam,
                'duration': user_input.survey_id.duration
            }
            return result
        return False    

    @http.route('/survey/set_survey_complete', type='json', auth="none", website=True)
    def set_survey_complete(self, user_token=False):
        if user_token:
            user_input = request.env['survey.user_input'].search([('token', '=', user_token)])
            if user_input:
                user_input.sudo().write({'state': "done"})
                return True
        return False    

    @http.route('/exam', type='http', auth="public", website=True)
    def exam_identification_form(self):
        return request.website.render("survey.exam_identification")


    @http.route('/exam_redirect', type='http', methods=['POST'], auth='public', website=True)
    def exam_redirect(self, **post):
        if not post.get('name') and not post.get('email'):
            return request.website.render("survey.not_found")
        name = post.get('name').lower().strip()
        email = post.get('email').lower().strip()
        survey = request.env['survey.user_input'].sudo().search([
            ('email', '=ilike', email),
            ('survey_id.type', 'in', ['exam', 'preliminary']),
            ('participant_name', '=ilike', name)],
            order="id desc", limit=1)
        if not survey:
            return request.website.render("survey.not_found")
        survey_url = survey.survey_id.public_url + '/' + survey.token
        survey_url = survey_url.replace('survey/', 'exam/')
        return request.redirect(survey_url)

    @http.route('/feedback', type='http', auth="public", website=True)
    def feedback_identification_form(self):
        return request.website.render("survey.feedback_identification")

    @http.route('/feedback_redirect', type='http', methods=['POST'], auth='public', website=True)
    def feedback_redirect(self, **post):
        if not post.get('name') and not post.get('email'):
            return request.website.render("survey.not_found")
        name = post.get('name').lower().strip()
        email = post.get('email').lower().strip()
        survey = request.env['survey.user_input'].sudo().search([
            ('email', '=ilike',email),
            ('survey_id.type', '=', 'feedback'),
            ('participant_name', '=ilike', name)],
            order="id desc", limit=1)
        if not survey:
            return request.website.render("survey.not_found")
        survey_url = survey.survey_id.public_url + '/' + survey.token
        survey_url = survey_url.replace('survey/', 'feedback/')
        return request.redirect(survey_url)

    @http.route('/survey/user_back_pressed', type='json', auth="none", website=True)
    def user_back_pressed(self, user_token=False):
        if user_token:
            survey = request.env['survey.user_input'].search([('token', '=', user_token)])
            if survey:
                survey.sudo().write({'survey_interrupted': True})
                return {'status': 'success'}
            return False
        return False

    @http.route(['/survey/results/<model("survey.survey"):survey>/<model("event.event"):event>'],
                type='http', auth='user', website=True)
    def course_survey_reporting(self, survey, event, token=None, **post):
        '''Display survey Results & Statistics for given survey.'''
        result_template ='survey.result'
        filter_display_data = []
        filter_finish = False
        if survey.type == 'feedback':
            current_filters = [participant.id for participant in event.feedback_survey_participants_ids]
        else:
            current_filters = [participant.id for participant in event.exam_survey_participants_ids]

        return request.website.render(result_template, {
            'survey': survey,
            'survey_dict': self.prepare_result_dict(survey, current_filters),
            'page_range': self.page_range,
            'current_filters': current_filters,
            'filter_display_data': filter_display_data,
            'filter_finish': filter_finish,
            'course_name': event.name or False,
        })

    # Survey displaying
    @http.route()
    def fill_survey(self, survey, token, prev=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        response = super(SurveyControllerExtension, self).fill_survey(survey, token)
        user_input_obj = request.registry['survey.user_input']

        # Load the user_input
        try:
            user_input_id = user_input_obj.search(cr, SUPERUSER_ID, [('token', '=', token)])[0]
        except IndexError:  # Invalid token
            return request.website.render("website.403")
        else:
            user_input = user_input_obj.browse(cr, SUPERUSER_ID, [user_input_id], context=context)[0]

        if user_input.start_exam == False and user_input.state == 'new':
            user_input.write({'start_exam': datetime.now()})
        response.qcontext.update({
            'event_ctu': user_input.event_id.ctu_order or False
        })
        return response

    # Printing routes
    @http.route()
    def print_survey(self, survey, token=None, **post):
        cr, uid, context, event_ctu = request.cr, request.uid, request.context, False
        response = super(SurveyControllerExtension, self).print_survey(survey, token)
        user_input_obj = request.registry['survey.user_input']
        # Load the user_input
        try:
            user_input_id = user_input_obj.search(cr, SUPERUSER_ID, [('token', '=', token)])[0]
        except IndexError:  # Invalid token
            event_ctu = False
        else:
            user_input = user_input_obj.browse(cr, SUPERUSER_ID, [user_input_id], context=context)[0]
            event_ctu = user_input.event_id.ctu_order
        response.qcontext.update({
            'event_ctu': event_ctu
        })
        return response
        
    # AJAX submission of a page
    @http.route()
    def submit(self, survey, **post):
        _logger.debug('Incoming data: %s', post)
        page_id = int(post['page_id'])
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']
        questions_obj = request.registry['survey.question']
        questions_ids = questions_obj.search(cr, uid, [('page_id', '=', page_id)], context=context)
        questions = questions_obj.browse(cr, uid, questions_ids, context=context)

        # Answer validation
        errors = {}
        for question in questions:
            answer_tag = "%s_%s_%s" % (survey.id, page_id, question.id)
            errors.update(questions_obj.validate_question(cr, uid, question, post, answer_tag, context=context))

        ret = {}
        if (len(errors) != 0):
            # Return errors messages to webpage
            ret['errors'] = errors
        else:
            # Store answers into database
            user_input_obj = request.registry['survey.user_input']

            user_input_line_obj = request.registry['survey.user_input_line']
            try:
                user_input_id = user_input_obj.search(cr, SUPERUSER_ID, [('token', '=', post['token'])], context=context)[0]
            except KeyError:  # Invalid token
                return request.website.render("website.403")
            user_input = user_input_obj.browse(cr, SUPERUSER_ID, user_input_id, context=context)
            user_id = uid if user_input.type != 'link' else SUPERUSER_ID
            for question in questions:
                answer_tag = "%s_%s_%s" % (survey.id, page_id, question.id)
                user_input_line_obj.save_lines(cr, user_id, user_input_id, question, post, answer_tag, context=context)

            go_back = post['button_submit'] == 'previous'
            next_page, _, last = survey_obj.next_page(cr, uid, user_input, page_id, go_back=go_back, context=context)
            vals = {'last_displayed_page_id': page_id}
            if next_page is None and not go_back:
                vals.update({'state': 'done'})
            elif user_input.state != 'done':
                vals.update({'state': 'skip'})
            user_input_obj.write(cr, user_id, user_input_id, vals, context=context)
            ret['redirect'] = '/survey/fill/%s/%s' % (survey.id, post['token'])
            if survey.type in ['exam', 'feedback', 'preliminary']:
                ret['redirect'] = ret['redirect'].replace('survey', 'exam' if survey.type == 'preliminary' else survey.type)
            if go_back:
                ret['redirect'] += '/prev'
        return json.dumps(ret)


    ### Routes for exam and feedback ###
    # Survey start
    @http.route(['/exam/start/<model("survey.survey"):survey>',
                 '/exam/start/<model("survey.survey"):survey>/<string:token>',
                 '/feedback/start/<model("survey.survey"):survey>',
                 '/feedback/start/<model("survey.survey"):survey>/<string:token>'],
                type='http', auth='public', website=True)
    def qw_start_survey(self, survey, token=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        response = super(SurveyControllerExtension, self).start_survey(survey, token)
        user_input_obj = request.registry['survey.user_input']
        try:
            user_input_id = user_input_obj.search(cr, SUPERUSER_ID, [('token', '=', token)], context=context)[0]
        except IndexError:  # Invalid token
            return request.website.render("website.403")
        else:
            user_input = user_input_obj.browse(cr, SUPERUSER_ID, [user_input_id], context=context)[0]
        if user_input.state == 'new':
            return response
        return request.redirect('/%s/fill/%s/%s' % ('exam' if survey.type =='preliminary' else survey.type, survey.id, user_input.token))

    # Survey displaying
    @http.route(['/exam/fill/<model("survey.survey"):survey>/<string:token>',
                 '/exam/fill/<model("survey.survey"):survey>/<string:token>/<string:prev>',
                 '/feedback/fill/<model("survey.survey"):survey>/<string:token>',
                 '/feedback/fill/<model("survey.survey"):survey>/<string:token>/<string:prev>'],
                type='http', auth='public', website=True)
    def qw_fill_survey(self, survey, token, prev=None, **post):
        return self.fill_survey(survey, token)

    # Printing routes
    @http.route(['/exam/print/<model("survey.survey"):survey>',
                 '/exam/print/<model("survey.survey"):survey>/<string:token>',
                 '/feedback/print/<model("survey.survey"):survey>',
                 '/feedback/print/<model("survey.survey"):survey>/<string:token>'],
                type='http', auth='public', website=True)
    def qw_print_survey(self, survey, token=None, **post):
        return super(SurveyControllerExtension, self).print_survey(survey, token)

    # Results reporting routes
    @http.route(['/exam/results/<model("survey.survey"):survey>',
                 '/feedback/results/<model("survey.survey"):survey>'],
                type='http', auth='user', website=True)
    def qw_survey_reporting(self, survey, token=None, **post):
        return super(SurveyControllerExtension, self).survey_reporting(survey, token)
    
class CertificateController(http.Controller):    
    #------------------------------------------------------
    # Certificate controllers
    #------------------------------------------------------
    @route([
        '/report/certificate/<path:converter>/<reportname>',
        '/report/certificate/<path:converter>/<reportname>/<docids>',
    ], type='http', auth='public', website=True)
    def certificate_routes(self, reportname, docids=None, converter=None, **data):
        certificate_obj = request.registry['report']
        cr, uid, context = request.cr, request.uid, request.context

        if docids:
            docids =[int(i) for i in docids.split(',')]
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            data['context'] = json.loads(data['context'])
            if data['context'].get('lang'):
                del data['context']['lang']
            context.update(data['context'])

        if converter =='html':
            html = certificate_obj.get_html(cr, uid, docids, reportname, data=data, context=context)
            return request.make_response(html)
        elif converter == 'pdf':
            pdf = certificate_obj.get_pdf(cr, uid, docids, reportname, data=data, context=context)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        elif converter == 'download':
            pdf = certificate_obj.get_pdf(cr, uid, docids, reportname, data=data, context=context)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            raise exceptions.HTTPException(description='Converter %s not implemented.' %converter)
    
class ReportController(ReportController):
    
    @route(['/report/download'])
    def report_download(self, data, token):
        response = super(ReportController, self).report_download(data, token)
        file_download_name = request.env['ir.attachment'].search([])[0].name
        # raise UserError(survey)
        response.headers.set('Content-Disposition', 'attachment; filename=%s;' % file_download_name)
        return response