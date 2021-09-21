# -*- coding: utf-8 -*-
import base64
import json

import werkzeug
import werkzeug.urls

from odoo import http, SUPERUSER_ID
from odoo.http import request
from odoo.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

from odoo.addons.website_crm.controllers.main import WebsiteForm

from captcha.image import ImageCaptcha
import random


class WebsiteForm(WebsiteForm):


    def gen_captcha(self,values):

        image = ImageCaptcha()
        captcha_value = str(random.randint(100,999))
        image_data = image.generate(captcha_value)

        values['captcha_src_data'] = (b'data:image/png;base64,%s' % base64.b64encode(image_data.getvalue())).decode("utf-8")
        request.session['captcha_sent'] = captcha_value

        image_data.close()


    @http.route(['/page/website.contactus', '/page/contactus', '/contactus'], type='http', auth="public", website=True)
    def contact(self, **kwargs):
        values = {}
        self.gen_captcha(values)
        for field in ['description', 'partner_name', 'phone', 'contact_name', 'email_from', 'name']:
            if kwargs.get(field):
                values[field] = kwargs.pop(field)
        values.update(kwargs=kwargs.items())
        return request.render("website.contactus", values)


    @http.route('/website_form/<string:model_name>', type='http', auth="public", methods=['POST'], website=True, csrf=False)
    def website_form(self, model_name, **kwargs):
        captcha_reseived = kwargs.pop("captcha",False)
        captcha_sent = request.session.get("captcha_sent",False)
        error = False
        if (not captcha_reseived or not captcha_sent or not captcha_reseived == captcha_sent):
            values = {}
            self.gen_captcha(values)
            _logger.info("Captcha error from %s: Captcha received (%s) != Captcha Sent (%s)\n"%(request.httprequest.environ["REMOTE_ADDR"],captcha_reseived,captcha_sent))
            return json.dumps({'error_fields' : ['captcha', {'captcha_src_data': values['captcha_src_data']}]}) #FIXME this is a hack actually, probably separate Captcha Widget should be implemented instead
        return super(WebsiteForm, self).website_form(model_name, **kwargs)
