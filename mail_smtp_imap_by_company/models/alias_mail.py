# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2016-Today Geminate Consultancy Services (<http://geminatecs.com>).
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
import re
from odoo.exceptions import ValidationError
from odoo.tools import remove_accents
from odoo import _, api, exceptions, fields, models, tools

class AliasMail(models.Model):
    _name = 'alias.mail'
    _rec_name = 'domain_name'
    
    domain_name = fields.Char(string="Domain Name")
    company_id = fields.Many2one('res.company', string="Company")

class Alias(models.Model):
    _inherit = "mail.alias"
    
    def _custom_default_alias_domain(self):
        current_user = self.env['res.users'].browse(self._context.get('uid') or self._uid or self.env.user.id)
        alias = self.env["alias.mail"].sudo().search([('company_id','=',current_user.company_id.id)],limit=1)
        return alias
    
    alias_domain = fields.Many2one('alias.mail',default=lambda self:self._custom_default_alias_domain())
#     name = fields.Char(store=True)
    
    _sql_constraints = [
        ('alias_unique', 'Check(1=1)', 'Unfortunately this email alias is already used, please choose a unique one')
    ]
    
    @api.model
    def _clean_and_make_unique(self, name, alias_ids=False):
        # when an alias name appears to already be an email, we keep the local part only
        name = remove_accents(name).lower().split('@')[0]
        name = re.sub(r'[^\w+.]+', '-', name)
        return name
    
    def name_get(self):
        """Return the mail alias display alias_name, including the implicit
           mail catchall domain if exists from config otherwise "New Alias".
           e.g. `jobs@mail.odoo.com` or `jobs` or 'New Alias'
        """
        res = []
        for record in self:
            if record.alias_name and record.alias_domain:
                res.append((record['id'], "%s@%s" % (record.alias_name, record.alias_domain.domain_name)))
            elif record.alias_name:
                res.append((record['id'], "%s" % (record.alias_name)))
            else:
                res.append((record['id'], _("Inactive Alias")))
        return res

class AccountJournal(models.Model):
    _inherit = "account.journal"
    
    alias_domain = fields.Many2one('alias.mail',related='alias_id.alias_domain')
    
    @api.model
    def create(self, vals):
        res = super(AccountJournal, self).create(vals)
        if 'alias_domain' in vals:
            if vals.get('alias_domain'):
                res.alias_id.sudo().write({'alias_domain':vals.get('alias_domain')})
                del(vals['alias_domain'])
            else:
                alias = self.env["alias.mail"].sudo().search([('company_id','=',self.env.user.company_id.id)],limit=1)
                if alias:
                    res.alias_id.sudo().write({'alias_domain':alias.id})
        return res
    
    def write(self, vals):
        for journal in self:
            if 'alias_domain' in vals:
                journal.alias_id.sudo().write({'alias_domain':vals.get('alias_domain')})
                if vals.get('alias_domain'):
                    del(vals['alias_domain'])
        return super(AccountJournal, self).write(vals)
    
    
