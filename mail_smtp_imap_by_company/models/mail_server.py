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

import base64
import datetime
import dateutil
import email
import hashlib
import hmac
import lxml
import logging
import pytz
import re
import socket
import time

from collections import namedtuple
from email.message import Message
from email.utils import formataddr
from lxml import etree
from werkzeug import url_encode
from werkzeug import urls

from odoo import _, api, exceptions, fields, models, tools
from odoo.tools import pycompat, ustr
from odoo.tools.misc import clean_context
from odoo.tools.safe_eval import safe_eval
from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)

class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    default_company = fields.Many2one('res.company', string="Company")

class MailMail(models.Model):
    _inherit = "mail.mail"
    
    def send(self, auto_commit=False, raise_exception=False):
        """ Sends the selected emails immediately, ignoring their current
            state (mails that have already been sent should not be passed
            unless they should actually be re-sent).
            Emails successfully delivered are marked as 'sent', and those
            that fail to be deliver are marked as 'exception', and the
            corresponding error mail is output in the server logs.

            :param bool auto_commit: whether to force a commit of the mail status
                after sending each mail (meant only for scheduler processing);
                should never be True during normal transactions (default: False)
            :param bool raise_exception: whether to raise an exception if the
                email sending process has failed
            :return: True
        """
        for server_id, batch_ids in self._split_by_server():
            #geminatecs
            smtp_session = None
            active_company_id = self.env['res.users'].browse(self._context.get('uid') or self._uid or self.env.user.id).company_id
            company_server_id = self.env['ir.mail_server'].search([('default_company', '=', active_company_id.id)])
            server_id = company_server_id and company_server_id.id or server_id
            #geminatecs
            
            try:
                smtp_session = self.env['ir.mail_server'].connect(mail_server_id=server_id)
            except Exception as exc:
                if raise_exception:
                    # To be consistent and backward compatible with mail_mail.send() raised
                    # exceptions, it is encapsulated into an Odoo MailDeliveryException
                    raise MailDeliveryException(_('Unable to connect to SMTP Server'), exc)
                else:
                    batch = self.browse(batch_ids)
                    batch.write({'state': 'exception', 'failure_reason': exc})
                    batch._postprocess_sent_message(success_pids=[], failure_type="SMTP")
            else:
                self.browse(batch_ids)._send(
                    auto_commit=auto_commit,
                    raise_exception=raise_exception,
                    smtp_session=smtp_session)
                _logger.info(
                    'Sent batch %s emails via mail server ID #%s',
                    len(batch_ids), server_id)
            finally:
                if smtp_session:
                    smtp_session.quit()
                    

class FetchmailServer(models.Model):
    _inherit = 'fetchmail.server'

    default_company = fields.Many2one('res.company', string="Company")

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'
    
    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        if not isinstance(message, Message):
            raise TypeError('message must be an email.message.Message at this point')
        MailMessage = self.env['mail.message']
        Alias, dest_aliases = self.env['mail.alias'], self.env['mail.alias']
        catchall_alias = self.env['ir.config_parameter'].sudo().get_param("mail.catchall.alias")
        bounce_alias = self.env['ir.config_parameter'].sudo().get_param("mail.bounce.alias")
        fallback_model = model

        # get email.message.Message variables for future processing
        local_hostname = socket.gethostname()
        message_id = message.get('Message-Id')

        # compute references to find if message is a reply to an existing thread
        references = tools.decode_message_header(message, 'References')
        in_reply_to = tools.decode_message_header(message, 'In-Reply-To').strip()
        thread_references = references or in_reply_to
        reply_match, reply_model, reply_thread_id, reply_hostname, reply_private = tools.email_references(thread_references)

        # author and recipients
        email_from = tools.decode_message_header(message, 'From')
        email_from_localpart = (tools.email_split(email_from) or [''])[0].split('@', 1)[0].lower()
        email_to = tools.decode_message_header(message, 'To')
        email_to_localpart = (tools.email_split(email_to) or [''])[0].split('@', 1)[0].lower()

        # Delivered-To is a safe bet in most modern MTAs, but we have to fallback on To + Cc values
        # for all the odd MTAs out there, as there is no standard header for the envelope's `rcpt_to` value.
        rcpt_tos = ','.join([
            tools.decode_message_header(message, 'Delivered-To'),
            tools.decode_message_header(message, 'To'),
            tools.decode_message_header(message, 'Cc'),
            tools.decode_message_header(message, 'Resent-To'),
            tools.decode_message_header(message, 'Resent-Cc')])
        rcpt_tos_localparts = [e.split('@')[0].lower() for e in tools.email_split(rcpt_tos)]
        
        email_to_alias_domain_list = [e.split('@')[1].lower() for e in tools.email_split(rcpt_tos)]
        
        # 0. Verify whether this is a bounced email and use it to collect bounce data and update notifications for customers
        if bounce_alias and bounce_alias in email_to_localpart:
            # Bounce regex: typical form of bounce is bounce_alias+128-crm.lead-34@domain
            # group(1) = the mail ID; group(2) = the model (if any); group(3) = the record ID
            bounce_re = re.compile("%s\+(\d+)-?([\w.]+)?-?(\d+)?" % re.escape(bounce_alias), re.UNICODE)
            bounce_match = bounce_re.search(email_to)

            if bounce_match:
                bounced_mail_id, bounced_model, bounced_thread_id = bounce_match.group(1), bounce_match.group(2), bounce_match.group(3)

                email_part = next((part for part in message.walk() if part.get_content_type() == 'message/rfc822'), None)
                dsn_part = next((part for part in message.walk() if part.get_content_type() == 'message/delivery-status'), None)

                partners, partner_address = self.env['res.partner'], False
                if dsn_part and len(dsn_part.get_payload()) > 1:
                    dsn = dsn_part.get_payload()[1]
                    final_recipient_data = tools.decode_message_header(dsn, 'Final-Recipient')
                    partner_address = final_recipient_data.split(';', 1)[1].strip()
                    if partner_address:
                        partners = partners.sudo().search([('email', '=', partner_address)])
                        for partner in partners:
                            partner.message_receive_bounce(partner_address, partner, mail_id=bounced_mail_id)

                mail_message = self.env['mail.message']
                if email_part:
                    email = email_part.get_payload()[0]
                    bounced_message_id = tools.mail_header_msgid_re.findall(tools.decode_message_header(email, 'Message-Id'))
                    mail_message = MailMessage.sudo().search([('message_id', 'in', bounced_message_id)])

                if partners and mail_message:
                    notifications = self.env['mail.notification'].sudo().search([
                        ('mail_message_id', '=', mail_message.id),
                        ('res_partner_id', 'in', partners.ids)])
                    notifications.write({
                        'email_status': 'bounce'
                    })

                if bounced_model in self.env and hasattr(self.env[bounced_model], 'message_receive_bounce') and bounced_thread_id:
                    self.env[bounced_model].browse(int(bounced_thread_id)).message_receive_bounce(partner_address, partners, mail_id=bounced_mail_id)

                _logger.info('Routing mail from %s to %s with Message-Id %s: bounced mail from mail %s, model: %s, thread_id: %s: dest %s (partner %s)',
                             email_from, email_to, message_id, bounced_mail_id, bounced_model, bounced_thread_id, partner_address, partners)
                return []

        # 0. First check if this is a bounce message or not.
        #    See http://datatracker.ietf.org/doc/rfc3462/?include_text=1
        #    As all MTA does not respect this RFC (googlemail is one of them),
        #    we also need to verify if the message come from "mailer-daemon"
        if message.get_content_type() == 'multipart/report' or email_from_localpart == 'mailer-daemon':
            _logger.info('Routing mail with Message-Id %s: not routing bounce email from %s to %s',
                         message_id, email_from, email_to)
            return []

        # 1. Check if message is a reply on a thread
        msg_references = [ref for ref in tools.mail_header_msgid_re.findall(thread_references) if 'reply_to' not in ref]
        mail_messages = MailMessage.sudo().search([('message_id', 'in', msg_references)], limit=1)
        is_a_reply = bool(mail_messages)

        # 1.1 Handle forward to an alias with a different model: do not consider it as a reply
        if reply_model and reply_thread_id:
            other_alias = Alias.search([
                '&',
                ('alias_name', '!=', False),
                ('alias_name', '=', email_to_localpart)
            ])
            if other_alias and other_alias.alias_model_id.model != reply_model:
                is_a_reply = False

        if is_a_reply:
            model, thread_id = mail_messages.model, mail_messages.res_id
            if not reply_private:  # TDE note: not sure why private mode as no alias search, copying existing behavior
                dest_aliases = Alias.search([('alias_name', 'in', rcpt_tos_localparts)], limit=1)

            route = self.message_route_verify(
                message, message_dict,
                (model, thread_id, custom_values, self._uid, dest_aliases),
                update_author=True, assert_model=reply_private, create_fallback=True,
                allow_private=reply_private, drop_alias=True)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: direct reply to msg: model: %s, thread_id: %s, custom_values: %s, uid: %s',
                    email_from, email_to, message_id, model, thread_id, custom_values, self._uid)
                return [route]
            elif route is False:
                return []

        # 2. Look for a matching mail.alias entry
        if rcpt_tos_localparts:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)

            # check it does not directly contact catchall
            if catchall_alias and catchall_alias in email_to_localpart:
                _logger.info('Routing mail from %s to %s with Message-Id %s: direct write to catchall, bounce', email_from, email_to, message_id)
                body = self.env.ref('mail.mail_bounce_catchall').render({
                    'message': message,
                }, engine='ir.qweb')
                self._routing_create_bounce_email(email_from, body, message, reply_to=self.env.user.company_id.email)
                return []
            
            alias_domain_id = self.env['alias.mail'].search([('domain_name','in',email_to_alias_domain_list)])
#             dest_aliases = False
            if alias_domain_id:
                dest_aliases = Alias.search([('alias_domain','in',alias_domain_id.ids),('alias_name', 'in', rcpt_tos_localparts)])
            if dest_aliases:
                routes = []
                for alias in dest_aliases:
                    user_id = alias.alias_user_id.id
                    if not user_id:
                        # TDE note: this could cause crashes, because no clue that the user
                        # that send the email has the right to create or modify a new document
                        # Fallback on user_id = uid
                        # Note: recognized partners will be added as followers anyway
                        # user_id = self._message_find_user_id(message)
                        user_id = self._uid
                        _logger.info('No matching user_id for the alias %s', alias.alias_name)
                    route = (alias.alias_model_id.model, alias.alias_force_thread_id, safe_eval(alias.alias_defaults), user_id, alias)
                    route = self.message_route_verify(
                        message, message_dict, route,
                        update_author=True, assert_model=True, create_fallback=True)
                    if route:
                        _logger.info(
                            'Routing mail from %s to %s with Message-Id %s: direct alias match: %r',
                            email_from, email_to, message_id, route)
                        routes.append(route)
                return routes

        # 5. Fallback to the provided parameters, if they work
        if fallback_model:
            # no route found for a matching reference (or reply), so parent is invalid
            message_dict.pop('parent_id', None)
            route = self.message_route_verify(
                message, message_dict,
                (fallback_model, thread_id, custom_values, self._uid, None),
                update_author=True, assert_model=True)
            if route:
                _logger.info(
                    'Routing mail from %s to %s with Message-Id %s: fallback to model:%s, thread_id:%s, custom_values:%s, uid:%s',
                    email_from, email_to, message_id, fallback_model, thread_id, custom_values, self._uid)
                return [route]

        # ValueError if no routes found and if no bounce occured
        raise ValueError(
            'No possible route found for incoming message from %s to %s (Message-Id %s:). '
            'Create an appropriate mail.alias or force the destination model.' %
            (email_from, email_to, message_id)
        )
    
    @api.model
    def _message_route_process(self, message, message_dict, routes):
        self = self.with_context(attachments_mime_plainxml=True) # import XML attachments as text
        # postpone setting message_dict.partner_ids after message_post, to avoid double notifications
        original_partner_ids = message_dict.pop('partner_ids', [])
        thread_id = False
        for model, thread_id, custom_values, user_id, alias in routes or ():
            subtype_id = False
            Model = self.env[model].with_context(mail_create_nosubscribe=True, mail_create_nolog=True)
            if not (thread_id and hasattr(Model, 'message_update') or hasattr(Model, 'message_new')):
                raise ValueError(
                    "Undeliverable mail with Message-Id %s, model %s does not accept incoming emails" %
                    (message_dict['message_id'], model)
                )

            # disabled subscriptions during message_new/update to avoid having the system user running the
            # email gateway become a follower of all inbound messages
            ModelCtx = Model.with_user(user_id).sudo()
            if thread_id and hasattr(ModelCtx, 'message_update'):
                thread = ModelCtx.browse(thread_id)
                thread.message_update(message_dict)
            else:
                # if a new thread is created, parent is irrelevant
                message_dict.pop('parent_id', None)
                thread = ModelCtx.message_new(message_dict, custom_values)
                print (">>>>>>>>>>>> THREAD>>>",thread)
                #geminatecs
                thread.sudo().write({'company_id': alias.alias_domain.company_id.id})
                #geminatecs

                thread_id = thread.id
                subtype_id = thread._creation_subtype().id

            # replies to internal message are considered as notes, but parent message
            # author is added in recipients to ensure he is notified of a private answer
            parent_message = False
            if message_dict.get('parent_id'):
                parent_message = self.env['mail.message'].sudo().browse(message_dict['parent_id'])
            partner_ids = []
            if not subtype_id:
                if message_dict.pop('internal', False):
                    subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note')
                    if parent_message and parent_message.author_id:
                        partner_ids = [parent_message.author_id.id]
                else:
                    subtype_id = self.env['ir.model.data'].xmlid_to_res_id('mail.mt_comment')

            post_params = dict(subtype_id=subtype_id, partner_ids=partner_ids, **message_dict)
            # remove computational values not stored on mail.message and avoid warnings when creating it
            for x in ('from', 'to', 'cc', 'recipients', 'references', 'in_reply_to', 'bounced_email', 'bounced_message', 'bounced_msg_id', 'bounced_partner'):
                post_params.pop(x, None)
            new_msg = False
            if thread._name == 'mail.thread':  # message with parent_id not linked to record
                new_msg = thread.message_notify(**post_params)
            else:
                new_msg = thread.message_post(**post_params)

            if new_msg and original_partner_ids:
                # postponed after message_post, because this is an external message and we don't want to create
                # duplicate emails due to notifications
                new_msg.write({'partner_ids': original_partner_ids})
        return thread_id
