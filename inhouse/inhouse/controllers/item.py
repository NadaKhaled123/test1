import frappe
from frappe import _


@frappe.whitelist()
def set_template_item_name(template_item):
    if not template_item:
        frappe.throw(_('Template Item Is Required to fetch its Name'))
    
    return  frappe.db.get_value("Item",template_item, "item_name")

@frappe.whitelist()
def get_template_attributes(template_item):
    if not template_item:
        frappe.throw(_("Template Item is required"))

    attributes_data = frappe.get_all(
        "Template Item Attribute",
        filters={"parent": template_item},
        fields=["attribute_name", "idx"], 
        order_by="idx"  
    )

    unique_attributes = []
    seen = set()
    for attribute in attributes_data:
        attribute_name = attribute["attribute_name"]
        if attribute_name not in seen:
            seen.add(attribute_name)
            unique_attributes.append({"attribute_name": attribute_name, "idx": attribute["idx"]})
    # frappe.throw(str(unique_attributes))

    return unique_attributes



@frappe.whitelist()
def get_attribute_values(attribute, template_item):
    if not attribute or not template_item:
        frappe.throw(_("Attribute and Template Item are required"))

    attributes_data = frappe.get_all(
        "Template Item Attribute",
        filters={"parent": template_item, "attribute_name": attribute},
        fields=["attribute_value"],
        order_by="idx asc"
    )

    values = [data["attribute_value"] for data in attributes_data]
    return values

@frappe.whitelist()
def fetch_attribute_data(attribute, attribute_value, template_item):
    attributes_data = frappe.get_all(
        "Template Item Attribute",
        filters={
            "parent": template_item,
            "attribute_name": attribute,
            "attribute_value": attribute_value
        },
        fields=["price"]
    )

    if not attributes_data:
        frappe.throw(_("No price found for the selected attribute value"))

    return {"price": attributes_data[0].get("price")}




@frappe.whitelist()
def get_template_item_price(template_item):
    
    if template_item:
        
        price = frappe.db.get_value("Item",template_item,"custom_template_item_price_")
        if price:
            return price


 


@frappe.whitelist()
def create_item_and_pricing():
    pass


@frappe.whitelist()
def check_template_required_values(template_item, attribute):
    template_doc = frappe.get_doc("Item", template_item)
    for row in template_doc.attributes:
        if row.attribute == attribute and row.custom_required_template_value:
            return row.custom_required_template_value
    return None

@frappe.whitelist()
def check_attribute_required(attribute, template_item):

    is_required = frappe.db.get_value(
        "Template Item Attribute",
        {"parent": template_item, "attribute_name": attribute},
        "required"
    )
    return {"required": bool(is_required)}

import json

@frappe.whitelist()
def generate_item_name(template_item, selected_attributes):
    if isinstance(selected_attributes, str):
        try:
            selected_attributes = json.loads(selected_attributes)
        except json.JSONDecodeError:
            frappe.throw(_("selected_attributes is not a valid JSON string."))

    if not isinstance(selected_attributes, dict):
        frappe.throw(_("selected_attributes is still not a dictionary after deserialization."))

    frappe.log_error(message=selected_attributes, title="Selected Attributes Received")
    
    attribute_values = []
    for attribute, value in selected_attributes.items():

        attribute_name = frappe.db.get_value(
            "Item Attribute Value",
            {"abbr": value, "parent": attribute},
            "attribute_value"
        )

        if not attribute_name:
            frappe.throw(_("Could not find the full attribute name for abbreviation '{}' in attribute '{}'.").format(value, attribute))

        attribute_values.append(attribute_name)

    item_name = f"{template_item} - {' - '.join(attribute_values)}"

    return {"item_name": item_name}

# @frappe.whitelist()
# def get_attribute_values_by_parent(parent_attribute):
#     return frappe.db.sql("""
#         SELECT  abbr
#         FROM `tabItem Attribute Value`
#         WHERE parent= %s
#     """, parent_attribute, as_dict=True)
