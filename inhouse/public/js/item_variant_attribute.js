frappe.ui.form.on('Item Variant Attribute', {
    attribute: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.attribute) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "Item Attribute",
                    filters: { parent: row.attribute },
                    fields: ["attribute_value", "abbr"]
                },
                callback: function (r) {
                    if (r.message) {
                        let options = r.message.map(d => `${d.attribute_value} (${d.abbr || ''})`).join('\n');

                        frappe.meta.get_docfield("Item Attribute Table", "custom_required_template_value", frm.docname).options = options;

                        frm.refresh_field("attributes");
                    }
                }
            });
        } else {
            frappe.meta.get_docfield("Item Variant Attribute", "custom_required_template_value", frm.docname).options = "";
            frm.refresh_field("attributes");
        }
    }
});
