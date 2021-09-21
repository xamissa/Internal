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

import time

from odoo import api, models, tools,fields, _

import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class Invoiceline(models.Model):
    _inherit = 'account.move.line'
    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', 'Helpdesk Ticket')

class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    invoice_id = fields.Many2one(
        'account.move', string='Invoice', ondelete="set null", copy=False)
    time_spent = fields.Float(string='Time Spent',  digits=(16, 2))
    total_value = fields.Float(string='Total Value',  digits=(16, 2))

    def write(self, vals):
        self._check_inv(vals)
        return super(AccountAnalyticLine, self).write(vals)

    def _check_inv(self, vals):
        print(vals)
        if 'invoice_id' not in vals or vals['invoice_id'] is False :
            for line in self:
                if line.invoice_id and  line.total_value!=0.0:
                    raise UserError(_(
                        'You cannot modify an invoiced analytic line!'))
        return True


    def _get_invoice_price(self, account, product_id, user_id, qty):
        product = self.env['product.product'].browse(product_id)
        pricelist = self.project_id.partner_id.property_product_pricelist and \
                self.project_id.partner_id.property_product_pricelist.id or False
        if pricelist:

           price = pro_price_obj.price_get(
                product_id, qty or 1.0, account.partner_id.id)[pricelist.id]
        else:
           price=product.lst_price
        return price

    def _prepare_cost_invoice(
            self, partner, company_id, currency_id, analytic_lines):
        """ returns values used to create main invoice from analytic lines"""
        account_payment_term_obj = self.env['account.payment.term']
        invoice_name = analytic_lines[0].account_id.name
        account_id = partner.property_account_receivable_id

        date_due = False
        if partner.property_payment_term_id:
            for pt in account_payment_term_obj:
                pterm_list = pt.compute(
                    value=1, date_ref=fields.Date.context_today(self),currency=currency_id)
                if pterm_list:
                    pterm_list = [line[0] for line in pterm_list]
                    pterm_list.sort()
                    date_due = pterm_list[-1]

        vals = {
            #'name': "%s - %s" % (time.strftime('%d/%m/%Y'), invoice_name),
            'name': "/",
            'partner_id': partner.id,
            'company_id': company_id,
            #'payment_term_id': partner.property_payment_term_id.id or False,
            'invoice_payment_term_id' : partner.property_payment_term_id.id or False,
            #'account_id': account_id and account_id.id or False,account_id is not availble on account.move
            'currency_id': currency_id,
            #'date_due': date_due,
            'invoice_date_due': date_due,
            'fiscal_position_id': partner.property_account_position_id.id,
            #'move_type': 'out_invoice'
        }
        _logger.info("^^^^^^^^^^^^^^_prepare_cost_invoice^^^^^^^^^^^^^^^^ %s",vals)
        return vals

    def _prepare_cost_invoice_line(
            self, invoice_id, product_id, uom, user_id, account,
            analytic_lines, journal_type, data):
        product_obj = self.env['product.product']

        total_price = sum(l.amount for l in analytic_lines)
        total_qty = sum(l.unit_amount for l in analytic_lines)

        if data.get('product'):
            # force product, use its public price
            if isinstance(data['product'], (tuple, list)):
                product_id = data['product'][0]
            else:
                product_id = data['product']
            unit_price = self.with_context({'uom': uom})._get_invoice_price(
                account, product_id, user_id, total_qty)
        elif journal_type == 'general' and product_id:
            # timesheets, use sale price
            unit_price = self.with_context({'uom': uom})._get_invoice_price(
                account, product_id, user_id, total_qty)
        else:
            # expenses, using price from amount field
            unit_price = total_price * -1.0 / total_qty

        curr_invoice_line = {
            'price_unit': unit_price,
            'quantity': total_qty,
            'product_id': product_id,
            'move_id': invoice_id.id,
            'product_uom_id': uom,
            'analytic_account_id': account.id,
            'account_id': account.id,
        }
        #_logger.info("###########curr_invoice_line############# %s",curr_invoice_line)
        if product_id:
            product = product_obj.browse(product_id)
            factor_name = product.name_get()[0][1]
            general_account = product.property_account_income_id or \
                product.categ_id.property_account_income_categ_id
            if not general_account:
                raise UserError(_(
                    "Please define income account for \
                    product '%s'.") % product.name)
            taxes = product.taxes_id or general_account.tax_ids
            tax = invoice_id.partner_id.property_account_position_id.map_tax(
                taxes)
            curr_invoice_line.update({
                'tax_ids': [(6, 0, tax.ids)],
                'name': factor_name,
                'account_id': general_account.id,
                
            })
            _logger.info("!!!!!!!!!!!!!!!!!!!!!!!!!curr_invoice_line!!!!!!!!!!!!!!!!!!!! %s",curr_invoice_line)
            note = []
            for line in analytic_lines:
                # set invoice_line_note
                details = []
                if data.get('date', False):
                    details.append(str(line['date']))
                if data.get('time', False):
                    if line['product_uom_id']:
                        details.append("%s %s" % (
                            line.time_spent, line.product_uom_id.name))
                    else:
                        details.append("%s" % (line['time_spent'], ))
                if data.get('name', False):
                    details.append(line['name'])
                if details:
                    note.append(
                        u' - '.join(map(lambda x: x or '', details)))
            if note:
                curr_invoice_line['name'] += "\n" + \
                    ("\n".join(map(lambda x: x or '', note)))
        return curr_invoice_line

    def invoice_cost_create(self, invoice_line_ids, data):
        invoice_obj = self.env['account.move']
        invoice_line_obj = self.env['account.move.line']
        analytic_line_obj = self.env['account.analytic.line']
        invoices = []

        # use key (partner/account, company, currency)
        # creates one invoice per key
        invoice_grouping = {}
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        currency_id = False
        # prepare for iteration on journal and accounts
        for line in self.browse(invoice_line_ids):

            key = (line.account_id.id,
                   line.account_id.company_id.id,
                   line.account_id.currency_id.id)
            invoice_grouping.setdefault(key, []).append(line)

        for (key_id, company_id, currency_id), analytic_lines in \
                invoice_grouping.items():
            # key_id is an account.analytic.account
            account = analytic_lines[0].account_id
            partner = analytic_lines[0].project_id.partner_id# will be the same for every line
            _logger.info("PPPPPPPPPPPPPPPPppp-------------------- %s",partner)
            if (not partner) or not (currency_id):
                raise UserError(_('Complete. \
                    Please fill in the Customer  \
                    fields for %s.') % (account.name))

            curr_invoice = self._prepare_cost_invoice(
                partner, company_id, currency_id, analytic_lines)

            invoice_context = {
                'lang': partner.lang,
                # set force_company in context so the \
                # correct product properties are selected \
                # (eg. income account)
                #'force_company': company_id, force_company is not available 

                'company_id': company_id,
                # set company_id in context,
                # so the correct default journal
                # will be selected
            }

            last_invoice = invoice_obj.with_context(
                invoice_context).create(curr_invoice)
            _logger.info("=================last_invoice=========== %s=======%s",last_invoice,last_invoice.partner_id)
            last_invoice._move_autocomplete_invoice_lines_values()
            invoices.append(last_invoice.id)

            # use key (product, uom, user, invoiceable, analytic account,
            # journal type)
            # creates one invoice line per key
            invoice_lines_grouping = {}
            for analytic_line in analytic_lines:
                account = analytic_line.account_id
                product_id=analytic_line.product_id.id
                uom= analytic_line.product_uom_id.id
                user_id= analytic_line.user_id.id
                account= analytic_line.account_id
                journal_type=journal.type

                # We want to retrieve the data in the partner language
                # for the invoice creation

                analytic_line = analytic_line_obj.browse([
                    line.id for line in analytic_line
                ])

                if not product_id:
                    support_product_id = self.product_id.search([
                        ('name', 'ilike', 'Support')
                    ])
                    if support_product_id and not uom:
                        uom = support_product_id.uom_id.id or False
                        product_id = support_product_id.id
                curr_invoice_line = self._prepare_cost_invoice_line(
                    last_invoice, product_id, uom, user_id, 
                    account, analytic_line, journal_type, data)
                #_logger.info("CCCCCCCCCCCCCCCCC----------------- %s",curr_invoice_line)
                invoice_line=invoice_line_obj.create(curr_invoice_line)
                #_logger.info("IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII %s",invoice_line)
                last_invoice.update({'invoice_line_ids': invoice_line})
                _logger.info("^^^^^^^^^^^^^^^^^^^^^^^^^^^^LLLLLLLLLLLLLLLLLLLLLLLLL %s",last_invoice.invoice_line_ids)

                if analytic_line and analytic_line.helpdesk_ticket_id:
                    invoice_line.write({'helpdesk_ticket_id':analytic_line.helpdesk_ticket_id.id})
                if invoice_line:
                   analytic_line.write({'total_value': invoice_line.price_subtotal,'invoice_id': last_invoice.id})
                #_logger.info("++++++++++++++++++++invoice_line==================%s",invoice_line)


            for line in analytic_lines:
                line.write({'invoice_id': last_invoice.id})
            #last_invoice.write({'helpdesk_ticket_id':line.helpdesk_ticket_id.id})
            #last_invoice.compute_taxes()
            last_invoice._compute_invoice_taxes_by_group()
            _logger.info("@@@@@@@@@@@@@@invoicesssss@@@@@@@@@@@@@@@@@@ %s",invoices)
        return invoices
        #return last_invoice



