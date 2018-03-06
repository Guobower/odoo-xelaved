odoo.define('qwarie.custom_chatter', function (require) {

    'use strict';
    var Chatter = require('mail.Chatter');
    var composer = require('mail.composer');
    var core = require('web.core');
    var _t = core._t;
    var qweb = core.qweb;
    var form_common = require('web.form_common');
    var throbber = require('qwarie.throbber');
    var Widget = require('web.Widget');

    Chatter.include({
        events: {
            'click .o_chatter_button_save_and_send_btn': 'on_composer_save_and_send',
            'click .o_chatter_button_new_message': 'on_open_composer_new_message',
            'click .o_chatter_button_log_note': 'on_open_composer_log_note',
        },

        start: function () {
           this._super.apply(this, arguments);
           if (this.model != 'project.project' && this.model != 'project.task') {
               this.$('.o_chatter_button_save_and_send_btn').hide();
           } else {
               this.$('.o_chatter_button_save_and_send_btn').show();
           }
        },

        mute_new_message_button: function (mute) {
            if (mute) {
                if (this.model === 'project.project' || this.model === 'project.task') {
                    this.$('.o_chatter_button_save_and_send_btn').show();
                }
            }
            this._super(mute);
        },

        on_composer_save_and_send: function () {
            var saved = false;
            if ($('.o_formdialog_save').is(':visible')) {
                $('.o_formdialog_save').click();
                saved = true;
            } else if ($('.oe_form_button_save:last').is(':visible')) {
                $('.oe_form_button_save').click();
                saved = true;
            }
            if ($('.o_composer_button_send:last').is(':visible')) {
                if (!this.composer.is_empty() || !this.composer.do_check_attachment_upload()) {
                    this.composer.send_message();
                    saved = true;
                }
            }
            if (saved) {
                throbber.blockUI();
                setTimeout(function() { throbber.unblockUI(); }, 3000);
            }
        },
    });
});
