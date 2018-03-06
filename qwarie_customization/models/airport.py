# -*- coding: utf-8 -*-
from openerp import fields, models

class Airport(models.Model):
    _name = 'airport.airport'
    _description = 'Airport'

    icao_code = fields.Char('ICAO Code', required=True,
            help='International Civil Aviation Organization airport code, used by air traffic control and airline operations such as flight planning.')
    type = fields.Selection([
                ('small_airport', 'Small Airport'),
                ('medium_airport', 'Medium Airprot'),
                ('large_airport', 'Large Airport')
            ], string='Airport Type', required=True)
    name = fields.Char('Name', required=True)
    continent = fields.Char('Continent', required=True)
    iso_country = fields.Char('Country ISO', required=True, help='ISO 3166-1 alpha-2 code - Country code')
    iso_region = fields.Char('Region ISO', required=True, help='ISO 3166-2 alpha-2 code - Country subdivision code')
    municipality = fields.Char('Municipality')
    gps_code = fields.Char('GPS Code')
    iata_code = fields.Char('IATA Code', help='International Air Transport Association location identifier')
