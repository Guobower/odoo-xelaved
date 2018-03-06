# -*- coding: utf-8 -*-
from openerp import fields, models, api
from collections import OrderedDict
from openerp.exceptions import UserError
import json


class Inventory(models.Model):
    _name = 'inventory.inventory'
    _description = 'Inventory'
    _inherit = ['mail.thread']
    _order = 'name asc'

    @api.one
    def get_quantity(self):
        self.quantity = len(self.stock_ids or [])

    @api.one
    @api.depends('stock_ids', 'subitems_ids')
    def get_item_value(self):
        if self.subitems_ids:
            self.value = sum([item.value for item in self.subitems_ids])
        if self.stock_ids:
            self.value += sum([item.value for item in self.stock_ids])

    name = fields.Char(string='Name', required=True)
    quantity = fields.Integer(string='Quantity', readonly=True, compute='get_quantity')
    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes')
    stock_ids = fields.One2many('inventory.stock', 'inventory_id', string='Stock')
    subitems_ids = fields.One2many('inventory.subitem', 'inventory_id', string='Subitems', readonly=True)
    value = fields.Float(string='Value', digits=(16,2), compute='get_item_value')
    currency_id = fields.Many2one('res.currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)


class InvetorySubitem(models.Model):
    _name = 'inventory.subitem'
    _description = 'Inventory Subitem'
    _order = 'name asc'

    @api.one
    @api.depends('item_id')
    def get_item_name(self):
        self.name = self.item_id.name

    @api.one
    @api.depends('serial_ids')
    def get_total_items(self):
        self.quantity = len(self.serial_ids)

    @api.one
    @api.depends('serial_ids')
    def get_values(self):
        values = ''
        for serial in self.serial_ids:
            value = serial.name
            if len(values) > 0:
                value = "\n{value}".format(value=value)
            values += value
        self.serial_ids_values = values

    @api.one
    @api.depends('serial_ids')
    def get_item_value(self):
        self.value = sum([item.value for item in self.serial_ids])

    name = fields.Char(string='Item', related='item_id.name', store=True)
    quantity = fields.Integer(string='Quantity', compute='get_total_items')
    serial_ids = fields.One2many('inventory.stock', 'subitem_id')
    serial_ids_values = fields.Char(compute='get_values', readonly=True, string='Serial Numbers')
    inventory_id = fields.Many2one('inventory.inventory', string='Inventory_id', ondelete='cascade', required=True)
    item_id = fields.Many2one('inventory.inventory', string='Type', ondelete='cascade', required=True)
    value = fields.Float(string='Value', digits=(16,2), compute='get_item_value')
    currency_id = fields.Many2one('res.currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)


class IventoryStock(models.Model):
    _name = 'inventory.stock'
    _description = 'Stock'

    @api.one
    @api.depends('attribute_line_ids')
    def get_values(self):
        values = ''
        for attribute in self.attribute_line_ids:
            value = "{attribute}: {value}".format(attribute=attribute.attribute_id.name, value=(attribute.value or '').encode('utf-8'))
            if len(values) > 0:
                value = "\n{value}".format(value=value)
            values += value
        self.value_ids = values

    @api.one
    @api.depends('stock_subitems_ids')
    def get_components_values(self):
        values = ''
        for component in self.stock_subitems_ids:
            value = "{component} (SN: {serial_number})".format(component=component.item_name, serial_number=component.name)
            if len(values) > 0:
                value = "\n{value}".format(value=value)
            values += value
        self.stock_subitems_ids_values = values

    @api.one
    @api.depends('stock_subitems_ids')
    def get_subitems_value(self):
        self.stock_subitems_value = sum([item.value for item in self.stock_subitems_ids])

    name = fields.Char(string='Serial Number', required=True)
    item_name = fields.Char(string="Item", related="inventory_id.name", required=True)
    inventory_id = fields.Many2one('inventory.inventory', string='Inventory', ondelete='cascade')
    parent_id = fields.Many2one('inventory.inventory', string='Distribution')
    parent_stock_id = fields.Many2one('inventory.stock', string='Stock Distribution')
    stock_subitems_ids = fields.One2many('inventory.stock', 'parent_stock_id', string='Stock Components', readonly=True)
    stock_subitems_ids_values = fields.Char(compute='get_components_values', readonly=True, string='Components')
    stock_subitems_value = fields.Float(string='Components Value', digits=(16,2), compute=get_subitems_value, readonly=True)
    attribute_line_ids = fields.One2many('inventory.stock.attribute.line', 'stock_id')
    value_ids = fields.Char(compute='get_values', readonly=True, string="Attributes")
    subitem_id = fields.Many2one('inventory.subitem', string='Component')
    value = fields.Float(string='Item Value', digits=(16,2))
    currency_id = fields.Many2one('res.currency', readonly=True, default=lambda self: self.env.user.company_id.currency_id)

    @api.model
    def create(self, vals):
        res = super(IventoryStock, self).create(vals)
        if res.parent_id:
            subitem_obj = self.env['inventory.subitem']
            subitem = subitem_obj.search([('inventory_id', '=', res.parent_id.id), ('item_id', '=', res.inventory_id.id)])
            if subitem:
                res.update({'subitem_id': subitem.id})
            else:
                vals = {
                    'item_id': res.inventory_id.id,
                    'inventory_id': res.parent_id.id
                }
                new_subitem = subitem_obj.create(vals)
                res.update({'subitem_id': new_subitem.id})

        return res

    @api.multi
    def write(self, vals):
        old_dist = self.subitem_id
        res = super(IventoryStock, self).write(vals)
        if 'parent_id' in vals:
            subitem_obj = self.env['inventory.subitem']
            subitem = subitem_obj.search([('inventory_id', '=', self.parent_id.id), ('item_id', '=', self.inventory_id.id)])
            if subitem:
                self.subitem_id = subitem.id
            else:
                vals = {
                    'item_id': self.inventory_id.id,
                    'inventory_id': self.parent_id.id
                }
                new_subitem = subitem_obj.create(vals)
                self.subitem_id = new_subitem.id
            oldSubitem = subitem_obj.search([('id', '=', old_dist.id)])
            if oldSubitem and len(oldSubitem.serial_ids) == 0:
                oldSubitem.unlink()
        return res


class InventoryStockAttributeLine(models.Model):
    _name = 'inventory.stock.attribute.line'
    _description = 'Inventory Stock Attributes'
    _order = 'name asc'

    name = fields.Char(string='Name', related='attribute_id.name', store=True)
    stock_id = fields.Many2one('inventory.stock', string='Stock', ondelete='cascade')
    attribute_id = fields.Many2one('inventory.stock.attribute', string='Attribute', required=True)
    value = fields.Char(string='Attribute Value', required=True)


class InventoryStockAttribute(models.Model):
    _name = 'inventory.stock.attribute'
    _description = 'Inventory Stock Attribute'
    _order = 'name asc'

    name = fields.Char(string='Name', required=True)
    attribute_line_ids = fields.One2many('inventory.stock.attribute.line', 'attribute_id', string='Attribute Line')
