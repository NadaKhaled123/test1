# Copyright (c) 2025, inhouse and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Offers(Document):
    pass
    # def validate(self):
    #     buy_more_items_count = len(self.get("buy_more_bay_less_items") or [])
    #     buy_more_groups_count = len(self.get("buy_more_bay_less_item_group") or [])
    #     buy_more_discounts_count = len(self.get("buy_more_bay_less_discounts") or [])

    #     if (buy_more_items_count + buy_more_groups_count - buy_more_discounts_count) > 1:
    #         frappe.throw("The total number of 'Buy More Bay Less Items' and 'Item Groups' minus 'Buy More Bay Less Discounts' cannot exceed 1.")
