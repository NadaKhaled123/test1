import frappe
from frappe import _
from inhouse.utils import buy_more_bay_less, exchange_items

def validate(doc,event):
    buy_more_bay_less(doc)
    doc.calculate_taxes_and_totals()

def submit(doc,event):
    exchange_items(doc)
    doc.calculate_taxes_and_totals()


def validate_sales_order_advance_paid(doc, method):
    for row in doc.items:
        if row.against_sales_order:
            sales_order = frappe.db.get_value('Sales Order', row.against_sales_order,["advance_paid","rounded_total"],as_dict=True)
            percent = (sales_order.get("advance_paid") / sales_order.get("rounded_total")) * 100

            if percent < 100:
                frappe.throw(_(f"Can't submit this document as advance paid percentage is {round(percent,3)} for the sales order {row.against_sales_order}"))

     
     
