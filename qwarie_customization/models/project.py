# -*- coding: utf-8 -*-
from openerp import fields, models, api, osv
from openerp import SUPERUSER_ID
from datetime import datetime, date
import json
from openerp.exceptions import UserError


class task(models.Model):
    _inherit = 'project.task'

    planned_hours = fields.Selection([(2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10)], 'Planned Hours', required=False, dafault=2)

    @api.one
    def _get_company_currency(self):
        if self.company_id:
            self.currency_id = self.sudo().company_id.currency_id
        else:
            self.currency_id = self.env.user.company_id.currency_id

    estimated_price = fields.Monetary(string='Estimated Cost', store=True,
                                      readonly=True, compute='_compute_amount', track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id, compute='_get_company_currency')
    date_deadline = fields.Date('Deadline', select=True, copy=False, track_visibility='onchange')

    _defaults = {
        'stage_id': 4,
        'planned_hours': 2,
        'user_id': lambda self, cr, uid, ctx=None: False,
    }


    @api.onchange('planned_hours', 'date_deadline')
    def change_estimate(self):
        rate = 60
        if self.date_deadline:
            d1 = datetime.strptime(fields.Date.today(), "%Y-%m-%d")
            d2 = datetime.strptime(self.date_deadline, "%Y-%m-%d")
            nr_days = abs((d2 - d1).days)
            if nr_days <= 3:
                rate = 100
        self.estimated_price = self.planned_hours * rate

    @api.one
    @api.depends('date_deadline', 'planned_hours')
    def _compute_amount(self):
        rate = 60
        if self.date_deadline:
            d1 = datetime.strptime(fields.Date.today(), "%Y-%m-%d")
            d2 = datetime.strptime(self.date_deadline, "%Y-%m-%d")
            nr_days = abs((d2 - d1).days)
            if nr_days <= 3:
                rate = 100
        self.estimated_price = self.planned_hours * rate

    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        if 'kanban_state' in init_values and record.kanban_state == 'blocked':
            return 'project.mt_task_blocked'
        elif 'kanban_state' in init_values and record.kanban_state == 'done':
            return 'project.mt_task_ready'
        elif 'user_id' in init_values and record.user_id:  # assigned -> new
            return 'project.mt_task_new'
        elif 'stage_id' in init_values and record.stage_id and record.stage_id.sequence <= 1:  # start stage -> new
            return 'project.mt_task_new'
        elif 'date_deadline' in init_values and record.date_deadline:
            return 'qwarie_customization.mt_task_change'
        elif 'estimated_price' in init_values and record.estimated_price:
            return 'qwarie_customization.mt_task_change'
        elif 'stage_id' in init_values:
            return 'project.mt_task_stage'
        return super(task, self)._track_subtype(cr, uid, ids, init_values, context=context)

    def open_default_project(self, cr, uid, ids=None, context=None):
        user_id = self.pool['res.users'].browse(cr, uid, uid).partner_id.id
        view_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'project.view_task_search_form')
        project_id = self.pool['project.project'].search(cr, uid, [('state', '=', 'open'), ['responsible_id', '=', user_id]], limit=1, order='create_date desc')

        return {
            'name': 'Investigations',
            'view_mode': 'kanban,tree,form,calendar,pivot,graph',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'search_view_id': view_id,
            'context': {
                'search_default_project_id': [project_id],
                'default_project_id': project_id,
            }
        }

class project(models.Model):
    _inherit = "project.project"

    def _get_default_customer(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.parent_id.id or self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
        return company_id

    _defaults = {
        'user_id': lambda self, cr, uid, ctx=None: False,
        'privacy_visibility': 'portal',
        'partner_id': _get_default_customer,
        'state': 'draft',
    }
    responsible_id = fields.Many2one('res.partner', string='Responsible', change_default=True,
        required=False, readonly=False, track_visibility='always')
    task_ids = fields.One2many('project.task', 'project_id', 'Task', readonly=False,
            states={'draft': [('readonly', True)], 'cancelled': [('readonly', True)]})

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        # Prevent double project creation when 'use_tasks' is checked + alias management
        create_context = dict(context, project_creation_in_progress=True,
                              alias_model_name=vals.get('alias_model', 'project.task'),
                              alias_parent_model_name=self._name,
                              mail_create_nosubscribe=False)

        ir_values = self.pool.get('ir.values').get_default(cr, uid, 'project.config.settings', 'generate_project_alias')
        if ir_values:
            vals['alias_name'] = vals.get('alias_name') or vals.get('name')
        project_id = super(project, self).create(cr, uid, vals, context=create_context)
        project_rec = self.browse(cr, uid, project_id, context=context)
        values = {'alias_parent_thread_id': project_id, 'alias_defaults': {'project_id': project_id}}

        # Subscribe customer managers
        group_id = self.pool.get('res.groups').search(cr, SUPERUSER_ID, [('name', '=', 'Customer Manager')], context=context)
        if vals.get('partner_id') or project_rec.partner_id.id:
            partner_ids = self.pool.get('res.partner').search(cr, SUPERUSER_ID, [('parent_id', '=', vals.get('partner_id') or project_rec.partner_id.id), ('user_ids.groups_id', 'in', group_id)], context=context)
            self.message_subscribe(cr, uid, project_id, partner_ids, context=context)
        # Subscribe customer responsible
        if project_rec.responsible_id.id:
            self.message_subscribe(cr, uid, project_id, [project_rec.responsible_id.id, ], context=context)
        # Subscribe Project Managers
        group_id = self.pool.get('res.groups').search(cr, SUPERUSER_ID, [('name', '=', 'Manager'), ('category_id.name', '=', 'Project')], context=context)
        user_ids = self.pool.get('res.partner').search(cr, SUPERUSER_ID, [('user_ids.groups_id', 'in', group_id)], context=context)
        self.message_subscribe(cr, uid, project_id, user_ids, context=context)
        self.pool.get('mail.alias').write(cr, uid, [project_rec.alias_id.id], values, context=context)
        self.write(cr, uid, project_id, {'state': 'open'}, context=context)
        return project_id
