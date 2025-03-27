# Copyright (c) 2024, inhouse and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class ItemCreationAndPricing(Document):
    def before_save(self):
        total_amount = 0

        for row in self.fetched_variant_attributes:
            if row.attribute_price and row.qty:
                row.amount = row.attribute_price * row.qty
            else:
                row.amount = 0

            total_amount += row.amount

        if self.template_item_price:
            total_amount += self.template_item_price

        self.total_item_price = total_amount

    def on_submit(self):
        self.generate_item()
        self.generate_item_price()
        
        

    def generate_item(self):
        frappe.throw(str(frappe.db.get_value("Item", self.template_item, "stock_uom")))
        if not self.template_item:
            frappe.throw(_("Template item is required to generate a new item."))

        attributes = []
        attribute_values = []

        for row in self.fetched_variant_attributes:
            if not (row.variant_attribute and row.attribute_value):
                continue

            attribute_name = frappe.db.get_value(
                "Item Attribute Value",
                {"abbr": row.attribute_value, "parent": row.variant_attribute},
                "attribute_value"
            )

            if not attribute_name:
                frappe.throw(_("Could not find the full attribute name for abbreviation '{}' in attribute '{}'.").format(
                    row.attribute_value, row.variant_attribute))

            attributes.append({
                "attribute": row.variant_attribute,
                "attribute_value": attribute_name
            })
            attribute_values.append(attribute_name)

        item_name = f"{self.template_item} - {' - '.join(attribute_values)}"

        existing_item = frappe.db.exists("Item", {"item_name": item_name})
        if existing_item:
            frappe.msgprint(_("Item '{}' already exists.").format(item_name))
            return
        

        item_doc = frappe.get_doc({
            "doctype": "Item",
            "item_code": item_name,
            "item_name": item_name,
            "variant_of": self.template_item,
            "item_group": frappe.db.get_value("Item", self.template_item, "item_group"),
            "attributes": attributes,
            "is_stock_item": 1,  
            "stock_uom" :  frappe.db.get_value("Item", self.template_item, "stock_uom"),
        })

        item_doc.insert(ignore_permissions=True)
        
        frappe.db.set_value("Item Customization",self.name,"item_name",item_name)
        frappe.db.commit()
        frappe.msgprint(_("Item '{}' has been created successfully with all attributes.").format(item_name))

    def generate_item_price(self):
        if not self.total_item_price or self.total_item_price <= 0:
            frappe.throw(_("Total item price is required and must be greater than zero to generate an Item Price."))

        attribute_values = [
            frappe.db.get_value(
                "Item Attribute Value",
                {"abbr": row.attribute_value, "parent": row.variant_attribute},
                "attribute_value"
            ) for row in self.fetched_variant_attributes if row.variant_attribute and row.attribute_value
        ]

        item_name = f"{self.template_item} - {' - '.join(attribute_values)}"

        existing_item = frappe.db.exists("Item", {"item_name": item_name})
        if not existing_item:
            frappe.throw(_("Item '{}' does not exist. Please ensure the item has been created.").format(item_name))

        existing_price = frappe.db.exists("Item Price", {"item_code": item_name})
        if existing_price:
            frappe.msgprint(_("Item Price already exists for '{}'. No new Item Price was created.").format(item_name))
            return

        item_price_doc = frappe.get_doc({
            "doctype": "Item Price",
            "item_code": item_name,
            "item_group": frappe.db.get_value("Item", self.template_item, "item_group"),
            "price_list": self.price_list,  
            "price_list_rate": self.total_item_price  
        })

        item_price_doc.insert(ignore_permissions=True)
        frappe.msgprint(_("Item Price for '{}' has been created successfully with rate {}.").format(item_name, self.total_item_price))
