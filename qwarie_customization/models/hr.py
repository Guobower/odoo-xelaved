# -*- coding: utf-8 -*-
from openerp import fields, models, api

class hr_employee(models.Model):
    _inherit = "hr.employee"

    facebook_account = fields.Char(string='Facebook')
    linkedin_account = fields.Char(string='Linkedin')

    def open_contact_page(self):
        user = self.env['res.users'].browse(self.env.uid)
        return {
            'name': 'Dashboard',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'res_id': user.partner_id.id
        }

class res_partner(models.Model):
    _inherit = 'res.partner'

    attachment_ids = fields.Many2many('ir.attachment', 'partner_ir_attachments_rel', 'partner_id', 'attachment_id', 'Attachments')


