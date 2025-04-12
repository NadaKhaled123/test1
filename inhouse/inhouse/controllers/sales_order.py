from erpnext.controllers.item_variant import get_variant
import frappe
from frappe.model.document import Document
from frappe import _
import json
from inhouse.inhouse.utils import buy_more_bay_less, exchange_items



def validate(doc,event):
    buy_more_bay_less(doc)
    doc.calculate_taxes_and_totals()

def submit(doc,event):
    exchange_items(doc)
    doc.calculate_taxes_and_totals()


@frappe.whitelist()
def create_sales_order(source_name,target_doc=None):

    
    sales_order = frappe.new_doc('Sales Order')
    sales_order.custom_custom_item = frappe.flags.args.item_name
    
    sales_order.customer = frappe.flags.args.customer
    for row in frappe.flags.args.items_to_be_created:
        name=row.get('name')
        rate=row.get('rate')
    
        sales_order.append('items', {
            'item_code':name,
            'item_name': frappe.db.get_value("Item", {"name": name}, "item_name"),
            'qty': 1,  
            'rate': rate,
            'uom':  frappe.db.get_value("Item", {"name": name}, "stock_uom")
        })

    for attribute in frappe.flags.args.variant_attributes:
        sales_order.append('custom_item_attributes_', {
            'item': attribute['item'],
            'variant_attribute': attribute['variant_attribute'],
            'attribute_value': attribute['attribute_value'],
        })
    return sales_order



@frappe.whitelist()
def create_payment_entries(sales_order, payments):
    import json
    payments = json.loads(payments) if isinstance(payments, str) else payments

    # Fetch Sales Order details
    grand_total, advance_paid, customer, currency = frappe.db.get_value(
        'Sales Order', sales_order, ['grand_total', 'advance_paid', 'customer', 'currency']
    )

    # Calculate the remaining amount to be paid
    remaining_amount = grand_total - advance_paid

    # Fetch default company and base currency
    default_company = frappe.get_single('Global Defaults').default_company
    base_currency = frappe.db.get_value('Company', default_company, 'default_currency')

    # Fetch or set exchange rate
    if currency == base_currency:
        exchange_rate = 1  # Same currency, exchange rate is 1
    else:
        exchange_rate = frappe.db.get_value(
            'Currency Exchange',
            {'from_currency': currency, 'to_currency': base_currency},
            'exchange_rate'
        )
        if not exchange_rate:
            frappe.throw(_('Exchange rate not found for {0} to {1}. Please set it in Currency Exchange.').format(currency, base_currency))

    total_paid = sum(float(payment.get('paid_amount', 0)) for payment in payments)
    if total_paid > remaining_amount:
        frappe.throw(_('Total Paid Amount ({0}) exceeds the Remaining Amount ({1}).').format(total_paid, remaining_amount))

    payment_entries = []
    for payment in payments:
        mode_of_payment = payment.get('mode_of_payment')
        account_paid_to = frappe.db.get_value(
            'Mode of Payment Account',
            {'parent': mode_of_payment, 'company': default_company},
            'default_account'
        )
        if not account_paid_to:
            frappe.throw(_('No default account found for Mode of Payment {0} in Company {1}.').format(mode_of_payment, default_company))

        pe = frappe.new_doc('Payment Entry')
        pe.payment_type = 'Receive'
        pe.party_type = 'Customer'
        pe.party = customer
        pe.mode_of_payment = mode_of_payment
        pe.paid_amount = payment.get('paid_amount')
        pe.received_amount = payment.get('paid_amount')
        pe.paid_to = account_paid_to  # Set the "Account Paid To"
        pe.reference_no = 'Quick Payment'
        pe.reference_date = frappe.utils.today()
        pe.target_exchange_rate = exchange_rate  # Set the exchange rate
        pe.source_exchange_rate = exchange_rate  # Set the exchange rate

        pe.append('references', {
            'reference_doctype': 'Sales Order',
            'reference_name': sales_order,
            'allocated_amount': payment.get('paid_amount')
        })

        pe.insert()
        pe.submit()
        payment_entries.append(pe.name)

    return payment_entries





@frappe.whitelist()
def fetch_work_order_status(sales_order_name):
    """
    Fetch the related work orders for the given sales order, calculate the completion percentage,
    and update the work_order_status field in the Sales Order.
    """
    if not sales_order_name:
        frappe.throw(_("Sales Order name is required"))

    work_orders = frappe.get_all(
        "Work Order",
        filters={"sales_order": sales_order_name},
        fields=["name", "status"]
    )

    total_work_orders = len(work_orders)
    if total_work_orders > 0:
        completed_work_orders = sum(1 for wo in work_orders if wo.status == "Completed")
        completion_percentage = (completed_work_orders / total_work_orders) * 100
        frappe.db.set_value(
            "Sales Order",
            sales_order_name,
            "work_order_status",
            completion_percentage
        )

    


@frappe.whitelist()
def get_work_orders(sales_order_name):
    """
    Fetch the related work orders for the given sales order, calculate the completion percentage,
    and update the work_order_status field in the Sales Order.
    """
    if not sales_order_name:
        return

    user = frappe.session.user
    roles = frappe.get_roles(user)
    # frappe.throw(str(roles))

    if  "System Manager" in roles:
        return 0

    else: 
        work_orders = frappe.get_all(
        "Work Order",
        filters={"sales_order": sales_order_name},
        fields=["name", "status"]
        )

        return len(work_orders)




@frappe.whitelist()
def get_template_item_attributes(template_item):
    attributes = frappe.get_all("Item Variant Attribute",
                                filters={"parent": template_item},
                                fields=["attribute", "idx"],
                                order_by="idx asc") 

    for attr in attributes:
        attr_values = frappe.get_all("Item Attribute Value",
                                     filters={"parent": attr["attribute"]},
                                     fields=["abbr"],
                                     order_by="idx asc") 
        attr["values"] = [v["abbr"] for v in attr_values]

    return attributes


@frappe.whitelist()
def get_template_item_attributes_as_array_of_objects(template_item):
    """
    Fetch template item attributes as an array of objects.

    Args:
        item (str): The template item code.

    Returns:
        list: A list of dictionaries representing the attributes.
    """
    template_doc = frappe.get_doc("Item", template_item)
    organized_attributes = organize_template_attributes(template_doc)
    return [
        {"attribute": key, "values": list(value.keys())}
        for key, value in organized_attributes.items()
    ]


@frappe.whitelist()
def find_variant(template_item, selected_attributes):
    if isinstance(selected_attributes, str):
        try:
            selected_attributes = json.loads(selected_attributes)
        except json.JSONDecodeError:
            frappe.throw("Invalid JSON format for selected_attributes")

    if not isinstance(selected_attributes, dict):
        frappe.throw("selected_attributes must be a dictionary")
    return get_variant(
        template=template_item,
        args=selected_attributes,
    )
    

def organize_template_attributes(item):
    """
    Organize custom_template_item_attributes_ into a dictionary of dictionaries.

    Args:
        item (str): The item code of the template item.

    Returns:
        dict: A dictionary where the key is the attribute name, and the value is another dictionary
        with attribute value as the key and price as the value.
    """
    # Fetch the Item document
    item_doc = frappe.get_doc("Item", item) if isinstance(item, str) else item

    # Access the custom child table
    template_item_attributes = item_doc.get(
        "custom_template_item_attributes_")  # Replace with actual fieldname

    # Organize into a dictionary of dictionaries
    attributes_dict = {}
    for row in template_item_attributes:

        if row.attribute_name not in attributes_dict:
            attributes_dict[row.attribute_name] = {}
        if attributes_dict[row.attribute_name].get(row.attribute_value):
            continue
        attributes_dict[row.attribute_name][row.attribute_value] = row

    return attributes_dict




@frappe.whitelist()
def get_item_price(variant, price_list):
    # item_code = frappe.db.get_value("Item", variant, "item_code")
    # frappe.throw(str(price_list))
    
    price_data = frappe.db.get_value("Item Price", 
                                     {"item_code": variant, "price_list": price_list}, 
                                     "price_list_rate", as_dict=True)
    # frappe.throw(str(price_data))
    
    if price_data:
        return price_data.price_list_rate
    return None


@frappe.whitelist()
def get_item_name(variant):
    item_name = frappe.db.get_value("Item", variant, "item_name")
    return item_name


@frappe.whitelist()
def get_uom(variant):
    uom = frappe.db.get_value("Item", {"name": variant}, "stock_uom")
    return uom
