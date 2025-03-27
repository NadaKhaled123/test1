import frappe
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

class CustomSalesOrder(SalesOrder):
    @property
    def advance_paid_percentage(self):
        if not self.rounded_total:  
            return
        
        return round(((self.advance_paid / self.rounded_total) * 100),3)