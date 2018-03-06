odoo.define('qwarie.custom_webclient', function (require) {
    'use strict';
    var wClient = require('web.WebClient');
    var lView = require('web.ListView');
    var Sidebar = require('web.Sidebar');
    var formView = require('web.FormView');
    var quickCreate = require('web_kanban.quick_create');
    var throbber = require('qwarie.throbber');
    var SearchView = require('web.SearchView');

    var core = require('web.core');
    var data = require('web.data');
    var _t = core._t;
    var qweb = core.qweb;

    wClient.include({
        init: function (parent, client_options) {
            this._super(parent, client_options);
            this.set('title_part', {"zopenerp": "Qwarie CRM"});
            document.title = document.title.replace('Survey', 'Exam');
        },
    });
    var messages_by_seconds = function() {
        return [
            [0, _t("Saving...")],
            [2, _t("Saved!")],
        ];
    };

    formView.include({
        init: function(parent, dataset, view_id, options) {
            var self = this;
            if (dataset.model === 'project.task' || dataset.model === 'project.project') {
                options.initial_mode = 'edit';
                $('.o_chatter_button_save_and_send_btn').removeClass('hide');
            }

            this._super(parent, dataset, view_id, options);
        },
        on_button_save: function(e) {
            var self = this;
            if (this.is_disabled) {
                return;
            }
            this.disable_button();
            return this.save().done(function(result) {
                self.trigger("save", result);
                self.reload().then(function() {
                    if (self.dataset.model === 'project.task' || self.dataset.model === 'project.project') {
                        throbber.blockUI();
                        setTimeout(function() { throbber.unblockUI(); }, 3000);
                        self.to_edit_mode();
                        $('.o_chatter_button_save_and_send_btn').removeClass('hide');
                    } else {
                        self.to_view_mode();
                    }
                    core.bus.trigger('do_reload_needaction');
                    core.bus.trigger('form_view_saved', self);
                });
            }).always(function(){
                self.enable_button();
            });
        },
        on_button_cancel: function(event) {
            this._super(event);
            if ((this.dataset.model === 'project.task' || this.dataset.model === 'project.project') && !$('.o_composer_input').is(':visible')) {
                $('.o_chatter_button_save_and_send_btn').hide();
            }
        },
        on_button_edit: function() {
            this._super();
            $('.o_chatter_button_save_and_send_btn').show();
        },
    });

    lView.include({
        handle_button: function (name, id, callback) {
            if (name === 'clipboard') {
                var record = this.records.get(id).toContext();
                var userSurveyURL = record.survey_url + '/' + record.token;
                userSurveyURL = userSurveyURL.replace('survey/', (record.survey_type === 'preliminary' ? 'exam' : record.survey_type) + '/');
                // create input placeholder to copy text
                var input = document.createElement("INPUT");
                input.setAttribute("type", "text");
                input.setAttribute('value', userSurveyURL);
                document.body.appendChild(input);
                input.select();
                // trigger browser native clipboard copy
                document.execCommand('copy', false, null);
                // remove input
                document.body.removeChild(input);
            }

            this._super(name, id, callback);
        },
        render_sidebar: function($node) {
            if (!this.sidebar && this.options.sidebar) {
                this.sidebar = new Sidebar(this, {editable: this.is_action_enabled('edit')});
                if (this.fields_view.toolbar) {
                    this.sidebar.add_toolbar(this.fields_view.toolbar);
                }
                self = this;
                this.session.user_has_group('base.group_system').then(function(can_export) {
                    self.sidebar.add_items('other', _.compact([
                        can_export && { label: _t("Export"), callback: self.on_sidebar_export },
                        self.fields_view.fields.active && {label: _t("Archive"), callback: self.do_archive_selected},
                        self.fields_view.fields.active && {label: _t("Unarchive"), callback: self.do_unarchive_selected},
                        self.is_action_enabled('delete') && { label: _t('Delete'), callback: self.do_delete_selected }
                    ]));
                });

                $node = $node || this.options.$sidebar || this.$('.oe_list_sidebar');
                this.sidebar.appendTo($node);

                // Hide the sidebar by default (it will be shown as soon as a record is selected)
                this.sidebar.do_hide();
            }
        },
    });

    quickCreate.RecordQuickCreate.include({
        start: function () {
            if (window.location.hash.indexOf('model=project.task') > -1) {
                this.$('input').attr('placeholder', 'Enter your reference number and/or case name');
                this.$('.o_kanban_add').text('Save');
            }
            this._super();
            
        },
    });
    SearchView.include({
        init: function() {
            this._super.apply(this, arguments);
            this.visible_filters = true;
        },
    });
});
