/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { formatFloat } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";
console.log("Loading the gauge Memo widget")
export class GaugeFieldMemo extends Component {
    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvasMemo");

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
        // return this.props.title || this.props.record.fields[this.props.name].string || "";
        return this.props.title || "";
    }

    get formattedValue() {
        return formatFloat(this.props.record.data[this.props.name], {
            humanReadable: true,
            decimals: 1,
        });
    }

    renderChart() {
        console.log('RECORD data')
        console.log(this.props.record.data)
        console.log('Fields data')
        console.log(this.props.record.fields)
        const gaugeValue = this.props.record.data[this.props.name];
        let maxValue = Math.max(gaugeValue, this.props.record.data[this.props.maxValueField]);
        console.log(`${maxValue} and the ga ${gaugeValue} ====> ${this.props.record.data[this.props.maxValueField]}`)
        let maxLabel = maxValue;
        if (gaugeValue === 0 && maxValue === 0) {
            maxValue = 1;
            maxLabel = 0;
        }
        let redLabel = this.props.fieldRed //record.data[this.props.fieldRed]
        let greenLabel = this.props.fieldGreen //record.data[this.props.fieldGreen]
        const circumference = 260;
        console.log(`THIOP OOP ==> ${gaugeValue}`, `${maxValue - gaugeValue}`)
        const config = {
            type: "doughnut",
            data: {
                datasets: [
                    {
                        data: [gaugeValue, maxValue - gaugeValue],
                        // data: [10, 20],
                        backgroundColor: 
                        ["#91f552", "#d44c4c"],
                        // label: this.title,
                        label: _t(greenLabel +':') + gaugeValue +' / ' +_t(redLabel +':') + String(maxValue - gaugeValue),
                        // tension: 0.1,
                        fill: false,
                    },
                ],
            },
            options: {
                responsive: true,
                layout: {
                  padding: {
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0
                  }
                },
                circumference: circumference,
                rotation: (circumference / 2) * -1, // 270
                responsive: true,
                maintainAspectRatio: true,
                cutout: "73%",
                borderWidth: 0,
                borderRadius: function (context, options) {
                    const index = context.dataIndex;
                    let radius = {};
                    if (index == 0) {
                      radius.innerStart = 50;
                      radius.outerStart = 50;
                    }
                    if (index === context.dataset.data.length - 1) {
                      radius.innerEnd = 50;
                      radius.outerEnd = 50;
                    }
                    return radius;
                  },
                scales: {
                  y: {
                    display: false // This hides the y-axis, which removes the margin
                  },
                  x: {
                    display: false // This hides the y-axis, which removes the margin
                  }
                },
                plugins: {
                    title: {
                        display: false,
                        text: this.title,
                        padding: {
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0
                          },
                    },
                    tooltip: {
                        displayColors: false,
                        callbacks: {
                            label: function (tooltipItem) {
                                if (tooltipItem.dataIndex === 0) {
                                    return _t(greenLabel +':') + gaugeValue + '%';
                                }
                                return _t(redLabel +':') + String(maxValue - gaugeValue);
                            },
                        },
                    },
                },
                aspectRatio: 0.5,
              }
            // options: {
            //     circumference: circumference,
            //     rotation: (circumference / 2) * -1, // 270
            //     responsive: true,
            //     maintainAspectRatio: true,
            //     cutout: "73%",
            //     borderWidth: 0,
            //     borderRadius: function (context, options) {
            //         const index = context.dataIndex;
            //         let radius = {};
            //         if (index == 0) {
            //           radius.innerStart = 50;
            //           radius.outerStart = 50;
            //         }
            //         if (index === context.dataset.data.length - 1) {
            //           radius.innerEnd = 50;
            //           radius.outerEnd = 50;
            //         }
            //         return radius;
            //       },
                
            //     layout: {
            //         padding: 2,
            //     },
            //     plugins: {
            //         title: {
            //             display: true,
            //             text: this.title,
            //             padding: 2,
            //         },
            //         tooltip: {
            //             displayColors: false,
            //             callbacks: {
            //                 label: function (tooltipItem) {
            //                     if (tooltipItem.dataIndex === 0) {
            //                         return _t(greenLabel +':') + gaugeValue + '%';
            //                     }
            //                     return _t(redLabel +':') + String(maxValue - gaugeValue);
            //                 },
            //             },
            //         },
            //     },
            //     aspectRatio: 2,
            // },
        };
        this.chart = new Chart(this.canvasRef.el, config);
    }
}

GaugeFieldMemo.template = "company_memo.GaugeFieldMemo";
GaugeFieldMemo.props = {
    ...standardFieldProps,
    maxValueField: { type: String },
    fieldGreen: { type: String },
    fieldRed: { type: String },
    guageInsideText: { type: String },
    title: { type: String, optional: true },
};

export const gaugeFieldMemo = {
    component: GaugeFieldMemo,
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
        guageInsideText: options.guageInsideText
    }),
};

registry.category("fields").add("gaugeMemo", gaugeFieldMemo);
