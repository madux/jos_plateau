/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
console.log("BROUEUWEUEW 2122")
export class memoFormController extends FormController {
    
    setup() {
        super.setup();
        this.chart = null;
        this.canvasRef = useRef("canvas");
        // this.data = JSON.parse(this.props.record.data[this.props.name]);

        onWillStart(async () => await loadBundle("web.chartjs_lib"));

        useEffect(() => {
            // this.renderChart();
            console.log('finishing the final game')
            return () => {
                if (this.chart) {
                    this.chart.destroy();
                }
            };
        }); 
        
    }
    // /**
    //  * @override
    //  */
    // async beforeExecuteActionButton(clickParams) {
    //     const record = this.model.root;
    //     if (
    //         clickParams.name === "action_submit_expenses" &&
    //         record.data.duplicate_expense_ids.count
    //     ) {
    //         return new Promise((resolve) => {
    //             this.dialogService.add(ConfirmationDialog, {
    //                 body: _t("An expense of same category, amount and date already exists."),
    //                 confirm: async () => {
    //                     await this.orm.call("hr.expense", "action_approve_duplicates", [record.resId]);
    //                     resolve(true);
    //                 },
    //             }, {
    //                 onClose: resolve.bind(null, false),
    //             });
    //         });
    //     }
    //     return super.beforeExecuteActionButton(...arguments);
    // }
}

export const memoFormView = {
    ...formView,
    Controller: memoFormController,
};

registry.category("views").add("memo_model_form_view_33", memoFormView);
