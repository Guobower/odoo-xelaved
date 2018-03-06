odoo.define('qwarie.CalendarView', function (require) {
    "use strict";

    var CalendarView = require('web_calendar.CalendarView');
    var widgets = require('web_calendar.widgets');
    var uid = null;

    CalendarView.include({
        init_calendar: function () {
            this._super();
            this.$calendar.fullCalendar('changeView','month');
            return $.when();
        },
        init: function (parent, dataset, view_id, options) {
            this._super.apply(this, arguments);
            uid = dataset.context.uid;
        },
    });
    widgets.SidebarFilter.include({ 
        events_loaded: function() {
            this._super.apply(this, arguments);
            if ([1, ].includes(uid)) {
               this.$el.find('input[value=-1]').trigger('change');
            }
        },
    });
});