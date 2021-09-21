from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo.osv import osv
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    project_id = fields.Many2one("project.project", string="Project")

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    @api.depends('hours_quoted_ids.total')
    def _amount_all(self):
        for hour in self:
            hour_total = amount_tax = total_hour = 0.0
            for line in hour.hours_quoted_ids:
                hour_total += line.subtotal
                amount_tax += line.price_tax
                total_hour += line.quoted_hour
            hour.update({
                'hour_total': hour.currency_id.round(hour_total),
                'amount_tax': hour.currency_id.round(amount_tax),
                'amount_total': hour_total + amount_tax,
            })

    @api.depends('hours_quoted_ids.quoted_hour')
    def _total_hours(self):
        for hour in self:
            total_hour = 0.0
            for line in hour.hours_quoted_ids:
                total_hour += line.quoted_hour
            hour.update({
                'total_hour': total_hour,
            })

    @api.depends('timesheet_ids.unit_amount')
    def _compute_billable_hours(self):
        for hour in self:
            billable_hour= spent_hours = 0.0
            for line in hour.timesheet_ids:
                billable_hour += line.unit_amount
                spent_hours += line.time_spent
            hour.update({
                'billable_hour': billable_hour,
                'spent_hours': spent_hours,
            })

    @api.depends('total_hour','billable_hour')
    def _compute_remaining_hours(self):
        for hour in self:
            hour.update({'remaining_hours': hour.total_hour - hour.billable_hour})


    @api.depends('testing_hour_ids.test_hour')
    def _compute_testing_hours(self):
        for hour in self:
            total_test_hours = 0.0
            for line in hour.testing_hour_ids:
                total_test_hours += line.test_hour
            hour.update({
                'total_test_hours': total_test_hours,
            })
            


    quote_id = fields.Char(string="Hours Quoted ID", required=True, default=lambda self: self.env['ir.sequence'].next_by_code('helpdesk.ticket'))
    #hour_quoted = fields.Float(string='Hour Quoted')
    billable_hour = fields.Float(string='Billable hours',  digits=(16, 2), compute='_compute_billable_hours')
    remaining_hours = fields.Float(string='Remaining Hours', compute='_compute_remaining_hours')
    spent_hours = fields.Float(string='Duration', compute='_compute_billable_hours')
    hours_quoted_ids = fields.One2many('hours.quoted', 'helpdesk_ticket_id', string='Hours Quoted')
    hour_total = fields.Monetary(string='Amount', store=True, readonly=True, compute='_amount_all')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, 
        default=lambda self: self.env.user.company_id.currency_id.id)
    total_hour = fields.Float(string='Total Hours', compute='_total_hours', store=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete="set null", copy=False)
    testing_hour_ids = fields.One2many('testing.hours', 'helpdesk_ticket_id', string='Testing Hours')
    total_test_hours = fields.Float(string='Total Testing Hours', compute='_compute_testing_hours')
    approved_by = fields.Many2one('res.users', string='Approved by')

    #not avialble in 14
    '''@api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id.project_id :
            self.project_id = self.partner_id.project_id
        else:
            self.project_id = "" 
        return super(HelpdeskTicket, self)._onchange_partner_id()'''

    @api.depends('partner_id')
    def _compute_partner_info(self):
        if self.partner_id.project_id :
            self.project_id = self.partner_id.project_id
        else:
            self.project_id = ""
        return super(HelpdeskTicket, self)._compute_partner_info()


    @api.model
    def create(self, vals):
        res = super(HelpdeskTicket, self).create(vals)
        name = str(vals['name']) + '#' +str(res.id)      
        res.write({
            'name': name,
        })

        if vals.get('timesheet_ids'):
            for t_ids in self.timesheet_ids:
                if t_ids.unit_amount > t_ids.time_spent:
                    raise UserError(_('Billable time cannot be more than Time Spent'))
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(HelpdeskTicket, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        helpdesk = self.env['helpdesk.ticket']
        for line in res:
            if '__domain' in line:
                helpdesk = self.search(line['__domain'])
            if 'billable_hour' in fields:
                line['billable_hour'] = sum(helpdesk.mapped('billable_hour'))
            if 'remaining_hours' in fields:
                line['remaining_hours'] = sum(helpdesk.mapped('remaining_hours'))
            if 'spent_hours' in fields:
                line['spent_hours'] = sum(helpdesk.mapped('spent_hours'))
        return res

    def write(self, vals):
        res = super(HelpdeskTicket, self).write(vals) 
        
        if vals.get('stage_id') == 27 and self.spent_hours > 1:
            raise UserError(_('Please ask Nicole to check before putting it on hold'))

        if vals.get('timesheet_ids'):
            #_logger.info("XXXXXXXXXXXXXXXXXXXXXXX %s",vals['timesheet_ids'])
            for t_ids in self.timesheet_ids:
                if t_ids.unit_amount > t_ids.time_spent:
                    raise UserError(_('Billable time cannot be more than Time Spent'))
        #_logger.info("VVVVVVVVVVVVVVVVVVVVVVVVV %s",vals)
        #_logger.info(D)
        return res
    '''@api.multi
    def write(self, values):
        result = super(HelpdeskTicket, self).write(values)
        if 'timesheet_ids' in values:
            imd_res = self.env['ir.model.data']
            template_res = self.env['mail.template']
            _, template_id = imd_res.get_object_reference('helpdesk_ticket_v12', 'timesheet_entry1')
            email_context = self.env.context.copy()
            data = {}
            timesheet_ids = []
            data.update({'timesheet_ids' : timesheet_ids })
            for record, item in values.items():
                for i in item:
                    if i[0] == 0 :
                        if i[2]['employee_id']:
                            project = self.env['hr.employee'].browse(i[2]['employee_id'])
                        timesheet_ids.append({
                           'date': i[2]['date'],
                           'employee_id': project.name,
                           'name': i[2]['name'],
                           'time_spent': i[2]['time_spent'],
                           'unit_amount': i[2]['unit_amount'],
                        })
            data.update({'timesheet_ids' : timesheet_ids })
            email_context.update(data)
            template = template_res.browse(template_id)
            template.with_context(email_context).send_mail(self.id)
        return result'''

    @api.model
    def get_email_to(self):
        email_list = []
        user1 = self.env['res.users'].search([])
        for usr in self.message_follower_ids:
            for u in user1:
                if usr.partner_id == u.partner_id:
                    email_list.append(usr.partner_id.email)
        return ",".join(email_list)


class HoursQuoted(models.Model):
    _name = 'hours.quoted'
    _rec_name = "description"

    '''type=fields.Selection([
        ('support', 'Support'),
        ('development', 'Development')], string="Type")'''
    product_id = fields.Many2one('product.product', string='Type', ondelete='restrict', index=True)
    description = fields.Char(string='Description', required=True)
    quoted_hour = fields.Float(string='Hours', default=0.0)
    unit_price = fields.Float(string='Unit Price', related="product_id.lst_price")
    #amount = fields.Float(string='Amount', compute='_compute_amount')
    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket')
    taxes_id = fields.Many2many('account.tax', string='Taxes')
    subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)
    currency_id = fields.Many2one(related='helpdesk_ticket_id.currency_id', store=True, string='Currency', readonly=True)
    free_text = fields.Char(string='Text')

    @api.depends('quoted_hour', 'unit_price', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            vals = line._prepare_compute_all_values()
            taxes = line.taxes_id.compute_all(
                vals['unit_price'],
                vals['currency_id'],
                vals['quoted_hour'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'total': taxes['total_included'],
                'subtotal': taxes['total_excluded'],
            })

    def _prepare_compute_all_values(self):
        self.ensure_one()
        return {
            'unit_price': self.unit_price,
            'currency_id': self.helpdesk_ticket_id.currency_id,
            'quoted_hour': self.quoted_hour,
        }


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    invoice_date = fields.Date(string='Invoice Date', related="invoice_id.invoice_date")
    stage_id = fields.Many2one('helpdesk.stage', string='Stage', ondelete='restrict', track_visibility='onchange',
                               group_expand='_read_group_stage_ids', copy=False,
                               index=True)
                    #, domain="[('team_ids', '=', team_id)]")
    state = fields.Char(related="stage_id.name")
    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', 'Helpdesk Ticket')
    state1 = fields.Many2one(related="helpdesk_ticket_id.stage_id")


class TestingHours(models.Model):
    _name = 'testing.hours'
    _rec_name = "description"


    user_id = fields.Many2one('res.users', string='User')
    description = fields.Char(string='Description', required=True)
    test_hour = fields.Float(string='Hours', default=0.0)
    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Helpdesk Ticket')


