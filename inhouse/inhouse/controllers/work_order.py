import frappe
from frappe import _

def add_custom_attributes(doc, method):
    if doc.sales_order:
        sales_order = frappe.get_doc('Sales Order', doc.sales_order)

        for attribute in sales_order.custom_item_attributes_:
            doc.append('custom_item_attributes_', {
                'variant_attribute': attribute.variant_attribute,
                'attribute_value': attribute.attribute_value,
            })

        doc.save()


def get_item_details(doc, method):
    item_template_name = ""
    barcode = ""
    item_group = frappe.db.get_value("Item",doc.production_item,"item_group")
    barcodes = frappe.get_all("Item Barcode",filters={"parenttype":"Item","parent":doc.production_item},pluck='barcode')

    if len(barcodes):
        barcode = barcodes[0]

    variants = frappe.get_all("Item Customization Items",filters={"parenttype":"Item Customization","item":doc.item_name},pluck='parent')

    if len(variants):
        item_template_name = frappe.db.get_value("Item Customization",variants[0],"template_item_name")

    doc.item_group = item_group
    doc.item_template_name = item_template_name
    doc.barcode = barcode

# def validate_sales_order_advance_paid(doc, method):
#     if doc.sales_order:
#         sales_order = frappe.db.get_value('Sales Order', doc.sales_order,["advance_paid","rounded_total"],as_dict=True)
#         percent = (sales_order.get("advance_paid") / sales_order.get("rounded_total")) * 100

#         if percent < 50:
#             frappe.throw(_(f"Can't submit this document as advance paid percentage is {round(percent,3)} for the sales order {doc.sales_order}"))

     



def notify_work_order_created(doc,event):
    frappe.publish_realtime(
        event='work_order_created',
        message={'sales_order': doc.sales_order},
        after_commit=True
    )
    