// frappe.ui.form.on('Template Item Attribute', {
//     attribute_name: function(frm, cdt, cdn) {
//         // Get the current row in the child table
//         let row = locals[cdt][cdn];

//         frappe.call({
//             method: 'frappe.client.get_list',
//             args: {
//                 doctype: 'Item Attribute Value',
//                 filters: {
//                     'parent': row.attribute_name,
//                 },
//                 fields: ['name', 'abbreviation'], // Load only required fields
//                 ignore_permissions: true  // Add this to ignore permission checks
//             },
//             callback: function(r) {
//                 if (r.message) {
//                     let attribute_values = r.message.map(d => {
//                         return {
//                             'value': d.name, // Use the 'name' as the value
//                             'label': d.abbreviation // Display the abbreviation as label
//                         };
//                     });
        
//                     row.attribute_value = undefined; // Clear the existing value
//                     row.attribute_value_options = attribute_values; // Set new options
//                     frm.refresh_field('template_item_attribute'); // Refresh the field to show updated options
//                 }
//             }
//         });
        
//     },
// // });


// frappe.utils.filter_dict(cur_frm.fields_dict["Template Item Attribute"].grid.grid_rows_by_docname[cdn].docfields, { "attribute_value": "attribute_value" })[0].options = ["1","2","3"];
// cur_frm.refresh();
frappe.ui.form.on('Template Item Attribute', {
    attribute_name: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn]; // Current row in the child table

        if (row.attribute_name) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Item Attribute',
                    name: row.attribute_name
                },
                callback: function (r) {
                    if (r.message && r.message.item_attribute_values) {
                        let options = r.message.item_attribute_values.map(value => value.abbr);
                        console.log('Options:', options);

                        // Ensure grid and field exist
                        if (frm.fields_dict.custom_template_item_attributes_ && frm.fields_dict.custom_template_item_attributes_.grid) {
                            frm.fields_dict.custom_template_item_attributes_.grid.update_docfield_property(
                                'attribute_value',
                                'options',         
                                [''].concat(options) // New options (prepended with an empty value)
                            );

                            // frappe.model.set_value(cdt, cdn, 'attribute_value', options[0] || '');
                        } else {
                            console.error("Grid or field 'custom_template_item_attributes_' not found");
                        }
                    }
                },
                error: function (err) {
                    console.error('Error fetching Item Attribute:', err);
                }
            });
        } else {
            if (frm.fields_dict.custom_template_item_attributes_ && frm.fields_dict.custom_template_item_attributes_.grid) {
                frm.fields_dict.custom_template_item_attributes_.grid.update_docfield_property(
                    'attribute_value',
                    'options',
                    [''] // Empty options
                );

                frappe.model.set_value(cdt, cdn, 'attribute_value', '');
            } else {
                console.error("Grid or field 'custom_template_item_attributes_' not found");
            }
        }
    }
});

// let row = locals[cdt][cdn];
// frappe.model.set_value(cdt, cdn, "owner1", null);


// frm.set_query("owner1",function(doc) {
//     var row = locals[cdt][cdn];
    
//     return {
//         filters: {
//             "unit":["in",[row.unit]]
//         }
//     };
// function setupAttributeValueFilter(frm, cdt, cdn) {
//     let row = locals[cdt][cdn];

//     // Clear the attribute_value field whenever the attribute_name changes
//     frappe.model.set_value(cdt, cdn, "attribute_value", null);

//     // Set query for the 'attribute_value' field in the child table
//     frm.fields_dict['template_item_attribute'].grid.get_field('attribute_value').get_query = function(doc, cdt, cdn) {
//         return {
//             filters: {
//                 "parent": row.attribute_name // Filter where parent equals the selected attribute_name
//             }
//         };
//     };
// }

// frappe.ui.form.on('Template Item Attribute', {
//     attribute_name: function(frm, cdt, cdn) {
//         setupAttributeValueFilter(frm, cdt, cdn); // Apply the filter when the attribute_name field is changed
//     }
// });

