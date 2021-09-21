from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    quote_note = fields.Text(string="Quotation Note")
