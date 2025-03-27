// Copyright (c) 2024, inhouse and contributors
// For license information, please see license.txt

frappe.ui.form.on('Item Customization', {
    setup: function(frm){
     
        frm.set_query('template_item', function(doc) {
            return {
                filters: {
                    'has_variants': 1,
                    'item_group':frm.doc.item_group
                }
            };
        });
        frm.set_query('item_group', function(doc) {
            return {
                filters: {
                    'parent_item_group':'مجموعة المنتجات التامة'
                }
            };
        });

    
    },
    template_item: function(frm){
        // frm.clear_table('fetched_variant_attributes');
        frm.refresh_field('fetched_variant_attributes');
        set_template_item_name(frm);
    },
    item_group: function(frm) {
        frm.set_query('item_group', function(doc) {
            return {
                filters: {
                    'parent_item_group':'مجموعة المنتجات التامة'
                }
            };
        });
        // frm.clear_table('fetched_variant_attributes');
        frm.refresh_field('fetched_variant_attributes');

        frm.set_value('template_item', null);
        frm.set_query('template_item', function(doc) {
            return {
                filters: {
                    'has_variants': 1,
                    'item_group':frm.doc.item_group
                }
            };
    
        })
    }
    
    });
    
    frappe.ui.form.on('Item Customization', {
            refresh: function(frm) {
                if (frm.doc.docstatus === 1) {
                    frm.add_custom_button(__('Create Sales Order'), function() {
                        create_sales_order(frm);
                    });
                }
    
            if (frm.is_new()) {
                frm.toggle_display('fetched_variant_attributes', false);
                frm.toggle_display('items_to_be_created', false);

            } else {
                frm.toggle_display('fetched_variant_attributes', true);
                frm.toggle_display('items_to_be_created', true);

            }
    
            frm.fields_dict.select_variants.$wrapper.find('button').off('click').on('click', function() {
                if (!frm.doc.template_item) {
                    frappe.msgprint(__('Please select an Item Template first.'));
                    return;
                }
                open_attribute_selection_modal(frm);
            });
        }        
    
    });
    function set_template_item_name(frm) {
        if (frm.doc.template_item) {
            frappe.call({
                method: 'inhouse.inhouse.controllers.item.set_template_item_name',
                args: {
                    template_item: frm.doc.template_item 
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('template_item_name', r.message); 
                    }
                }
            });
        }
    }
    
    
    function open_attribute_selection_modal(frm) {
        if (!frm.doc.template_item) {
            frappe.msgprint(__('Please select a Template Item first.'));
            return;
        }
        let template_item_price;
        frm.call({
            method: 'inhouse.inhouse.controllers.item.get_template_item_price',
            args: { template_item: frm.doc.template_item },
            callback: function(r) {
                if (r.message) {
                   template_item_price = r.message;
                }
            }
        });
    
        frappe.call({
            method: 'inhouse.inhouse.controllers.item.get_template_attributes',
            args: {
                template_item: frm.doc.template_item
            },
            callback: function(r) {
                if (r.message) {
                    console.log(r.message)
                    let attributes = r.message.sort((a, b) => a.idx - b.idx); // Sort by index
                    let attribute_names = attributes.map(attr => attr.attribute_name);
    
                    let attribute_promises = attribute_names.map(attr => {
                        return frappe.call({
                            method: 'inhouse.inhouse.controllers.item.get_attribute_values',
                            args: {
                                attribute: attr,
                                template_item: frm.doc.template_item
                            }
                        });
                    });
    
                    let required_promises = attribute_names.map(attr => {
                        return frappe.call({
                            method: 'inhouse.inhouse.controllers.item.check_attribute_required',
                            args: {
                                attribute: attr,
                                template_item: frm.doc.template_item
                            }
                        });
                    });
    
                    Promise.all([Promise.all(attribute_promises), Promise.all(required_promises)]).then(results => {
                        let attribute_values = results[0];
                        let required_status = results[1];
    
                        let dialog_fields = attribute_names.flatMap((attr, idx) => {
                            let values = attribute_values[idx]?.message || [];
                            let isRequired = required_status[idx]?.message.required;
    
                            if (values.length === 1) {
                                return isRequired
                                    ? [
                                          {
                                              fieldname: `data_${attr}`,
                                              fieldtype: 'Data',
                                              label: attr,
                                              default: values[0],
                                              read_only: 1
                                          }
                                      ]
                                    : [
                                          {
                                              fieldname: `check_${attr}`,
                                              fieldtype: 'Check',
                                              label: `optional ${attr}`,
                                              default: 1,
                                              onchange: function() {
                                                  let isChecked = dialog.get_value(`check_${attr}`);
                                                  dialog.set_df_property(`data_${attr}`, 'hidden', !isChecked);
                                              }
                                          },
                                          {
                                              fieldname: `data_${attr}`,
                                              fieldtype: 'Data',
                                              label: attr,
                                              default: values[0],
                                              read_only: 1,
                                              hidden: 0
                                          }
                                      ];
                            }
    
                            return isRequired
                                ? [
                                      {
                                          fieldname: `select_${attr}`,
                                          fieldtype: 'Select',
                                          label: attr,
                                          options: '\n' + values.join('\n'), 
                                          default: "", 
                                          hidden: 0
                                      }
                                  ]
                                : [
                                      {
                                          fieldname: `check_${attr}`,
                                          fieldtype: 'Check',
                                          label: `optional ${attr}`,
                                          default: 1,
                                          onchange: function() {
                                              let isChecked = dialog.get_value(`check_${attr}`);
                                              dialog.set_df_property(`select_${attr}`, 'hidden', !isChecked);
                                          }
                                      },
                                      {
                                          fieldname: `select_${attr}`,
                                          fieldtype: 'Select',
                                          label: attr,
                                          options: '\n' + values.join('\n'),
                                          default: "",
                                          hidden: 0
                                      }
                                  ];
                        });
    
                        let dialog = new frappe.ui.Dialog({
                            title: __('Select Attributes'),
                            fields: dialog_fields,
                            primary_action: function() {
                                let selected_attributes = {};
                                let validation_failed = false;

    
                                attribute_names.forEach(attr => {
                                    let value = dialog.get_value(`data_${attr}`) || dialog.get_value(`select_${attr}`);
    
                                    if (required_status[attribute_names.indexOf(attr)].message.required && !value) {
                                        frappe.msgprint(__('Please select a value for the required attribute: ') + attr);
                                        validation_failed = true;
                                        return;
                                    }
    
                                   
                                    let isChecked = dialog.get_value(`check_${attr}`);
                                    if ((isChecked || isChecked === undefined) && value) {
                                        selected_attributes[attr] = value;
                                    }
                                });
    
                                if (validation_failed) {
                                    return;
                                }
                                frappe.call({
                                    method: 'inhouse.inhouse.controllers.item.generate_item_name',
                                    args: {
                                        template_item: frm.doc.template_item,
                                        selected_attributes: selected_attributes
                                    },
                                    callback: function(r) {
                                        if (r.message) {
                                            let generated_item_name = r.message.item_name;
                                    
                
    
                 
    
                                            attribute_names.forEach(attr => {
                                                let value = selected_attributes[attr]; 
                                                if (value) {
                                                    frappe.call({
                                                        method: 'inhouse.inhouse.controllers.item.fetch_attribute_data',
                                                        args: {
                                                            attribute: attr,
                                                            attribute_value: value,
                                                            template_item: frm.doc.template_item
                                                        },
                                                        callback: function(r) {
                                                            if (r.message) {
                                                                let variant_price = r.message.price;
                                            
                                                                frm.add_child('fetched_variant_attributes', {
                                                                    item: generated_item_name,
                                                                    template_item: frm.doc.template_item,
                                                                    variant_attribute: attr,
                                                                    attribute_value: value,
                                                                    attribute_price: variant_price,
                                                                    template_item_price: template_item_price
                                                                });
                                                                frm.refresh_field('fetched_variant_attributes');
                                                            }
                                                        }
                                                    });
                                                }
                                            });
                                            
                                
                                            frm.refresh_field('fetched_variant_attributes');
                                        }
                                    }
                                });
    
                                
    
                                frm.refresh_field('fetched_variant_attributes');
                                frm.toggle_display('fetched_variant_attributes', true);
                                frm.toggle_display('items_to_be_created', true);
                                dialog.hide();
                            },
                            primary_action_label: __('Apply')
                        });
    
                        dialog.show();
                    });
                }
            }
        });
    }
    
    
    function create_sales_order(frm) {
        frm.reload_doc().then(() => {
            let variant_attributes = frm.doc.fetched_variant_attributes || [];
            let attributes_data = [];
            variant_attributes.forEach(function(attribute) {
                attributes_data.push({
                    'item': attribute.item,
                    'variant_attribute': attribute.variant_attribute,
                    'attribute_value': attribute.attribute_value
                });
            });
            
            let items_data = [];
            frm.doc.items_to_be_created.forEach(function(item_row) {
                items_data.push({
                    'name': item_row.item,
                    'rate': item_row.price
                });
            });
    
            frappe.model.open_mapped_doc({
                method: "inhouse.inhouse.controllers.sales_order.create_sales_order",  
                frm: frm, 
                args: {
                    "customer": frm.doc.customer,
                    "item_name": frm.doc.name,
                    "variant_attributes": attributes_data,
                    "items_to_be_created": items_data 
                }
            });
        });
    }