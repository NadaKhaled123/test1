# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from collections import defaultdict

import frappe
from frappe import _, bold, qb, throw
from frappe.model.workflow import get_workflow_name, is_transition_condition_satisfied
from frappe.query_builder import Criterion, DocType
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Abs, Sum
from frappe.utils import (
    add_days,
    add_months,
    cint,
    comma_and,
    flt,
    fmt_money,
    formatdate,
    get_last_day,
    get_link_to_form,
    getdate,
    nowdate,
    parse_json,
    today,
)

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    get_accounting_dimensions,
    get_dimensions,
)
from erpnext.accounts.doctype.pricing_rule.utils import (
    apply_pricing_rule_for_free_items,
    apply_pricing_rule_on_transaction,
    get_applied_pricing_rules,
)
from erpnext.accounts.general_ledger import get_round_off_account_and_cost_center
from erpnext.accounts.party import (
    get_party_account,
    get_party_account_currency,
    get_party_gle_currency,
    validate_party_frozen_disabled,
)
from erpnext.accounts.utils import (
    create_gain_loss_journal,
    get_account_currency,
    get_currency_precision,
    get_fiscal_years,
    validate_fiscal_year,
)
from erpnext.buying.utils import update_last_purchase_rate
from erpnext.controllers.print_settings import (
    set_print_templates_for_item_table,
    set_print_templates_for_taxes,
)
from erpnext.controllers.sales_and_purchase_return import validate_return
from erpnext.exceptions import InvalidCurrency
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.doctype.item.item import get_uom_conv_factor
from erpnext.stock.doctype.packed_item.packed_item import make_packing_list
from erpnext.stock.get_item_details import (
    _get_item_tax_template,
    get_conversion_factor,
    get_item_tax_map,
    get_item_warehouse,
)
from inhouse.override.get_item_details import  custom_get_item_details
from erpnext.utilities.regional import temporary_flag
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.controllers.accounts_controller import AccountsController

class AccountMissingError(frappe.ValidationError):
    pass


class InvalidQtyError(frappe.ValidationError):
    pass


force_item_fields = (
    "item_group",
    "brand",
    "stock_uom",
    "is_fixed_asset",
    "pricing_rules",
    "weight_per_unit",
    "weight_uom",
    "total_weight",
    "valuation_rate",
)


class CustomAccountsController(AccountsController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate(self):
        if not self.get("is_return") and not self.get("is_debit_note"):
            self.validate_qty_is_not_zero()

        if (
            self.doctype in ["Sales Invoice", "Purchase Invoice"]
            and self.get("is_return")
            and self.get("update_stock")
        ):
            self.validate_zero_qty_for_return_invoices_with_stock()

        # if self.get("_action") and self._action != "update_after_submit":
        # 	self.set_missing_values(for_validate=True)

        if self.get("_action") == "submit":
            self.remove_bundle_for_non_stock_invoices()

        self.ensure_supplier_is_not_blocked()

        self.validate_date_with_fiscal_year()
        self.validate_party_accounts()

        self.validate_inter_company_reference()

        self.disable_pricing_rule_on_internal_transfer()
        self.disable_tax_included_prices_for_internal_transfer()
        self.set_incoming_rate()
        self.init_internal_values()

        if self.meta.get_field("currency"):
            self.calculate_taxes_and_totals()

            if not self.meta.get_field("is_return") or not self.is_return:
                self.validate_value("base_grand_total", ">=", 0)

            validate_return(self)

        self.validate_all_documents_schedule()

        if self.meta.get_field("taxes_and_charges"):
            self.validate_enabled_taxes_and_charges()
            self.validate_tax_account_company()

        self.validate_party()
        self.validate_currency()
        self.validate_party_account_currency()
        self.validate_return_against_account()

        if self.doctype in ["Purchase Invoice", "Sales Invoice"]:
            if invalid_advances := [x for x in self.advances if not x.reference_type or not x.reference_name]:
                frappe.throw(
                    _(
                        "Rows: {0} in {1} section are Invalid. Reference Name should point to a valid Payment Entry or Journal Entry."
                    ).format(
                        frappe.bold(comma_and([x.idx for x in invalid_advances])),
                        frappe.bold(_("Advance Payments")),
                    )
                )

            if self.get("is_return") and self.get("return_against") and not self.get("is_pos"):
                if self.get("update_outstanding_for_self"):
                    document_type = "Credit Note" if self.doctype == "Sales Invoice" else "Debit Note"
                    frappe.msgprint(
                        _(
                            "We can see {0} is made against {1}. If you want {1}'s outstanding to be updated, uncheck '{2}' checkbox. <br><br> Or you can use {3} tool to reconcile against {1} later."
                        ).format(
                            frappe.bold(document_type),
                            get_link_to_form(self.doctype, self.get("return_against")),
                            frappe.bold(_("Update Outstanding for Self")),
                            get_link_to_form("Payment Reconciliation", "Payment Reconciliation"),
                        )
                    )

            pos_check_field = "is_pos" if self.doctype == "Sales Invoice" else "is_paid"
            if cint(self.allocate_advances_automatically) and not cint(self.get(pos_check_field)):
                self.set_advances()

            self.set_advance_gain_or_loss()

            if self.is_return:
                self.validate_qty()
            else:
                self.validate_deferred_start_and_end_date()

            self.validate_deferred_income_expense_account()
            self.set_inter_company_account()

        self.set_taxes_and_charges()

        if self.doctype == "Purchase Invoice":
            self.calculate_paid_amount()
            # apply tax withholding only if checked and applicable
            self.set_tax_withholding()

        with temporary_flag("company", self.company):
            validate_regional(self)
            validate_einvoice_fields(self)

        if self.doctype != "Material Request" and not self.ignore_pricing_rule:
            apply_pricing_rule_on_transaction(self)

        self.set_total_in_words()
        self.set_default_letter_head()
        self.validate_company_in_accounting_dimension()

        

    def set_missing_item_details(self, for_validate=False):
        """set missing item values"""
        from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

        if hasattr(self, "items"):
            parent_dict = {}
            for fieldname in self.meta.get_valid_columns():
                parent_dict[fieldname] = self.get(fieldname)

            if self.doctype in ["Quotation", "Sales Order", "Delivery Note", "Sales Invoice"]:
                document_type = f"{self.doctype} Item"
                parent_dict.update({"document_type": document_type})

            # party_name field used for customer in quotation
            if (
                self.doctype == "Quotation"
                and self.quotation_to == "Customer"
                and parent_dict.get("party_name")
            ):
                parent_dict.update({"customer": parent_dict.get("party_name")})

            self.pricing_rules = []

            for item in self.get("items"):
                if item.get("item_code"):
                    args = parent_dict.copy()
                    args.update(item.as_dict())

                    args["doctype"] = self.doctype
                    args["name"] = self.name
                    args["child_doctype"] = item.doctype
                    args["child_docname"] = item.name
                    args["ignore_pricing_rule"] = (
                        self.ignore_pricing_rule if hasattr(self, "ignore_pricing_rule") else 0
                    )

                    if not args.get("transaction_date"):
                        args["transaction_date"] = args.get("posting_date")

                    if self.get("is_subcontracted"):
                        args["is_subcontracted"] = self.is_subcontracted
                    
                    ret = custom_get_item_details(args, self, for_validate=for_validate, overwrite_warehouse=False)
                    for fieldname, value in ret.items():
                        if item.meta.get_field(fieldname) and value is not None:
                            if (
                                item.get(fieldname) is None
                                or fieldname in force_item_fields
                                or (
                                    fieldname in ["serial_no", "batch_no"]
                                    and item.get("use_serial_batch_fields")
                                )
                            ):
                                if fieldname == "batch_no" and not item.batch_no:
                                    item.set("rate", ret.get("rate"))
                                    item.set("price_list_rate", ret.get("price_list_rate"))
                                item.set(fieldname, value)

                            elif fieldname in ["cost_center", "conversion_factor"] and not item.get(
                                fieldname
                            ):
                                item.set(fieldname, value)
                            elif fieldname == "item_tax_rate" and not (
                                self.get("is_return") and self.get("return_against")
                            ):
                                item.set(fieldname, value)
                            elif fieldname == "serial_no":
                                # Ensure that serial numbers are matched against Stock UOM
                                item_conversion_factor = item.get("conversion_factor") or 1.0
                                item_qty = abs(item.get("qty")) * item_conversion_factor

                                if item_qty != len(get_serial_nos(item.get("serial_no"))):
                                    item.set(fieldname, value)

                            elif (
                                ret.get("pricing_rule_removed")
                                and value is not None
                                and fieldname
                                in [
                                    "discount_percentage",
                                    "discount_amount",
                                    "rate",
                                    "margin_rate_or_amount",
                                    "margin_type",
                                    "remove_free_item",
                                ]
                            ):
                                # reset pricing rule fields if pricing_rule_removed
                                item.set(fieldname, value)

                    if self.doctype in ["Purchase Invoice", "Sales Invoice"] and item.meta.get_field(
                        "is_fixed_asset"
                    ):
                        item.set("is_fixed_asset", ret.get("is_fixed_asset", 0))

                    # Double check for cost center
                    # Items add via promotional scheme may not have cost center set
                    if hasattr(item, "cost_center") and not item.get("cost_center"):
                        item.set(
                            "cost_center",
                            self.get("cost_center") or erpnext.get_default_cost_center(self.company),
                        )

                    if ret.get("pricing_rules"):
                        self.apply_pricing_rule_on_items(item, ret)
                        self.set_pricing_rule_details(item, ret)
                else:
                    # Transactions line item without item code

                    uom = item.get("uom")
                    stock_uom = item.get("stock_uom")
                    if bool(uom) != bool(stock_uom):  # xor
                        item.stock_uom = item.uom = uom or stock_uom

                    # UOM cannot be zero so substitute as 1
                    item.conversion_factor = (
                        get_uom_conv_factor(item.get("uom"), item.get("stock_uom"))
                        or item.get("conversion_factor")
                        or 1
                    )

            if self.doctype == "Purchase Invoice":
                self.set_expense_account(for_validate)


@erpnext.allow_regional
def validate_regional(doc):
	pass

@erpnext.allow_regional
def validate_einvoice_fields(doc):
	pass

