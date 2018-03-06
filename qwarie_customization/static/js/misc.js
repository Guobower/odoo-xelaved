odoo.define('qwarie.throbber', function (require) {
    "use strict";

    var core = require('web.core');
    var crash_manager = require('web.crash_manager');
    var session = require('web.session');
    var Widget = require('web.Widget');

    var _t = core._t;
    var Spinner = window.Spinner;

    var messages = function() {
        return [
            [0, _t("Saving...")],
            [2, _t("Saved!")],
        ];
    };

    var Throbber = Widget.extend({
        template: "Throbber",
        start: function() {
            var opts = {
            lines: 13, // The number of lines to draw
            length: 7, // The length of each line
            width: 4, // The line thickness
            radius: 10, // The radius of the inner circle
            rotate: 0, // The rotation offset
            color: '#FFF', // #rgb or #rrggbb
            speed: 1, // Rounds per second
            trail: 60, // Afterglow percentage
            shadow: false, // Whether to render a shadow
            hwaccel: false, // Whether to use hardware acceleration
            className: 'spinner', // The CSS class to assign to the spinner
            zIndex: 2e9, // The z-index (defaults to 2000000000)
            top: 'auto', // Top position relative to parent in px
            left: 'auto' // Left position relative to parent in px
            };
            this.spin = new Spinner(opts).spin(this.$el[0]);
            this.start_time = new Date().getTime();
            this.act_message();
        },
        act_message: function() {
            var self = this;
            setTimeout(function() {
                if (self.isDestroyed())
                    return;
                var seconds = (new Date().getTime() - self.start_time) / 1000;
                var mes;
                _.each(messages(), function(el) {
                    if (seconds >= el[0])
                        mes = el[1];
                });
                self.$(".oe_throbber_message").html(mes);
                self.act_message();
            }, 1000);
        },
        destroy: function() {
            if (this.spin)
                this.spin.stop();
            this._super();
        },
    });


    /** Setup blockui */
    if ($.blockUI) {
        $.blockUI.defaults.baseZ = 1100;
        $.blockUI.defaults.message = '<div class="openerp oe_blockui_spin_container" style="background-color: transparent;">';
        $.blockUI.defaults.css.border = '0';
        $.blockUI.defaults.css["background-color"] = '';
    }


    var throbbers = [];

    function blockUI () {
        var tmp = $.blockUI.apply($, arguments);
        var throbber = new Throbber();
        throbbers.push(throbber);
        throbber.appendTo($(".oe_blockui_spin_container"));
        $('body').addClass('o_ui_blocked');
        return tmp;
    }

    function unblockUI () {
        _.invoke(throbbers, 'destroy');
        throbbers = [];
        $('body').removeClass('o_ui_blocked');
        return $.unblockUI.apply($, arguments);
    }

    return {
        blockUI: blockUI,
        unblockUI: unblockUI,
    };

});
