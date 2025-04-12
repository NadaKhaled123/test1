frappe.ui.form.on('Sales Order', {
   
    refresh: function(frm) {
        check_work_orders(frm);
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Quick Payment'), function() {
                open_payment_dialog(frm);
            });
        }
        
        if (frm.doc.docstatus === 1) {
        frm.add_custom_button(__('Fetch Work Order Update'), function() {
            frappe.call({
                method: 'inhouse.inhouse.controllers.sales_order.fetch_work_order_status',
                args: {
                    sales_order_name: frm.doc.name
                },
                callback: function(response) {
                    if (response.message) {
                        const { completed, total, percentage } = response.message;
                        frappe.msgprint({
                            title: __('Work Order Status Updated'),
                            indicator: 'green'
                        });

                      

                    }
                    frm.reload_doc();
                }
            });
        });}
    },
    onload: function(frm) {
        frm.set_query("custom_template_item", function() {
            return {
                filters: {
                    has_variants: 1  
                }
            };
        });

        frappe.realtime.on('work_order_created', (data) => {
            if (data.sales_order === frm.doc.name) {
                // Trigger the check for work orders
                check_work_orders(frm);
            }
        });
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Quick Payment'), function() {
                open_payment_dialog(frm);
            });
        }
    }
});

function open_payment_dialog(frm) {
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Sales Order',
            filters: { name: frm.doc.name },
            fieldname: ['grand_total', 'advance_paid']
        },
        callback: function(response) {
            const grand_total = response.message.grand_total || 0;
            const advance_paid = response.message.advance_paid || 0;
            const remaining_amount = grand_total - advance_paid;

            const dialog = new frappe.ui.Dialog({
                title: 'Quick Payment',
                fields: [
                    {
                        fieldname: 'payments_table',
                        fieldtype: 'Table',
                        label: 'Payments',
                        fields: [
                            {
                                fieldname: 'mode_of_payment',
                                fieldtype: 'Link',
                                options: 'Mode of Payment',
                                label: 'Mode of Payment',
                                reqd: 1,
                                in_list_view: 1
                            },
                            {
                                fieldname: 'paid_amount',
                                fieldtype: 'Currency',
                                label: 'Paid Amount',
                                reqd: 1,
                                in_list_view: 1
                            }
                        ]
                    }
                ],
                primary_action_label: 'Save Payments',
                primary_action: function() {
                    const data = dialog.get_values();
                    if (data && data.payments_table) {
                        const total_paid = data.payments_table.reduce((total, row) => total + row.paid_amount, 0);

                        if (total_paid > remaining_amount) {
                            frappe.msgprint(
                                __('Total Paid Amount ({0}) exceeds the Remaining Amount ({1}).', [total_paid, remaining_amount])
                            );
                        } else {
                            create_payment_entries(frm, data.payments_table);
                            frm.reload_doc();
                            dialog.hide();
                        }
                    } else {
                        frappe.msgprint(__('Please enter payment details.'));
                    }
                }
            });

            dialog.show();
        }
    });
}


function create_payment_entries(frm, payments) {
    frappe.call({
        method: 'inhouse.inhouse.controllers.sales_order.create_payment_entries',
        args: {
            sales_order: frm.doc.name,
            payments: payments
        },
        callback: function(response) {
            if (response.message) {
                frappe.msgprint(__('Payment Entries Created Successfully.'));
                frm.reload_doc()
            }
        }
    });
}



function check_work_orders(frm) {
    frappe.call({
        method: "inhouse.inhouse.controllers.sales_order.get_work_orders",
        args: {
            sales_order_name: frm.doc.name,
        },
        callback: function(r) {
            if (r.message && r.message > 0) {
                cur_frm.page.btn_secondary.hide();
            } else {
                cur_frm.page.btn_secondary.show();
            }
        }
    });
}


frappe.ui.form.on("Sales Order", {

    custom_template_item: function(frm) {
        frappe.call({
            method: "inhouse.inhouse.controllers.item.set_template_item_name",
            args: {
                template_item: frm.doc.custom_template_item
            },
            callback: function(response) {
                if (response.message) {
                    frm.set_value("custom_template_item_name", response.message);
                } else {
                    frappe.show_alert({
                        message: "Item name not found for the selected template item.",
                        indicator: 'red'
                    });
                }
            }
        });
        if (frm.doc.custom_template_item) {
            if (frm.fields_dict.custom_get_item) {
                frm.fields_dict.custom_get_item.$input.off('click').on('click', function() { 
                    open_variant_selector(frm);
                });
            }
            
        }
    }
});

let attribute_dialog = null; 

function open_variant_selector(frm) {
    if (attribute_dialog) {
        attribute_dialog.hide();
        attribute_dialog = null;
    }

    frappe.call({
        method: "inhouse.inhouse.controllers.sales_order.get_template_item_attributes_as_array_of_objects",
        args: {
            template_item: frm.doc.custom_template_item,
        },
        callback: function (response) {
            if (response.message) {
                show_attribute_popup(frm, response.message);
            }
        },
    });
}

function show_attribute_popup(frm, attributes) {
    let fields = [];
    console.log(attributes)
    attributes.forEach(attr => {
        let options = attr.values.map(value => ({
            label: value,
            fieldname: attr.attribute.replace(/\s+/g, '_').toLowerCase() + "_" + value.replace(/\s+/g, '_').toLowerCase(),
            fieldtype: "Check"
        }));

        fields.push({
            label: attr.attribute,
            fieldname: attr.attribute.replace(/\s+/g, '_').toLowerCase(),
            fieldtype: "Section Break"
        });

        fields.push(...options);
    });

    // Destroy the previous dialog instance if it exists
    if (attribute_dialog) {
        attribute_dialog.hide();
        attribute_dialog = null;
    }

    attribute_dialog = new frappe.ui.Dialog({
        title: "Select Item Attributes",
        fields: fields,
        primary_action_label: "Find Variant",
        primary_action(values) {
            let selected_values = {};
            let error_found = false;

            attributes.forEach(attr => {
                let attr_name = attr.attribute.replace(/\s+/g, '_').toLowerCase();
                let selected_values_for_attribute = [];

                attr.values.forEach(value => {
                    if (values[attr_name + "_" + value.replace(/\s+/g, '_').toLowerCase()]) {
                        selected_values_for_attribute.push(value);
                    }
                });

                if (selected_values_for_attribute.length > 1) {
                    frappe.show_alert({
                        message: `You cannot select more than one value for the attribute: ${attr.attribute}.`,
                        indicator: 'red'
                    });
                    error_found = true;
                } else if (selected_values_for_attribute.length === 1) {
                    selected_values[attr.attribute] = selected_values_for_attribute[0];
                }
            });

            if (!error_found) {
                find_variant_item(frm, selected_values);
                attribute_dialog.hide();
                attribute_dialog = null; // Reset the variable when dialog is closed
            }
        }
    });

    attribute_dialog.show();
}




function find_variant_item(frm, selected_values) {
    if (!frm.doc.selling_price_list) {
        frappe.show_alert({
            message: "You must set a value for the Price List to get the rate of the item.",
            indicator: 'red'
        });
        return; 
    }

    frappe.call({
        method: "inhouse.inhouse.controllers.sales_order.find_variant",
        args: {
            template_item: frm.doc.custom_template_item,
            selected_attributes: selected_values
        },
        callback: function(response) {
            if (response.message) {
                let variant = response.message;
                
                let existing_row = frm.doc.items.find(item => item.item_code === variant);
                
                if (existing_row) {
                    frappe.show_alert({
                        message: `Variant ${variant} already exists in the items table.`,
                        indicator: 'orange'
                    });
                } else {
                    let new_row = frm.add_child('items', {
                        item_code: variant,
                        qty: 1,
                    });

                    frappe.show_alert({
                        message: `Item ${variant} has been successfully added to the items table.`,
                        indicator: 'green'
                    }, 5); 

                    frappe.call({
                        method: "inhouse.inhouse.controllers.sales_order.get_item_name",
                        args: { variant: variant },
                        callback: function(item_name_response) {
                            if (item_name_response.message) {
                                new_row.item_name = item_name_response.message;
                            }
                        }
                    });
                    console.log("price list" , frm.doc.selling_price_list)

                    frappe.call({
                        method: "inhouse.inhouse.controllers.sales_order.get_item_price",
                        args: {
                            variant: variant,
                            price_list: frm.doc.selling_price_list
                        },
                        callback: function(price_response) {
                            if (price_response.message) {
                                new_row.rate = price_response.message;
                            }
                        }
                    });

                    frappe.call({
                        method: "inhouse.inhouse.controllers.sales_order.get_uom",
                        args: { variant: variant },
                        callback: function(uom_response) {
                            if (uom_response.message) {
                                new_row.uom = uom_response.message;
                                frm.refresh_field("items");
                            }
                        }
                    });

                    // frm.refresh_field("items");
                }
            } else {
                frappe.show_alert({
                    message: "No matching variant found.",
                    indicator: 'red'
                }, 5);
            }
        }
    });
}
