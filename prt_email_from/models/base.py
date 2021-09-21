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

from odoo import models, tools


class BaseModel(models.AbstractModel):
    _inherit = "base"

    def _notify_get_reply_to(
        self, default=None, records=None, company=None, doc_names=None
    ):
        """
        Cetmix. In Pro version we add an ability to modify 'Reply-to'
        This is a copy-paste of the base method.
         Need to check it regularly for possible changes
        """
        if records:
            raise ValueError(
                "Use of records is deprecated as this method is available on BaseModel."
            )

        _records = self
        model = (
            _records._name if _records and _records._name != "mail.thread" else False
        )
        res_ids = _records.ids if _records and model else []
        _res_ids = res_ids or [False]  # always have a default value located in False

        alias_domain = (
            self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
        )
        result = dict.fromkeys(_res_ids, False)
        result_email = dict()
        doc_names = doc_names if doc_names else dict()

        if alias_domain:
            if model and res_ids:
                if not doc_names:
                    doc_names = {rec.id: rec.display_name for rec in _records}

                mail_aliases = (
                    self.env["mail.alias"]
                    .sudo()
                    .search(
                        [
                            ("alias_parent_model_id.model", "=", model),
                            ("alias_parent_thread_id", "in", res_ids),
                            ("alias_name", "!=", False),
                        ]
                    )
                )
                # take only first found alias for each thread_id,
                # to match order (1 found -> limit=1 for each res_id)
                for alias in mail_aliases:
                    result_email.setdefault(
                        alias.alias_parent_thread_id,
                        "{}@{}".format(alias.alias_name, alias_domain),
                    )

            # left ids: use catchall
            left_ids = set(_res_ids) - set(result_email)
            if left_ids:
                catchall = (
                    self.env["ir.config_parameter"]
                    .sudo()
                    .get_param("mail.catchall.alias")
                )
                if catchall:
                    result_email.update(
                        {
                            rid: "{}@{}".format(catchall, alias_domain)
                            for rid in left_ids
                        }
                    )

            # compute name of reply-to - TDE tocheck: quotes and stuff like that
            # Cetmix
            company_id = company if company else self.env.user.company_id

            # Prepend with user's name
            if company_id.add_sender_reply_to:
                if company_id.email_joint:
                    company_name = " ".join(
                        (self.env.user.name, company_id.email_joint, company_id.name)
                    )
                else:
                    company_name = " ".join((self.env.user.name, company_id.name))
            else:
                company_name = company_id.name

            for res_id in result_email:
                name = "{}{}{}".format(
                    company_name,
                    " " if doc_names.get(res_id) else "",
                    doc_names.get(res_id, ""),
                )
                result[res_id] = tools.formataddr((name, result_email[res_id]))

        left_ids = set(_res_ids) - set(result_email)
        if left_ids:
            result.update({res_id: default for res_id in left_ids})

        return result
