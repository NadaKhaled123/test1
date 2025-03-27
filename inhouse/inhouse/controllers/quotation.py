from inhouse.inhouse.utils import buy_more_bay_less, exchange_items

def validate(doc,event):
    buy_more_bay_less(doc)
    doc.calculate_taxes_and_totals()

def submit(doc,event):
    exchange_items(doc)
    doc.calculate_taxes_and_totals()

