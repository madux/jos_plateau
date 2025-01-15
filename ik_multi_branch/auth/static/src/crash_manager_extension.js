odoo.define('eha_multi_branch.crashManager', function (require) {
        "use strict";
        var ajax = require('web.ajax');
        var core = require('web.core');
        var CrashManager = require('web.CrashManager');
        var Dialog = require('web.Dialog');
        
        var _t = core._t;
        var QWeb = core.qweb;

        // setInterval(function() {
        //     ajax.jsonRpc('/eha_multi_branch/login/session_info', 'call', {}, {shadow:false}).then(function (res) {
        //         console.log("response: "+res)
        //         if(res == "expired") window.location.reload();
        //     }).fail(function () {
        //       console.log("Error Occurred")
        //     });
        // }, 30000);
        
        CrashManager.include({
    
            /**
             * @override
             * This function is invoked after user performs an action after session expiry
             */
            rpc_error: function (error) {
                var self = this;
                if (error.data.name === "odoo.http.SessionExpiredException" || error.data.name === "werkzeug.exceptions.Forbidden" ) {
                    window.location.reload(true);
                    return;
                } else {
                    this._super.apply(this, arguments);
                }
            },
        });
    
    });

    
    