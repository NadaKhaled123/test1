import frappe
import json
from frappe.utils import add_days, flt,cint
from erpnext.stock.get_item_details import(
    process_args,
    process_string_args,
    validate_item_details,
    get_basic_details,
    get_item_tax_template,
    get_party_item_code,
    get_item_tax_map,
    set_valuation_rate,
    update_party_blanket_order,
    get_pos_profile_item_details,
    get_price_list_rate,
    remove_standard_fields,
    get_gross_profit,
    get_default_bom,
    update_stock,
    update_bin_details
)

from erpnext.accounts.doctype.pricing_rule.pricing_rule import (
remove_pricing_rule_for_item,
update_args_for_pricing_rule,
get_pricing_rule_details,
apply_price_discount_rule
)
from erpnext.setup.doctype.item_group.item_group import get_child_item_groups

apply_on_table = {"Item Code": "items", "Item Group": "item_groups", "Brand": "brands"}
 
@frappe.whitelist()
def custom_get_item_details(args, doc=None, for_validate=False, overwrite_warehouse=True):
    # frappe.throw(str("jbj"))
    """
    args = {
            "item_code": "",
            "warehouse": None,
            "customer": "",
            "conversion_rate": 1.0,
            "selling_price_list": None,
            "price_list_currency": None,
            "plc_conversion_rate": 1.0,
            "doctype": "",
            "name": "",
            "supplier": None,
            "transaction_date": None,
            "conversion_rate": 1.0,
            "buying_price_list": None,
            "is_subcontracted": 0/1,
            "ignore_pricing_rule": 0/1
            "project": ""
            "set_warehouse": ""
    }
    """
    
    args = process_args(args)
    for_validate = process_string_args(for_validate)
    overwrite_warehouse = process_string_args(overwrite_warehouse)
    item = frappe.get_cached_doc("Item", args.item_code)
    validate_item_details(args, item)

    if isinstance(doc, str):
        doc = json.loads(doc)

    if doc:
        args["transaction_date"] = doc.get("transaction_date") or doc.get("posting_date")

        if doc.get("doctype") == "Purchase Invoice":
            args["bill_date"] = doc.get("bill_date")

    out = get_basic_details(args, item, overwrite_warehouse)

    get_item_tax_template(args, item, out)
    out["item_tax_rate"] = get_item_tax_map(
        args.company,
        args.get("item_tax_template")
        if out.get("item_tax_template") is None
        else out.get("item_tax_template"),
        as_json=True,
    )

    get_party_item_code(args, item, out)

    if args.get("doctype") in ["Sales Order", "Quotation"]:
        set_valuation_rate(out, args)

    update_party_blanket_order(args, out)

    # Never try to find a customer price if customer is set in these Doctype
    current_customer = args.customer
    if args.get("doctype") in ["Purchase Order", "Purchase Receipt", "Purchase Invoice"]:
        args.customer = None

    out.update(get_price_list_rate(args, item))

    args.customer = current_customer

    if args.customer and cint(args.is_pos):
        out.update(get_pos_profile_item_details(args.company, args, update_data=True))

    if item.is_stock_item:
        update_bin_details(args, out, doc)

    # update args with out, if key or value not exists
    for key, value in out.items():
        if args.get(key) is None:
            args[key] = value

    data = get_pricing_rule_for_item(args, doc=doc, for_validate=for_validate)

    out.update(data)

    update_stock(args, out)

    if args.transaction_date and item.lead_time_days:
        out.schedule_date = out.lead_time_date = add_days(args.transaction_date, item.lead_time_days)

    if args.get("is_subcontracted"):
        out.bom = args.get("bom") or get_default_bom(args.item_code)

    get_gross_profit(out)
    if args.doctype == "Material Request":
        out.rate = args.rate or out.price_list_rate
        out.amount = flt(args.qty) * flt(out.rate)

    out = remove_standard_fields(out)
    return out




def get_pricing_rule_for_item(args, doc=None, for_validate=False):
    from erpnext.accounts.doctype.pricing_rule.utils import (
        get_applied_pricing_rules,
        get_pricing_rules,
        get_product_discount_rule,
    )

    if isinstance(doc, str):
        doc = json.loads(doc)

    if doc:
        doc = frappe.get_doc(doc)

    if args.get("is_free_item") or args.get("parenttype") == "Material Request":
        return {}

    item_details = frappe._dict(
        {
            "doctype": args.doctype,
            "has_margin": False,
            "name": args.name,
            "free_item_data": [],
            "parent": args.parent,
            "parenttype": args.parenttype,
            "child_docname": args.get("child_docname"),
            "discount_percentage": 0.0,
            "discount_amount": 0,
        }
    )

    if args.ignore_pricing_rule or not args.item_code:
        if frappe.db.exists(args.doctype, args.name) and args.get("pricing_rules"):
            item_details = remove_pricing_rule_for_item(
                args.get("pricing_rules"),
                item_details,
                item_code=args.get("item_code"),
                rate=args.get("price_list_rate"),
            )
        return item_details
    

    update_args_for_pricing_rule(args)


    pricing_rules = (
        get_applied_pricing_rules(args.get("pricing_rules"))
        if for_validate and args.get("pricing_rules")
        else get_pricing_rules(args, doc)
    )



    if pricing_rules:
        rules = []

        for pricing_rule in pricing_rules:

            if not pricing_rule:
                continue



            if isinstance(pricing_rule, str):

                pricing_rule = frappe.get_cached_doc("Pricing Rule", pricing_rule)
                update_pricing_rule_uom(pricing_rule, args)
                # frappe.throw(str(pricing_rule))

                fetch_other_item = True if pricing_rule.apply_rule_on_other else False
                pricing_rule.apply_rule_on_other_items = (
                    get_pricing_rule_items(pricing_rule, other_items=fetch_other_item) or []
                    )


            if pricing_rule.coupon_code_based == 1:
                if not args.coupon_code:
                    return item_details

                coupon_code = frappe.db.get_value(
                    doctype="Coupon Code", filters={"pricing_rule": pricing_rule.name}, fieldname="name"
                )
                if args.coupon_code != coupon_code:
                    continue

            if pricing_rule.get("suggestion"):
                continue

            item_details.validate_applied_rule = pricing_rule.get("validate_applied_rule", 0)
            item_details.price_or_product_discount = pricing_rule.get("price_or_product_discount")

            rules.append(get_pricing_rule_details(args, pricing_rule))
            # frappe.throw(str(rules))


            if pricing_rule.mixed_conditions or pricing_rule.apply_rule_on_other:
                item_details.update(
                    {
                        "price_or_product_discount": pricing_rule.price_or_product_discount,
                        "apply_rule_on": (
                            frappe.scrub(pricing_rule.apply_rule_on_other)
                            if pricing_rule.apply_rule_on_other
                            else frappe.scrub(pricing_rule.get("apply_on"))
                        ),
                    }
                )

                if pricing_rule.apply_rule_on_other_items:
                    item_details["apply_rule_on_other_items"] = json.dumps(
                        pricing_rule.apply_rule_on_other_items
                    )

            if not pricing_rule.validate_applied_rule:
                if pricing_rule.price_or_product_discount == "Price":
                    apply_price_discount_rule(pricing_rule, item_details, args)
                else:
                    get_product_discount_rule(pricing_rule, item_details, args, doc)

        if not item_details.get("has_margin"):
            item_details.margin_type = None
            item_details.margin_rate_or_amount = 0.0

        item_details.has_pricing_rule = 1

        item_details.pricing_rules = frappe.as_json([d.pricing_rule for d in rules])

        if not doc:
            return item_details

    elif args.get("pricing_rules"):
        item_details = remove_pricing_rule_for_item(
            args.get("pricing_rules"),
            item_details,
            item_code=args.get("item_code"),
            rate=args.get("price_list_rate"),
        )

    
    return item_details



def get_pricing_rule_items(pr_doc, other_items=False) -> list:
    apply_on_data = []
    apply_on = frappe.scrub(pr_doc.get("apply_on"))

    pricing_rule_apply_on = apply_on_table.get(pr_doc.get("apply_on"))

    if pr_doc.apply_rule_on_other and other_items:
        apply_on = frappe.scrub(pr_doc.apply_rule_on_other)
        apply_on_data.append(pr_doc.get("other_" + apply_on))
    else:

        if not pr_doc.get(pricing_rule_apply_on):
            return
        
        for d in pr_doc.get(pricing_rule_apply_on):
            if apply_on == "item_group":
                apply_on_data.extend(get_child_item_groups(d.get(apply_on)))
            else:
                apply_on_data.append(d.get(apply_on))

    return list(set(apply_on_data))


def update_pricing_rule_uom(pricing_rule, args):

    child_doc = {"Item Code": "items", "Item Group": "item_groups", "Brand": "brands"}.get(
        pricing_rule.apply_on
    )

    apply_on_field = frappe.scrub(pricing_rule.apply_on)
    
    if not pricing_rule.get(child_doc):
        return

    for row in pricing_rule.get(child_doc):
        if row.get(apply_on_field) == args.get(apply_on_field):
            pricing_rule.uom = row.uom

