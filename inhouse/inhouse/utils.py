import frappe


def buy_more_bay_less(doc):
    """
    Applies discounts based on the "Buy More Bay Less" offer:
    - ALL selected items in the invoice must match the offer items or belong to the specified item groups.
    - If any item does not match, remove all discounts and reset rates to the price list rate.
    - If all items match, highest-priced item gets 0% discount, second highest gets the lowest discount, etc.
    """

    offers = frappe.get_all(
        "Offers", 
        filters={"buy_more_bay_less_offer": 1}, 
        fields=["name", "creation"], 
        order_by="creation DESC"
    )

    for offer in offers:
        offer_doc = frappe.get_doc("Offers", offer.name)

        offer_items = {item.item for item in offer_doc.buy_more_bay_less_items}
        offer_groups = {group.item_group for group in offer_doc.buy_more_bay_less_item_group}
        offer_discounts = sorted([discount.discount for discount in offer_doc.buy_more_bay_less_discounts])

        if not offer_items and not offer_groups:
            continue  

        matched_items = []
        for item in doc.items:
            item_group = frappe.get_value("Item", item.item_code, "item_group")
            if item.item_code in offer_items or item_group in offer_groups:
                matched_items.append({"item_code": item.item_code, "rate": item.price_list_rate, "doc_item": item})

        if not len(matched_items):
            for item in doc.items:
                item.offers_discount = 0
                item.discount_percentage = 0
                item.rate = item.price_list_rate
                item.base_rate = item.price_list_rate
                item.amount = item.price_list_rate * item.qty
                item.base_amount = item.price_list_rate * item.qty
                item.net_rate = item.price_list_rate
                item.base_net_rate = item.price_list_rate
                item.net_amount = item.price_list_rate * item.qty
                item.base_net_amount = item.price_list_rate * item.qty
            return 

        matched_items.sort(key=lambda x: x["rate"], reverse=True)  
        total_discount_amount = 0

        for i, item in enumerate(matched_items):
            discount = 0 if i == 0 else offer_discounts.pop(0) if offer_discounts else 0  
            item["doc_item"].offers_discount = discount 
            total_discount = item["doc_item"].discount_percentage + discount
            discounted_rate = item["rate"] - (item["rate"] * (total_discount / 100))

            item["doc_item"].rate = discounted_rate
            item["doc_item"].base_rate = discounted_rate
            item["doc_item"].amount = discounted_rate * item["doc_item"].qty
            item["doc_item"].base_amount = discounted_rate * item["doc_item"].qty
            item["doc_item"].net_rate = discounted_rate
            item["doc_item"].base_net_rate = discounted_rate
            item["doc_item"].net_amount = discounted_rate * item["doc_item"].qty
            item["doc_item"].base_net_amount = discounted_rate * item["doc_item"].qty
            total_discount_amount += (item["rate"] - discounted_rate) * item["doc_item"].qty

        break 

def exchange_items(doc):
        
        if not doc.is_exchange:
            return
        
        # frappe.throw(str("matched_items"))


        offers = frappe.get_all(
        "Offers", 
        filters={"exchange_offer": 1}, 
        fields=["name", "creation"], 
        order_by="creation DESC"
                )
        for offer in offers:
            offer_doc = frappe.get_doc("Offers", offer.name)

            offer_items = {item.item for item in offer_doc.exchange_items}
            offer_groups = {group.item_group for group in offer_doc.exchange_group}

            if not offer_items and not offer_groups:
                continue  

            matched_items = []
            for item in doc.items:
                item_group = frappe.get_value("Item", item.item_code, "item_group")
                if item.item_code in offer_items or item_group in offer_groups:
                    matched_items.append({"item_code": item.item_code, "rate": item.price_list_rate, "doc_item": item,"discount":offer_doc.discount})

            if len(matched_items) and doc.doctype == "Sales Invoice":
                create_stock_entry(doc.set_warehouse,offer_doc.exchange_item)

            total_discount_amount = 0
            for item in matched_items:

                item["doc_item"].exchange_discount = item["discount"] 
                total_discount = item["doc_item"].discount_percentage + item["discount"] + item["doc_item"].offers_discount 
                item["doc_item"].offer_discount =  item["discount"] + item["doc_item"].offers_discount 
                discounted_rate = item["rate"] - (item["rate"] * (total_discount / 100))
                item["doc_item"].rate = discounted_rate
                item["doc_item"].base_rate = discounted_rate
                item["doc_item"].amount = discounted_rate * item["doc_item"].qty
                item["doc_item"].base_amount = discounted_rate * item["doc_item"].qty
                item["doc_item"].net_rate = discounted_rate
                item["doc_item"].base_net_rate = discounted_rate
                item["doc_item"].net_amount = discounted_rate * item["doc_item"].qty
                item["doc_item"].base_net_amount = discounted_rate * item["doc_item"].qty
            break

def create_stock_entry(warehouse,item):
    se = frappe.new_doc("Stock Entry")
    se.stock_entry_type = "Material Receipt"
    se.append("items",
            {"t_warehouse":warehouse,
             "item_code": item,
             "qty": 1,
             "allow_zero_valuation_rate": 1
             
             }) 
    
    se.insert()
    se.submit()

