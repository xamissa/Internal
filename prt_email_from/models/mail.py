###################################################################################
# 
#    Copyright (C) Cetmix OÜ
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU LESSER GENERAL PUBLIC LICENSE as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

from odoo import api, fields, models
from odoo.tools import formataddr


################
# Mail.Message #
################
class MailMessage(models.Model):
    _inherit = "mail.message"

    @api.model
    def _get_default_from(self, user, email_from):
        """
        Check settings and use company's email if forced.
        Make 'From:' look like 'John Smith via Your Company <yorcompany@example.com>
        """
        company = user.company_id
        # Used for Pro version
        if self._context.get("force_email_from", False):
            company_email = email_from
        else:
            company_email = company.email
        # Check settings.
        # If not using company email return False
        if company_email and company.add_company_from:
            if company.add_company_mode == "r":
                name_from = company.name
            else:
                if company.email_joint:
                    name_from = " ".join((user.name, company.email_joint, company.name))
                else:
                    name_from = " ".join((user.name, company.name))

            return formataddr((name_from, company_email))
        else:
            return email_from

    # -- Create
    @api.model_create_multi
    def create(self, values_list):
        # Compose "email_from" if template is not used
        if not self._context.get("default_use_template", False):
            for vals in values_list:
                # Proceed only if Author is an internal user
                author_id = vals.get("author_id", False)
                if author_id:
                    users = self.env["res.partner"].browse(author_id).user_ids
                    if users and users[0].has_group("base.group_user"):
                        updated_from = self._get_default_from(
                            users[0], vals.get("email_from", False)
                        )
                        vals.update({"email_from": updated_from})
        return super(MailMessage, self).create(values_list)


###############
# Res.Company #
###############
class Company(models.Model):
    _name = "res.company"
    _inherit = "res.company"

    use_company_email = fields.Boolean(
        string="Use Company Email",
        help="Before: From 'Some User <some.user@usermail.com>'\n"
        "After: From 'Some User <mycompany@companymail.com>'",
    )
    add_company_from = fields.Boolean(
        string="Company Name In 'From'",
        help="Before: 'Some User <mycompany@example.com>'\n"
        "After: Some User via My Company <mycompany@example.com>",
    )
    add_company_mode = fields.Selection(
        string="Company Name",
        selection=[("a", "append to username"), ("r", "replace completely")],
        default="a",
    )
    add_sender_reply_to = fields.Boolean(
        string="Sender's Name In 'Reply-to'",
        help="Before: 'My Company <mycompany@example.com>'\n"
        "After: Some User via My Company <mycompany@example.com>",
    )
    email_joint = fields.Char(
        string="Name Joint",
        translate=True,
        default="via",
        help="Before: 'Some User My Company <mycompany@example.com>'\n"
        "After: Some User via My Company <mycompany@example.com>",
    )
