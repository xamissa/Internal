# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from odoo import api, models, tools,fields,_
from odoo.tools.float_utils import float_round 

import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class HRTimesheetInvoiceCreate(models.TransientModel):
    _name = 'helpdesk.ticket.invoice.create'
    _description = 'Create invoice from timesheet'

    date = fields.Boolean(
        string='Date', default=True,
        help='The real date of each work will be displayed on the invoice')
    time = fields.Boolean(
        string='Time spent',
        help='The time of each work done will be displayed on the invoice')
    name = fields.Boolean(
        string='Description', default=True,
        help='The detail of each work done will be displayed on the invoice')
    price = fields.Boolean(
        string='Cost',
        help='The cost of each work done will be displayed on the invoice. \
        You probably don\'t want to check this')
    product = fields.Many2one(
        'product.product', string='Force Product', required=True, domain=[('type', '=', 'service')],
        help='Fill this field only if you want to force to use a \
        specific product. Keep empty to use the real product that comes \
        from the cost.')

    @api.model
    def view_init(self, fields):
        """
            This function checks for precondition before wizard executes
            @param self: The object pointer
            @param fields: List of fields for default value
        """
        context = self.env.context
        data = context and context.get('active_ids', [])
        for ticket in self.env['helpdesk.ticket'].browse(data):
            if ticket.invoice_id:
                raise UserError(_(
                    "Invoice is already linked to some of the \
                    analytic line(s)!"))
       

    def do_create(self):
        self.ensure_one()
        data = self.read()[0]
        context = self.env.context
        line_obj = self.env['account.analytic.line']
        helpdesk_obj = self.env['helpdesk.ticket'].browse(context['active_ids'])
        active_ids = context['active_ids']
        for ticket in helpdesk_obj:
            #ticket1 = self.env['helpdesk.ticket'].search(['&',('id','in',active_ids),('partner_id','=',ticket.partner_id.id)])
            ticket_ids = self.env['helpdesk.ticket'].search([('id','in',active_ids)])
            line_id=[]
            #_logger.info("======================im he %s",ticket_ids)
            for t1 in ticket_ids:
                #_logger.info("===========================%s====%s",t1,t1.timesheet_ids.ids)
                if t1.timesheet_ids.ids:
                    if t1.partner_id == ticket.partner_id :
                        active_ids.remove(t1.id)
                        for a in t1.timesheet_ids.ids:
                            line_id.append(a)
                            #_logger.info("====================if===== %s",line_id)
                    else:
                        active_ids.remove(t1.id)
                        for a in t1.timesheet_ids.ids:
                            #_logger.info("====================else=== %s",line_id)
                            line_id.append(a)
                else:
                    raise UserError(_("Here is no Timesheet lines for '%s'! \n Please Fill the line first.") % t1.partner_id.name)

            _logger.info("=--line_id--%s---ticket_id----%s--------%s",line_id,ticket,ticket.timesheet_ids)
            if not line_id and len(active_ids)==1:
                line_id=ticket.timesheet_ids.ids
            if line_id:
                invs = line_obj.invoice_cost_create(line_id, data)
                _logger.info("#################iiiiiiiiiiiiii %s------",invs)
                helpdesk_obj.write({'invoice_id' : invs[0]})
                act_win = self.env.ref('account.action_move_out_invoice_type').read()[0]
                act_win['domain'] = [('id', 'in', invs), ('move_type', '=', 'out_invoice')]
                act_win['name'] = _('Invoices')
                line_id=[]
                #return act_win
                invoice_obj = self.env.ref('account.view_move_form')
                return {'name': _("Invoices"),
                    'view_mode': 'form',
                    'res_model': 'account.move',
                    'view_id': invoice_obj.id,
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'current',
                    'res_id': invs[0],
                    'domain': ('move_type', '=', 'out_invoice'),
                    'context': {}}
            else:
                raise UserError(_("Here is no Timesheet lines! \n Please Fill the line first."))

       
