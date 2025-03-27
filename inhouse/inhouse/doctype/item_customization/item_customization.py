# Copyright (c) 2024, inhouse and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class ItemCustomization(Document):
    def before_save(self):
        item_prices = self.compute_amount_for_rows()

        self.fetch_and_compute_total_price(item_prices)

    def compute_amount_for_rows(self):
        """
        Computes the amount for each row (qty * attribute_price) and returns a dictionary of
        item prices.
        """
        item_prices = {}

        for row in self.fetched_variant_attributes:
            if row.item not in item_prices:
                item_prices[row.item] = 0  

            if row.attribute_price and row.qty:
                amount = row.attribute_price * row.qty
            else:
                amount = 0
            row.amount = amount

            item_prices[row.item] += amount
        
        return item_prices

    def fetch_and_compute_total_price(self, item_prices):
        """
        Fetches the template item price for each unique item and computes the total price
        including the template price.
        """
        self.items_to_be_created = []
        
        for item, item_price in item_prices.items():
            template_item = None
            template_price = 0

            for row in self.fetched_variant_attributes:
                if row.item == item:
                    template_item = row.template_item
                    if template_item:
                        template_price = frappe.db.get_value("Item", template_item, "custom_template_item_price_") or 0

            total_item_price = item_price + template_price

            self.append("items_to_be_created", {
                "item": item,
                "price": total_item_price
            })



    def before_submit(self):
        for row in self.items_to_be_created:
            item = row.item
            item_price = row.price
            template_item = next((r.template_item for r in self.fetched_variant_attributes if r.item == item), None)
            
            if not template_item:
                frappe.throw(_("Template Item is required for validating item '{}'").format(item))
            
            existing_item = self.generate_item_for_unique_item(item)
            if existing_item:
                # item_name= frappe.db.get_value("Item",existing_item,"item_name")
                row.item = existing_item
                frappe.db.set_value("Item Customization Items", row.name, "item", existing_item)
                frappe.msgprint(_("Item '{}' already exists. Using the existing item.").format(existing_item))
            
            self.generate_item_price_for_unique_item(item, item_price)
        frappe.db.commit()


    @staticmethod
    def get_normalized_attributes(item_name):
        """
        Fetch and normalize the attributes of an existing item for comparison.
        This function directly retrieves:
        - Attributes and their values from the Item Variant Attribute table of the Item.
        """
        item_attributes = frappe.db.get_all(
            "Item Variant Attribute",  
            filters={"parent": item_name},
            fields=["attribute", "attribute_value"]
        )

        result = [(attr["attribute"], attr["attribute_value"]) for attr in item_attributes]

        return sorted(result)


    @staticmethod
    def is_item_existing(template_item, attributes):
        """
        Check if an item with the same attributes already exists.
        """
        normalized_attributes = sorted([(attr["attribute"], attr["attribute_value"]) for attr in attributes])

        existing_items = frappe.db.get_all(
            "Item",
            filters={"variant_of": template_item},
            fields=["name","item_name"]
        )

        for item in existing_items:
            existing_attributes = ItemCustomization.get_normalized_attributes(item["name"])

            if normalized_attributes == existing_attributes:
                return item["name"]
        return None

    def generate_item_for_unique_item(self, item):
        """
        Generate the item for the unique item by fetching its attributes and applying validations.
        """
        template_item = None
        attributes = []
        for row in self.fetched_variant_attributes:
            if row.item == item:
                template_item = row.template_item
                break
        
        for row in self.fetched_variant_attributes:
            if row.item == item and row.variant_attribute and row.attribute_value:
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

        existing_item = self.is_item_existing(template_item, attributes)
        if existing_item:
            
            return existing_item

        item_doc = frappe.get_doc({
            "doctype": "Item",
            "item_code": template_item + " - " + " - ".join([attr["attribute_value"] for attr in attributes]),
            "item_name": template_item + " - " + " - ".join([attr["attribute_value"] for attr in attributes]),
            "variant_of": template_item,
            "item_group": frappe.db.get_value("Item", template_item, "item_group"),
            "attributes": attributes,
            "stock_uom": frappe.db.get_value("Item", template_item, "stock_uom"),
            "is_stock_item": 1,
        })
        item_doc.insert(ignore_permissions=True)
        # frappe.throw(str(item_doc.name))

        # frappe.db.set_value("Item Customization", self.name, "item_name", item_doc.item_name)
        frappe.db.commit()
        frappe.msgprint(_("Item '{}' has been created successfully.").format(item_doc.item_name))
        return item_doc.name
        

    def generate_item_price_for_unique_item(self, item, item_price):

        """
        Generate item price for the unique item by applying validations and logic.
        """
        template_item = None
        for row in self.fetched_variant_attributes:
            if row.item == item:
                template_item = row.template_item
                break
        
        if not item_price or item_price <= 0:
            frappe.throw(_("Item price must be greater than zero to generate an Item Price."))

        attributes = []
        for row in self.fetched_variant_attributes:
            if row.item == item and row.variant_attribute and row.attribute_value:
                attribute_name = frappe.db.get_value(
                    "Item Attribute Value",
                    {"abbr": row.attribute_value, "parent": row.variant_attribute},
                    "attribute_value"
                )
                if not attribute_name:
                    frappe.throw(_("Could not find the full attribute value for abbreviation '{}' in attribute '{}'.").format(
                        row.attribute_value, row.variant_attribute))
                
                attributes.append({
                    "attribute": row.variant_attribute,
                    "attribute_value": attribute_name
                })

        existing_item = self.is_item_existing(template_item, attributes)
        if not existing_item:
            frappe.throw(_("No existing item matches the specified attributes. Ensure the item is generated first."))

        item_code = frappe.db.get_value("Item", {"name": existing_item}, "item_code")
        if not item_code:
            frappe.throw(_("Item code for '{}' not found.").format(existing_item))

        existing_price = frappe.db.get_value("Item Price", {"item_code": item_code}, "price_list_rate")
        existing_price_list = frappe.db.get_value("Item Price", {"item_code": item_code}, "price_list")

        if existing_price:
            if existing_price == item_price:
                frappe.msgprint(_("Item Price for '{}' already exists and is up-to-date.").format(existing_item))
            else:
                frappe.db.set_value("Item Price", {"item_code": item_code}, "price_list_rate", item_price)
                frappe.db.set_value("Item", item_code, "standard_rate", item_price)
                frappe.msgprint(_("Item Price for '{}' updated to {}.").format(existing_item, item_price))
        
        if existing_price_list:
            if existing_price_list == self.price_list:
                frappe.msgprint(_("Price List for '{}' already exists and is up-to-date.").format(existing_item))
            else:
                frappe.db.set_value("Item Price", {"item_code": item_code}, "price_list", self.price_list)
                frappe.msgprint(_("Price List for '{}' updated to {}.").format(existing_item, self.price_list))
        else:
            item_price_doc = frappe.get_doc({
                "doctype": "Item Price",
                "item_code": item_code,
                "price_list": self.price_list,
                "price_list_rate": item_price
            })
            item_price_doc.insert(ignore_permissions=True)
            frappe.db.set_value("Item", item_code, "standard_rate", item_price)
            frappe.msgprint(_("Item Price for '{}' created successfully at {}.").format(existing_item, item_price))