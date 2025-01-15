odoo.define('eha_multi_branch.account_financial_report_backend', function (require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');
    var ControlPanelMixin = require('web.ControlPanelMixin');


    // var report_backend = Widget.extend(ControlPanelMixin, {
    //     render_searchview_buttons: function() {
    //         var self = this;
    //         this.$searchview_buttons.find('#branch_filter').click(function (event) {
    //             var option_value = $(this).data('filter');
    //             var option_id = $(this).data('id');
    //             alert(option_id)
    //             // _.filter(self.report_options[option_value], function(el) {
    //             //     if (''+el.id == ''+option_id){
    //             //         if (el.selected === undefined || el.selected === null){el.selected = false;}
    //             //         el.selected = !el.selected;
    //             //     } else if (option_value === 'ir_filters') {
    //             //         el.selected = false;
    //             //     }
    //             //     return el;
    //             // });
    //             //self.reload();
    //         });
    //     },
     
    // });

});