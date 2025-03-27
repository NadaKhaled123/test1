app_name = "inhouse"
app_title = "inhouse"
app_publisher = "inhouse"
app_description = "inhouse"
app_email = "inhouse@gmail.com"
app_license = "MIT"



override_doctype_class = {
    "Production Plan": "inhouse.override.production_plan.CustomProductionPlan",
    "Sales Order": "inhouse.override.sales_order.CustomSalesOrder",

}

doctype_js = {
   
    "Item": "public/js/template_item_attribute.js",
    "Sales Order": "public/js/sales_order.js"
    # "point_of_sale":"public/js/point_of_sale.js"


    
}
doc_events = {
    "Work Order": {
        "after_insert": "inhouse.inhouse.controllers.work_order.add_custom_attributes",
        "before_validate": "inhouse.inhouse.controllers.work_order.get_item_details",
        "on_submit": "inhouse.inhouse.controllers.work_order.notify_work_order_created",
        "on_trash": "inhouse.inhouse.controllers.work_order.notify_work_order_created",
        "validate": "inhouse.inhouse.controllers.work_order.notify_work_order_created",
    },
    "Delivery Note": {
        "on_submit": "inhouse.inhouse.controllers.delivery_note.validate_sales_order_advance_paid",
    },
    "Sales Invoice": {
        "validate": "inhouse.inhouse.controllers.sales_invoice.validate",
        "before_submit": "inhouse.inhouse.controllers.sales_invoice.submit"
    },
        "Sales Order": {
        "validate": "inhouse.inhouse.controllers.sales_order.validate",
        "before_submit": "inhouse.inhouse.controllers.sales_order.submit"
    },
    "Quotation": {
        "validate": "inhouse.inhouse.controllers.quotation.validate",
        "before_submit": "inhouse.inhouse.controllers.quotation.submit"
    },
    "Delivery Note": {
        "validate": "inhouse.inhouse.controllers.quotation.validate",
        "before_submit": "inhouse.inhouse.controllers.quotation.submit"
    },
    "POS Invoice": {
        "validate": "inhouse.inhouse.controllers.sales_invoice.validate",
        "before_submit": "inhouse.inhouse.controllers.sales_invoice.submit"
    }
}
# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/inhouse/css/inhouse.css"
# app_include_js = "/assets/inhouse/js/inhouse.js"

# include js, css files in header of web template
# web_include_css = "/assets/inhouse/css/inhouse.css"
# web_include_js = "/assets/inhouse/js/inhouse.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "inhouse/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "inhouse.utils.jinja_methods",
# 	"filters": "inhouse.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "inhouse.install.before_install"
# after_install = "inhouse.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "inhouse.uninstall.before_uninstall"
# after_uninstall = "inhouse.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "inhouse.utils.before_app_install"
# after_app_install = "inhouse.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "inhouse.utils.before_app_uninstall"
# after_app_uninstall = "inhouse.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "inhouse.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"inhouse.tasks.all"
# 	],
# 	"daily": [
# 		"inhouse.tasks.daily"
# 	],
# 	"hourly": [
# 		"inhouse.tasks.hourly"
# 	],
# 	"weekly": [
# 		"inhouse.tasks.weekly"
# 	],
# 	"monthly": [
# 		"inhouse.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "inhouse.install.before_tests"

# Overriding Methods
# ------------------------------
#

# override_whitelisted_methods = {
# 	"erpnext.accounts.doctype.pricing_rule.pricing_rule.apply_pricing_rule": "inhouse.override.apply_pricing_rule.custom_apply_pricing_rule",
# 	"erpnext.stock.get_item_details.get_item_details": "inhouse.override.get_item_details.custom_get_item_details",
# }


#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "inhouse.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["inhouse.utils.before_request"]
# after_request = ["inhouse.utils.after_request"]

# Job Events
# ----------
# before_job = ["inhouse.utils.before_job"]
# after_job = ["inhouse.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"inhouse.auth.validate"
# ]

