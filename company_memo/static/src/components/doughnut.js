/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { formatFloat } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";
console.log("Loading the DOUGHNUT Memo widget")
export class DoughnutFieldMemo extends Component {
    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvasDougnnut");

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
    //     console.log('RECORD data')
    //     console.log(this.props.record.data)
    //     console.log('Fields data')
    //     console.log(this.props.record.fields)
        const gaugeValue = this.props.record.data[this.props.name];
        let maxValue = Math.max(gaugeValue, this.props.record.data[this.props.maxValueField]);
        let maxLabel = maxValue;
        if (gaugeValue === 0 && maxValue === 0) {
            maxValue = 1;
            maxLabel = 0;
        }
        let redLabel = this.props.fieldRed //record.data[this.props.fieldRed]
        let greenLabel = this.props.fieldGreen //record.data[this.props.fieldGreen]
        const config = {
            type: "doughnut",
            data: {
                datasets: [
                    {
                        data: [gaugeValue, maxValue - gaugeValue],
                        // ["#1f77b4", "#dddddd"],
                        backgroundColor: 
                        ['rgb(16, 235, 4)',
                        'rgba(232, 5, 43, 0.839)'],
                        label: _t(greenLabel +':') + gaugeValue +' / ' +_t(redLabel +':') + String(maxValue - gaugeValue),
                    },
                ],
            },
            options: {
                // circumference: 180,
                // rotation: 270,
                responsive: true,
                maintainAspectRatio: ture,
                // cutout: "70%",
                layout: {
                    padding: 1,//5
                    margin: 1,
                },
                plugins: {
                    title: {
                        display: true,
                        text: this.title,
                        padding: 1, //4
                    },
                    tooltip: {
                        displayColors: false,
                        callbacks: {
                            label: function (tooltipItem) {
                                if (tooltipItem.dataIndex === 0) {
                                    return _t(greenLabel +':') + gaugeValue;
                                }
                                return _t(redLabel +':') + String(maxValue - gaugeValue);
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

DoughnutFieldMemo.template = "company_memo.DoughnutFieldMemo";
DoughnutFieldMemo.props = {
    ...standardFieldProps,
    maxValueField: { type: String },
    fieldGreen: { type: String },
    fieldRed: { type: String },
    // greenLabel: { type: String },
    // redLabel: { type: String },
    title: { type: String, optional: true },
};

// const resValue = this.props.record.data[this.props.name];
// let maxValue = Math.max(gaugeValue, this.props.record.data[this.props.maxValueField]);
export const doughnutFieldMemo = {
    
    component: DoughnutFieldMemo,
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
        fieldRed: options.field_red,
        fieldGreen: options.field_green,
        title: options.title,
    }),
};

registry.category("fields").add("doughnutMemo", doughnutFieldMemo);
