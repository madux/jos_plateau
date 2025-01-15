/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { formatFloat } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";
console.log("Loading the task Doughnut Memo widget");

export class TaskDoughnutFieldMemo extends Component {
    setup() {    
        this.chart = null;
        this.canvasRef = useRef("canvasTaskDougnnut");

        onWillStart(async () => await loadBundle("web.chartjs_lib"));

        useEffect(() => {
            this.renderChart();
            return () => {
                if (this.chart) {
                    this.chart.destroy();
                }
            };
        });
    }

    get title() {
        return this.props.title || this.props.record.fields[this.props.name].string || "";
    }

    get formattedValue() {
        return formatFloat(this.props.record.data[this.props.name], {
            humanReadable: true,
            decimals: 1,
        });
    }

    renderChart() { 
        var TodoValue = this.props.record.data[this.props.todofieldRed] 
        var ActiveValue = this.props.record.data[this.props.activefieldYellow]
        var DoneValue = this.props.record.data[this.props.donefieldGreen]
        const config = {
            type: "doughnut",
            data: {
                datasets: [
                    {
                        data: [parseInt(TodoValue), parseInt(ActiveValue), parseInt(DoneValue)],
                        backgroundColor: 
                        [
                            'rgba(232, 5, 43, 0.839)',
                            'rgb(253, 241, 5)',
                            'rgb(16, 235, 4)',
                        ],
                    },
                ],
            },
            options: {
                // circumference: 180,
                // rotation: 270,
                responsive: true,
                maintainAspectRatio: false,
                // cutout: "70%",
                layout: {
                    padding: 2,
                },
                plugins: {
                    title: {
                        display: true,
                        text: this.title,
                        padding: 4,
                    },
                    tooltip: {
                        displayColors: false,
                        callbacks: {
                            label: function (tooltipItem) {
                                if (tooltipItem.dataIndex === 0) {
                                    return _t('Todo' +':') + String(TodoValue) + '%';
                                }
                                else if (tooltipItem.dataIndex === 1) {
                                    return _t('Active' +':') + String(ActiveValue) + '%';
                                }
                                return _t('Done' +':') + String(DoneValue) + '%';
                            }, 
                        },
                    },
                },
                aspectRatio: 2,
            },
        };
        this.chart = new Chart(this.canvasRef.el, config);
    }
}

TaskDoughnutFieldMemo.template = "company_memo.TaskDoughnutFieldMemo";
TaskDoughnutFieldMemo.props = {
    ...standardFieldProps,
    maxValueField: { type: String },
    todofieldRed: { type: String },
    activefieldYellow: { type: String },
    donefieldGreen: { type: String },
    title: { type: String, optional: true },
};

export const taskDoughnutFieldMemo = {
    component: TaskDoughnutFieldMemo,
    supportedOptions: [
        {
            label: _t("Title"),
            name: "title",
            type: "string",
        },
        {
            label: _t("Max value field"),
            name: "max_value",
            type: "field",
            availableTypes: ["integer", "float"],
        },
         
    ],
    extractProps: ({ options }) => ({
        maxValueField: options.max_field,
        todofieldRed: options.todo_field_red,
        activefieldYellow: options.active_field_yellow,
        donefieldGreen: options.done_field_green,
        title: options.title,
    }),
};

registry.category("fields").add("taskdoughnutMemo", taskDoughnutFieldMemo);
