odoo.define('website_crm_captcha.s_website_form', ['website_form.s_website_form', 'web.public.widget', 'web.core'], function (require) {
  'use strict';

  var core = require('web.core');
  var publicWidget = require('web.public.widget');

  var _t = core._t;
  var qweb = core.qweb;

  publicWidget.registry.s_website_form.include({
    check_error_fields: function (error_fields) {

      if (Array.isArray(error_fields)) {
        var i = error_fields.indexOf("captcha");

        if (-1 != i && ++i < error_fields.length) {
          var new_captcha = error_fields.splice(i, 1)[0];
          this.$el.find("img.website-crm-captcha-img")[0].src = new_captcha.captcha_src_data;
        }
      }
      return this._super(error_fields);
    },
  });
});
