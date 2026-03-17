from flask import Flask, render_template, request, jsonify, send_file
import os, zipfile, io, json, base64, re

app = Flask(__name__)

VERSION_COMPAT = {
    "11.0": {"python":"3.5+","deprecated":[],"features":["basic_views","qweb","website","pos","accounting"],"license_options":["LGPL-3","GPL-3","OPL-1"],"manifest_keys":["name","version","summary","description","author","website","category","depends","data","demo","installable","auto_install","application","license"]},
    "12.0": {"python":"3.5+","deprecated":[],"features":["basic_views","qweb","website","pos","accounting","activity"],"license_options":["LGPL-3","GPL-3","OPL-1"],"manifest_keys":["name","version","summary","description","author","website","category","depends","data","demo","installable","auto_install","application","license"]},
    "13.0": {"python":"3.6+","deprecated":[],"features":["basic_views","qweb","website","pos","accounting","activity","owl_v1"],"license_options":["LGPL-3","GPL-3","OPL-1"],"manifest_keys":["name","version","summary","description","author","website","category","depends","data","demo","installable","auto_install","application","license"]},
    "14.0": {"python":"3.6+","deprecated":[],"features":["basic_views","qweb","website","pos","accounting","activity","owl_v2"],"license_options":["LGPL-3","GPL-3","OPL-1"],"manifest_keys":["name","version","summary","description","author","website","category","depends","data","demo","installable","auto_install","application","license"]},
    "15.0": {"python":"3.8+","deprecated":[],"features":["basic_views","qweb","website","pos","accounting","activity","owl_v2","spreadsheet"],"license_options":["LGPL-3","GPL-3","OPL-1"],"manifest_keys":["name","version","summary","description","author","website","category","depends","data","demo","installable","auto_install","application","license"]},
    "16.0": {"python":"3.10+","deprecated":["qweb_legacy"],"features":["basic_views","qweb","website","pos","accounting","activity","owl_v2","spreadsheet","discuss"],"license_options":["LGPL-3","GPL-3","OPL-1"],"manifest_keys":["name","version","summary","description","author","website","category","depends","data","demo","installable","auto_install","application","license","assets"]},
    "17.0": {"python":"3.10+","deprecated":["qweb_legacy"],"features":["basic_views","qweb","website","pos","accounting","activity","owl_v2","spreadsheet","discuss","knowledge"],"license_options":["LGPL-3","GPL-3","OPL-1"],"manifest_keys":["name","version","summary","description","author","website","category","depends","data","demo","installable","auto_install","application","license","assets"]},
    "18.0": {"python":"3.10+","deprecated":["qweb_legacy","old_api"],"features":["basic_views","qweb","website","pos","accounting","activity","owl_v2","spreadsheet","discuss","knowledge","studio"],"license_options":["LGPL-3","GPL-3","OPL-1","AGPL-3"],"manifest_keys":["name","version","summary","description","author","website","category","depends","data","demo","installable","auto_install","application","license","assets","cloc_exclude"]},
    "19.0": {"python":"3.11+","deprecated":["qweb_legacy","old_api"],"features":["basic_views","qweb","website","pos","accounting","activity","owl_v2","spreadsheet","discuss","knowledge","studio","ai_features"],"license_options":["LGPL-3","GPL-3","OPL-1","AGPL-3"],"manifest_keys":["name","version","summary","description","author","website","category","depends","data","demo","installable","auto_install","application","license","assets","cloc_exclude"]}
}

CATEGORIES = ["Accounting","Administration","Bar","Barcode","Bridge Module","CRM","Calendar","Connector","Contact","Customer","Customizations","Database","Discuss","Document Management","eCommerce","Email","Enterprise","Events","Extra Tools","Fleet","Hidden","HR","Industries","Inventory","IoT","Leaves","Localization","Lunch","Mail","Manufacturing","Marketing","Members","Payroll","Point of Sale","Productivity","Project","Purchase","Recruitment","Repairs","Sales","Services","Sign","Social","Stock","Survey","Technical","Timesheets","Uncategorized","Warehouse","Website"]
COMMON_DEPENDS = ["base","mail","web","account","sale","purchase","stock","mrp","hr","project","crm","website","point_of_sale","fleet","maintenance","helpdesk","timesheet","calendar","contacts","utm","portal","product","sale_management"]


# ─── COPYRIGHT HEADER UTILITY ────────────────────────────────────────────────

LICENSE_URLS = {
    "LGPL-3": "https://www.gnu.org/licenses/lgpl-3.0-standalone.html",
    "GPL-3":  "https://www.gnu.org/licenses/gpl-3.0-standalone.html",
    "OPL-1":  "https://www.odoo.com/documentation/user/legal/licenses.html",
    "AGPL-3": "https://www.gnu.org/licenses/agpl-3.0-standalone.html",
}

def _file_header(data, lang="py"):
    """Return a language-appropriate copyright + license header block."""
    dev_name    = data.get("dev_name","").strip()
    dev_email   = data.get("dev_email","").strip()
    dev_year    = data.get("dev_year","2025").strip() or "2025"
    dev_company = data.get("dev_company","").strip()
    lic         = data.get("license","LGPL-3")
    lic_url     = LICENSE_URLS.get(lic,"")
    website     = data.get("website","").strip()
    module_name = data.get("display_name") or data.get("name","Module")

    author = dev_company or dev_name
    copy_line = f"Copyright (c) {dev_year}"
    if author:     copy_line += f" {author}"
    if dev_email:  copy_line += f" <{dev_email}>"

    if lang == "py":
        lines = ["# -*- coding: utf-8 -*-"]
        if author or dev_year:
            lines.append(f"# {copy_line}")
        if lic_url:
            lines.append(f"# License {lic}: {lic_url}")
        lines.append("#")
        if dev_name:
            lines.append(f"# @author   {dev_name}" + (f" <{dev_email}>" if dev_email else ""))
        if dev_company and dev_company != dev_name:
            lines.append(f"# @company  {dev_company}")
        if website:
            lines.append(f"# @website  {website}")
        lines.append(f"# @module   {module_name}")
        lines.append("")
        return "\n".join(lines) + "\n"

    elif lang == "xml":
        lines = ['<?xml version="1.0" encoding="utf-8"?>',
                 "<!--"]
        if author or dev_year:
            lines.append(f"    {copy_line}")
        if lic_url:
            lines.append(f"    License {lic}: {lic_url}")
        if dev_name:
            lines.append(f"    @author   {dev_name}" + (f" <{dev_email}>" if dev_email else ""))
        if dev_company and dev_company != dev_name:
            lines.append(f"    @company  {dev_company}")
        if website:
            lines.append(f"    @website  {website}")
        lines.append(f"    @module   {module_name}")
        lines.append("-->")
        return "\n".join(lines) + "\n"

    elif lang == "js":
        lines = ["/**"]
        if author or dev_year:
            lines.append(f" * {copy_line}")
        if lic_url:
            lines.append(f" * License {lic}: {lic_url}")
        if dev_name:
            lines.append(f" * @author   {dev_name}" + (f" <{dev_email}>" if dev_email else ""))
        if website:
            lines.append(f" * @website  {website}")
        lines.append(f" * @module   {module_name}")
        lines.append(" */")
        return "\n".join(lines) + "\n"

    elif lang == "css":
        lines = ["/**"]
        if author or dev_year:
            lines.append(f" * {copy_line}")
        if lic_url:
            lines.append(f" * License {lic}: {lic_url}")
        lines.append(f" * @module   {module_name}")
        lines.append(" */")
        return "\n".join(lines) + "\n"

    return ""


# ─── MANIFEST GENERATOR ──────────────────────────────────────────────────────

def generate_manifest(data):
    version = data.get("odoo_version","17.0")
    compat = VERSION_COMPAT.get(version, VERSION_COMPAT["17.0"])
    module_name = data.get("name","my_module")
    mod_version = version + "." + (data.get("custom_version") or "1.0.0")
    depends = list(data.get("depends",["base"]) or ["base"])

    # Auto-inject required depends
    if data.get("has_invoice") and "account" not in depends:
        depends.append("account")
    if data.get("has_pos_buttons") and "point_of_sale" not in depends:
        depends.append("point_of_sale")

    data_files = []
    if data.get("has_security"):         data_files.append("security/ir.model.access.csv")
    if data.get("has_views"):            data_files.append("views/"+module_name+"_views.xml")
    if data.get("has_menus"):            data_files.append("views/"+module_name+"_menus.xml")
    if data.get("has_wizard"):           data_files.append("wizard/"+module_name+"_wizard_views.xml")
    if data.get("has_reports"):          data_files += ["report/"+module_name+"_report.xml","report/"+module_name+"_templates.xml"]
    if data.get("has_data"):             data_files.append("data/"+module_name+"_data.xml")
    if data.get("has_cron"):             data_files.append("data/"+module_name+"_cron.xml")
    if data.get("has_email_templates"):  data_files.append("data/"+module_name+"_email_templates.xml")
    if data.get("has_config"):           data_files.append("views/res_config_settings_views.xml")
    if data.get("has_pricing"):          data_files.append("data/"+module_name+"_pricelists.xml")
    # Invoice report designer
    if data.get("has_invoice"):
        data_files.append("report/"+module_name+"_invoice_layout.xml")
        data_files.append("report/"+module_name+"_invoice_templates.xml")
        if data.get("inv_paper_format"):
            data_files.append("report/"+module_name+"_paper_format.xml")

    demo_files = ["demo/"+module_name+"_demo.xml"] if data.get("has_demo") else []

    L = ["# -*- coding: utf-8 -*-"]
    # Copyright block in manifest
    dev_name    = data.get("dev_name","").strip()
    dev_email   = data.get("dev_email","").strip()
    dev_year    = data.get("dev_year","2025").strip() or "2025"
    dev_company = data.get("dev_company","").strip()
    lic         = data.get("license","LGPL-3")
    lic_url     = LICENSE_URLS.get(lic,"")
    author_str  = dev_company or dev_name
    if author_str or dev_year:
        copy_line = f"# Copyright (c) {dev_year}"
        if author_str: copy_line += f" {author_str}"
        if dev_email:  copy_line += f" <{dev_email}>"
        L.append(copy_line)
    if lic_url:
        L.append(f"# License {lic}: {lic_url}")
    L.append("{")
    dn = data.get("display_name") or data.get("name","My Module")
    L.append("    'name': '" + dn + "',")
    L.append("    'version': '" + mod_version + "',")
    if data.get("summary"):     L.append("    'summary': '" + data["summary"].replace("'","\\'") + "',")
    if data.get("description"):
        L.append("    'description': '''")
        L.append(data["description"].replace("'","\\'"))
        L.append("    ''',")
    if data.get("author"):      L.append("    'author': '" + data["author"] + "',")
    if dev_name and dev_name != data.get("author",""):
        L.append("    'maintainer': '" + dev_name + "',")
    if dev_email:               L.append("    'maintainer_email': '" + dev_email + "',")
    if data.get("website"):     L.append("    'website': '" + data["website"] + "',")
    if data.get("category"):    L.append("    'category': '" + data["category"] + "',")
    L.append("    'license': '" + data.get("license","LGPL-3") + "',")
    L.append("    'depends': " + json.dumps(depends) + ",")
    if data_files:
        formatted = "[\n        " + ",\n        ".join(json.dumps(f) for f in data_files) + "\n    ]"
        L.append("    'data': " + formatted + ",")
    else:
        L.append("    'data': [],")
    if demo_files:  L.append("    'demo': " + json.dumps(demo_files) + ",")
    if data.get("images"): L.append("    'images': ['static/description/banner.png'],")
    if data.get("price") and data.get("pricing_enabled"):
        L.append("    'price': " + str(float(data["price"])) + ",")
        L.append("    'currency': '" + data.get("currency","EUR") + "',")
    L.append("    'installable': " + str(bool(data.get("installable",True))) + ",")
    L.append("    'auto_install': " + str(bool(data.get("auto_install",False))) + ",")
    L.append("    'application': " + str(bool(data.get("application",False))) + ",")

    has_assets = (data.get("has_js") or data.get("has_css") or data.get("has_qweb")
                  or data.get("has_invoice") or data.get("has_pos_buttons"))
    if "assets" in compat["manifest_keys"] and has_assets:
        L.append("    'assets': {")
        # Backend JS/CSS
        if data.get("has_js") or data.get("has_css"):
            L.append("        'web.assets_backend': [")
            if data.get("has_css"): L.append("            '"+module_name+"/static/src/css/"+module_name+".css',")
            if data.get("has_js"):  L.append("            '"+module_name+"/static/src/js/"+module_name+".js',")
            L.append("        ],")
        # QWeb templates
        if data.get("has_qweb"):
            L.append("        'web.assets_qweb': [")
            L.append("            '"+module_name+"/static/src/xml/"+module_name+"_templates.xml',")
            L.append("        ],")
        # Invoice report CSS
        if data.get("has_invoice"):
            L.append("        'web.report.assets_common': [")
            L.append("            '"+module_name+"/static/src/css/"+module_name+"_invoice.css',")
            L.append("        ],")
        # POS buttons JS + XML
        if data.get("has_pos_buttons"):
            v_num = float(version.split(".")[0])
            pos_asset = "point_of_sale.assets" if v_num >= 16 else "point_of_sale.assets_backend"
            L.append("        '"+pos_asset+"': [")
            L.append("            '"+module_name+"/static/src/js/pos_buttons.js',")
            L.append("            '"+module_name+"/static/src/xml/pos_buttons.xml',")
            L.append("        ],")
        L.append("    },")
    elif data.get("has_qweb") and "assets" not in compat["manifest_keys"]:
        L.append("    'qweb': ['"+module_name+"/static/src/xml/"+module_name+"_templates.xml'],")
    if "cloc_exclude" in compat["manifest_keys"] and data.get("has_cloc_exclude"):
        L.append("    'cloc_exclude': ['**/*.xml'],")
    L.append("}")
    return "\n".join(L)


# ─── FILE STRUCTURE GENERATOR ────────────────────────────────────────────────

def generate_file_structure(data):
    version = data.get("odoo_version","17.0")
    mn = data.get("name","my_module")
    model_name = data.get("model_name","my.custom.model")
    class_name = "".join(w.capitalize() for w in model_name.replace(".","_").split("_"))
    S = {}
    inits = []

    S["__manifest__.py"] = generate_manifest(data)

    if data.get("has_models"):
        inits.append("models")
        safe = model_name.replace(".","_")
        S["models/__init__.py"] = _file_header(data) + "from . import "+safe+"\n"
        ml = [_file_header(data).rstrip(),"from odoo import models, fields, api","",
              "class "+class_name+"(models.Model):",
              "    _name = '"+model_name+"'",
              "    _description = '"+data.get("display_name",mn)+" Model'"]
        if data.get("inherit_mail"): ml.append("    _inherit = ['mail.thread', 'mail.activity.mixin']")
        ml += ["","    name = fields.Char(string='Name', required=True)","    active = fields.Boolean(string='Active', default=True)"]
        if data.get("has_pricing"):
            ml += ["    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')",
                   "    currency_id = fields.Many2one(related='pricelist_id.currency_id', string='Currency')"]
        ml.append("")
        S["models/"+safe+".py"] = "\n".join(ml)

    if data.get("has_views"):
        S["views/"+mn+"_views.xml"] = _views_xml(data)
    if data.get("has_menus"):
        S["views/"+mn+"_menus.xml"] = _menus_xml(data)
    if data.get("has_security"):
        S["security/ir.model.access.csv"] = _security(data)
    if data.get("has_wizard"):
        inits.append("wizard")
        wn = mn+"_wizard"
        S["wizard/__init__.py"] = _file_header(data) + "from . import "+wn+"\n"
        S["wizard/"+wn+".py"] = _wizard_py(data)
        S["wizard/"+wn+"_views.xml"] = _wizard_xml(data)
    if data.get("has_controllers"):
        inits.append("controllers")
        S["controllers/__init__.py"] = _file_header(data) + "from . import main\n"
        S["controllers/main.py"] = _controller(data)
    if data.get("has_reports"):
        S["report/"+mn+"_report.xml"] = _report_action(data)
        S["report/"+mn+"_templates.xml"] = _report_template(data)
    if data.get("has_data"):
        S["data/"+mn+"_data.xml"] = '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <!-- Static data -->\n</odoo>\n'
    if data.get("has_cron"):
        S["data/"+mn+"_cron.xml"] = _cron(data)
    if data.get("has_email_templates"):
        S["data/"+mn+"_email_templates.xml"] = _email_template(data)
    if data.get("has_config"):
        S["views/res_config_settings_views.xml"] = _config_views(data)
    if data.get("has_pricing"):
        S["data/"+mn+"_pricelists.xml"] = _pricelist_data(data)
    if data.get("has_js"):
        S["static/src/js/"+mn+".js"] = _js(data, version)
    if data.get("has_css"):
        S["static/src/css/"+mn+".css"] = _file_header(data,"css") + "/* "+data.get("display_name",mn)+" Styles */\n"
    if data.get("has_qweb"):
        S["static/src/xml/"+mn+"_templates.xml"] = _qweb(data)
    if data.get("has_demo"):
        S["demo/"+mn+"_demo.xml"] = '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <!-- Demo data -->\n</odoo>\n'
    # ── Invoice report designer ──────────────────────────────────────────
    if data.get("has_invoice"):
        S["report/"+mn+"_invoice_layout.xml"]    = _invoice_layout_xml(data)
        S["report/"+mn+"_invoice_templates.xml"] = _invoice_templates_xml(data)
        S["static/src/css/"+mn+"_invoice.css"]   = _invoice_css(data)
        if data.get("inv_paper_format"):
            S["report/"+mn+"_paper_format.xml"]  = _invoice_paper_xml(data)
    # ── POS button designer ──────────────────────────────────────────────
    if data.get("has_pos_buttons"):
        S["static/src/js/pos_buttons.js"]        = _pos_buttons_js(data, version)
        S["static/src/xml/pos_buttons.xml"]      = _pos_buttons_xml(data)
        if data.get("pos_needs_model"):
            inits.append("models") if "models" not in inits else None
            safe_mn = mn+"_pos_config"
            if "models/__init__.py" not in S:
                S["models/__init__.py"] = "# -*- coding: utf-8 -*-\nfrom . import "+safe_mn+"\n"
            else:
                S["models/__init__.py"] = S["models/__init__.py"].rstrip() + "\nfrom . import "+safe_mn+"\n"
            S["models/"+safe_mn+".py"] = _pos_config_model(data)
    S["static/description/index.html"] = _desc_html(data)
    S["__init__.py"] = _file_header(data) + ("\n".join("from . import "+i for i in inits)+"\n" if inits else "")
    return S

def _views_xml(d):
    mn = d.get("name","my_module"); ml = d.get("model_name","my.model"); mid = ml.replace(".","_")
    dn = d.get("display_name",mn)
    hdr = _file_header(d, "xml")
    return hdr + f'''<odoo>
    <record id="view_{mid}_list" model="ir.ui.view">
        <field name="name">{ml}.list</field>
        <field name="model">{ml}</field>
        <field name="arch" type="xml">
            <list string="{dn}"><field name="name"/></list>
        </field>
    </record>
    <record id="view_{mid}_form" model="ir.ui.view">
        <field name="name">{ml}.form</field>
        <field name="model">{ml}</field>
        <field name="arch" type="xml">
            <form string="{dn}">
                <sheet><group><field name="name"/></group></sheet>
            </form>
        </field>
    </record>
    <record id="view_{mid}_search" model="ir.ui.view">
        <field name="name">{ml}.search</field>
        <field name="model">{ml}</field>
        <field name="arch" type="xml">
            <search><field name="name"/><filter string="Active" name="active" domain="[(\'active\',\'=\',True)]"/></search>
        </field>
    </record>
    <record id="action_{mid}" model="ir.actions.act_window">
        <field name="name">{dn}</field>
        <field name="res_model">{ml}</field>
        <field name="view_mode">list,form</field>
    </record>
</odoo>
'''

def _menus_xml(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); ml = d.get("model_name","my.model"); mid = ml.replace(".","_")
    dn = d.get("display_name",mn)
    hdr = _file_header(d, "xml")
    return hdr + f'''<odoo>
    <menuitem id="menu_{mn}_root" name="{dn}" sequence="100"/>
    <menuitem id="menu_{mn}_main" name="{dn}" parent="menu_{mn}_root" action="action_{mid}" sequence="10"/>
</odoo>
'''

def _security(d):
    ml = d.get("model_name","my.model"); mid = ml.replace(".","_")
    return f"id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\naccess_{mid}_user,{ml} User,model_{mid},base.group_user,1,1,1,0\naccess_{mid}_manager,{ml} Manager,model_{mid},base.group_system,1,1,1,1\n"

def _wizard_py(d):
    mn = d.get("name","my_module"); cn = "".join(w.capitalize() for w in mn.replace(" ","_").split("_"))
    hdr = _file_header(d)
    return hdr + f"from odoo import models, fields, api\n\nclass {cn}Wizard(models.TransientModel):\n    _name = '{mn.lower().replace(' ','_')}.wizard'\n    _description = '{d.get('display_name',mn)} Wizard'\n\n    name = fields.Char(string='Name')\n\n    def action_confirm(self):\n        return {{'type': 'ir.actions.act_window_close'}}\n"

def _wizard_xml(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); dn = d.get("display_name",mn)
    hdr = _file_header(d, "xml")
    return hdr + f'''<odoo>
    <record id="view_{mn}_wizard_form" model="ir.ui.view">
        <field name="name">{mn}.wizard.form</field>
        <field name="model">{mn}.wizard</field>
        <field name="arch" type="xml">
            <form string="{dn} Wizard">
                <group><field name="name"/></group>
                <footer>
                    <button name="action_confirm" type="object" string="Confirm" class="btn-primary"/>
                    <button string="Cancel" class="btn-secondary" special="cancel"/>
                </footer>
            </form>
        </field>
    </record>
</odoo>
'''

def _controller(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); cn = "".join(w.capitalize() for w in mn.split("_"))
    hdr = _file_header(d)
    return hdr + f"from odoo import http\nfrom odoo.http import request\n\nclass {cn}Controller(http.Controller):\n\n    @http.route(['/{mn}'], type='http', auth='public', website=True)\n    def index(self, **kwargs):\n        return request.render('{mn}.index_template', {{}})\n"

def _report_action(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); ml = d.get("model_name","my.model"); dn = d.get("display_name",mn)
    hdr = _file_header(d, "xml")
    return hdr + f'<odoo>\n    <report id="report_{mn}" model="{ml}" string="{dn} Report" name="{mn}.report_template" file="{mn}_report" report_type="qweb-pdf"/>\n</odoo>\n'

def _report_template(d):
    hdr = _file_header(d, "xml")
    return hdr + '<odoo>\n    <template id="report_template">\n        <t t-call="web.html_container">\n            <t t-foreach="docs" t-as="doc">\n                <t t-call="web.external_layout">\n                    <div class="page"><h2><t t-esc="doc.name"/></h2></div>\n                </t>\n            </t>\n        </t>\n    </template>\n</odoo>\n'

def _cron(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); dn = d.get("display_name",mn)
    hdr = _file_header(d, "xml")
    return hdr + f'<odoo>\n    <record id="ir_cron_{mn}" model="ir.cron">\n        <field name="name">{dn} Scheduled Action</field>\n        <field name="state">code</field>\n        <field name="code">model.your_cron_method()</field>\n        <field name="interval_number">1</field>\n        <field name="interval_type">days</field>\n        <field name="numbercall">-1</field>\n        <field name="active">True</field>\n    </record>\n</odoo>\n'

def _email_template(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); ml = d.get("model_name","my.model"); mid = ml.replace(".","_"); dn = d.get("display_name",mn)
    hdr = _file_header(d, "xml")
    return hdr + f'<odoo>\n    <record id="email_template_{mn}" model="mail.template">\n        <field name="name">{dn} Email</field>\n        <field name="model_id" ref="model_{mid}"/>\n        <field name="subject">{dn} Notification</field>\n        <field name="body_html"><![CDATA[<p>Dear <t t-out="object.name"/>,</p><p>Notification from {dn}.</p>]]></field>\n        <field name="auto_delete" eval="True"/>\n    </record>\n</odoo>\n'

def _config_views(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); dn = d.get("display_name",mn)
    hdr = _file_header(d, "xml")
    return hdr + f'<odoo>\n    <record id="res_config_settings_view_{mn}" model="ir.ui.view">\n        <field name="name">res.config.settings.view.{mn}</field>\n        <field name="model">res.config.settings</field>\n        <field name="inherit_id" ref="base_setup.action_general_configuration"/>\n        <field name="arch" type="xml">\n            <xpath expr="//div[hasclass(\'settings\')]" position="inside">\n                <div class="app_settings_block" data-string="{dn}" data-key="{mn}">\n                    <h2>{dn} Settings</h2>\n                </div>\n            </xpath>\n        </field>\n    </record>\n</odoo>\n'

def _pricelist_data(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); dn = d.get("display_name",mn)
    currency = d.get("currency","EUR")
    hdr = _file_header(d, "xml")
    return hdr + f'<odoo>\n    <!-- Pricelist configuration for {dn} -->\n    <!-- <record id="pricelist_{mn}_standard" model="product.pricelist">\n        <field name="name">{dn} Standard</field>\n        <field name="currency_id" ref="base.{currency.lower()}"/>\n    </record> -->\n</odoo>\n'

def _js(d, version):
    mn = d.get("name","my_module").lower().replace(" ","_"); cn = "".join(w.capitalize() for w in mn.split("_"))
    hdr = _file_header(d, "js")
    v = float(version.split(".")[0])
    if v >= 16:
        return hdr + f'/** @odoo-module **/\nimport {{ Component }} from "@odoo/owl";\nimport {{ registry }} from "@web/core/registry";\n\nclass {cn}Widget extends Component {{\n    static template = "{mn}.widget_template";\n    setup() {{}}\n}}\n\nregistry.category("view_widgets").add("{mn}_widget", {cn}Widget);\n'
    elif v >= 14:
        return hdr + f"odoo.define('{mn}.widget', function(require) {{\n    \"use strict\";\n    const {{ Component }} = owl;\n    const {{ registry }} = require(\"@web/core/registry\");\n    class {cn}Widget extends Component {{}}\n    registry.category(\"view_widgets\").add(\"{mn}_widget\", {cn}Widget);\n}});\n"
    else:
        return hdr + f"odoo.define('{mn}.js', function(require) {{\n    \"use strict\";\n    var Widget = require('web.Widget');\n    var {cn}Widget = Widget.extend({{\n        template: '{mn}_widget',\n        init: function(parent, options) {{ this._super.apply(this, arguments); }},\n        start: function() {{ return this._super.apply(this, arguments); }}\n    }});\n    return {cn}Widget;\n}});\n"

def _qweb(d):
    mn = d.get("name","my_module").lower().replace(" ","_")
    hdr = _file_header(d, "xml")
    return hdr + f'<templates xml:space="preserve">\n    <t t-name="{mn}.widget_template">\n        <div class="{mn}_widget"><!-- Widget content --></div>\n    </t>\n</templates>\n'

def _desc_html(d):
    dn = d.get("display_name",d.get("name","My Module")); sm = d.get("summary",""); desc = d.get("description","")
    return f'<!DOCTYPE html>\n<html>\n<head><meta charset="utf-8"/></head>\n<body>\n<h1>{dn}</h1>\n<p>{sm}</p>\n<p>{desc}</p>\n</body>\n</html>\n'


# ─── INVOICE REPORT DESIGNER ─────────────────────────────────────────────────

def _invoice_layout_xml(d):
    mn  = d.get("name","my_module")
    dn  = d.get("display_name", mn)
    lay = d.get("invoice_layout","standard")
    pc  = d.get("invoice_primary_color","#875A7B")
    sc  = d.get("invoice_secondary_color","#f8f8f8")
    logo_field = '<img t-if="company.logo" t-att-src="\'data:image/png;base64,\' + (company.logo or \'\')" style="max-height:60px;max-width:160px;"/>' if d.get("inv_show_logo",True) else "<!-- logo hidden -->"
    bank_block = '''
                    <t t-if="o.partner_bank_id">
                        <div class="bank-details">
                            <span t-field="o.partner_bank_id.bank_id.name"/> —
                            <span t-field="o.partner_bank_id.acc_number"/>
                        </div>
                    </t>''' if d.get("inv_show_bank",True) else ""
    footer_txt = d.get("inv_footer_text","").replace("'","\\'")

    # ── Layout dispatch ────────────────────────────────────────────────
    if lay == "standard":
        body = f'''    <!-- Standard layout: clean, left-aligned header, ruled sections -->
    <template id="invoice_layout_standard" inherit_id="account.report_invoice_document" priority="15">
        <xpath expr="//t[@t-call]" position="attributes">
            <attribute name="t-call">web.external_layout_standard</attribute>
        </xpath>
    </template>'''

    elif lay == "boxed":
        body = f'''    <!-- Boxed layout: bordered header/footer boxes -->
    <template id="invoice_layout_boxed" inherit_id="account.report_invoice_document" priority="15">
        <xpath expr="//t[@t-call]" position="attributes">
            <attribute name="t-call">web.external_layout_boxed</attribute>
        </xpath>
    </template>'''

    elif lay == "minimalist":
        body = f'''    <!-- Minimalist: typography-focused, no decorative rules -->
    <template id="invoice_layout_minimalist" inherit_id="account.report_invoice_document" priority="15">
        <xpath expr="//div[hasclass('page')]" position="before">
            <div class="{mn}-inv-header-minimalist">
                <div class="inv-logo">{logo_field}</div>
                <div class="inv-meta">
                    <span class="company-name" t-field="company.name"/>
                    <t t-if="company.street"><span t-field="company.street"/></t>
                    <t t-if="company.email"><span t-field="company.email"/></t>
                </div>
            </div>
        </xpath>
    </template>'''

    elif lay == "modern":
        body = f'''    <!-- Modern: full-width color band header, accent accent_color line -->
    <template id="invoice_layout_modern" inherit_id="account.report_invoice_document" priority="15">
        <xpath expr="//div[hasclass('page')]" position="before">
            <div class="{mn}-inv-header-modern">
                <div class="mod-band">
                    <div class="mod-logo">{logo_field}</div>
                    <div class="mod-company">
                        <strong t-field="company.name"/>
                        <span t-if="company.phone" t-field="company.phone"/>
                        <span t-if="company.email" t-field="company.email"/>
                    </div>
                </div>
                <div class="mod-accent-line"/>
            </div>
        </xpath>
        <xpath expr="//div[hasclass('page')]" position="after">
            <div class="{mn}-inv-footer-modern">
                <t t-if="company.website"><span t-field="company.website"/></t>
                {bank_block}
                <t t-if="\\'{footer_txt}\\'"><div class="footer-text">{footer_txt}</div></t>
            </div>
        </xpath>
    </template>'''

    elif lay == "classic":
        body = f'''    <!-- Classic: centered header with horizontal rules, traditional feel -->
    <template id="invoice_layout_classic" inherit_id="account.report_invoice_document" priority="15">
        <xpath expr="//div[hasclass('page')]" position="before">
            <div class="{mn}-inv-header-classic">
                <div class="classic-logo-row">
                    {logo_field}
                    <div class="classic-company-block">
                        <h2 t-field="company.name"/>
                        <p>
                            <t t-if="company.street"><span t-field="company.street"/><br/></t>
                            <t t-if="company.city"><span t-field="company.city"/></t>
                            <t t-if="company.country_id">, <span t-field="company.country_id.name"/></t>
                        </p>
                        <p>
                            <t t-if="company.phone">Tel: <span t-field="company.phone"/>  </t>
                            <t t-if="company.email">Email: <span t-field="company.email"/></t>
                        </p>
                    </div>
                </div>
                <hr class="classic-rule classic-rule-top"/>
            </div>
        </xpath>
        <xpath expr="//div[hasclass('page')]" position="after">
            <div class="{mn}-inv-footer-classic">
                <hr class="classic-rule classic-rule-bottom"/>
                {bank_block}
                <t t-if="\\'{footer_txt}\\'"><p class="footer-text">{footer_txt}</p></t>
            </div>
        </xpath>
    </template>'''

    elif lay == "corporate":
        body = f'''    <!-- Corporate: large full-width banner, strong brand presence -->
    <template id="invoice_layout_corporate" inherit_id="account.report_invoice_document" priority="15">
        <xpath expr="//div[hasclass('page')]" position="before">
            <div class="{mn}-inv-header-corporate">
                <div class="corp-banner">
                    <div class="corp-logo">{logo_field}</div>
                    <div class="corp-name-block">
                        <h1 class="corp-company-name" t-field="company.name"/>
                        <p class="corp-tagline" t-if="company.website" t-field="company.website"/>
                    </div>
                </div>
                <div class="corp-contact-strip">
                    <t t-if="company.street"><span class="corp-addr" t-field="company.street"/></t>
                    <t t-if="company.phone"><span class="corp-phone">&#9742; <span t-field="company.phone"/></span></t>
                    <t t-if="company.email"><span class="corp-email">&#9993; <span t-field="company.email"/></span></t>
                    <t t-if="company.vat"><span class="corp-vat">VAT: <span t-field="company.vat"/></span></t>
                </div>
            </div>
        </xpath>
        <xpath expr="//div[hasclass('page')]" position="after">
            <div class="{mn}-inv-footer-corporate">
                <div class="corp-footer-strip">
                    {bank_block}
                    <t t-if="\\'{footer_txt}\\'"><span class="footer-text">{footer_txt}</span></t>
                    <span class="corp-page">Page <span class="page"/> / <span class="topage"/></span>
                </div>
            </div>
        </xpath>
    </template>'''

    elif lay == "letterhead":
        body = f'''    <!-- Letterhead: pre-printed paper style with top/bottom gutters for letterhead paper -->
    <template id="invoice_layout_letterhead" inherit_id="account.report_invoice_document" priority="15">
        <xpath expr="//div[hasclass('page')]" position="before">
            <!-- Reserved gutter for physical letterhead top (60mm) -->
            <div class="{mn}-inv-letterhead-top-gutter"/>
        </xpath>
        <xpath expr="//div[hasclass('page')]" position="after">
            <div class="{mn}-inv-footer-letterhead">
                {bank_block}
                <t t-if="\\'{footer_txt}\\'"><p class="footer-text">{footer_txt}</p></t>
                <!-- Reserved gutter for physical letterhead bottom (20mm) -->
                <div class="{mn}-inv-letterhead-bottom-gutter"/>
            </div>
        </xpath>
    </template>'''

    else:
        body = f'    <!-- Layout: {lay} -->'

    return f'''<?xml version="1.0" encoding="utf-8"?>
<odoo>
{body}
</odoo>
'''


def _invoice_templates_xml(d):
    mn  = d.get("name","my_module")
    lay = d.get("invoice_layout","standard")
    show_tax    = d.get("inv_show_tax", True)
    show_terms  = d.get("inv_show_terms", True)
    show_qr     = d.get("inv_show_qr", False)
    show_sign   = d.get("inv_show_signature", False)
    pf_id       = d.get("inv_paper_format_id","")
    pf_line     = f'\n    <attribute name="paperformat_id">{mn}.paperformat_{mn}</attribute>' if d.get("inv_paper_format") and pf_id else ""

    tax_block   = "" if show_tax else '''
        <xpath expr="//table[hasclass('o_taxes')]" position="replace"/>'''
    terms_block = "" if show_terms else '''
        <xpath expr="//p[@t-if='o.invoice_payment_term_id']" position="replace"/>'''
    qr_block    = '''
        <xpath expr="//div[hasclass('o_account_invoice_qr')]" position="replace">
            <div class="o_account_invoice_qr o_qr_enabled"/>
        </xpath>''' if show_qr else ""
    sign_block  = f'''
        <xpath expr="//div[hasclass('page')]" position="inside">
            <div class="{mn}-signature-block">
                <div class="sig-line"></div>
                <p>Authorized Signature</p>
            </div>
        </xpath>''' if show_sign else ""

    return f'''<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Report action override — change paper format or report name here -->
    <record id="account_invoices_{mn}" model="ir.actions.report">
        <field name="name">Invoice / {d.get("display_name",mn)}</field>
        <field name="model">account.move</field>
        <field name="report_type">qweb-pdf</field>
        <field name="report_name">account.report_invoice_with_payments</field>{pf_line}
    </record>

    <!-- Field visibility overrides for the invoice document -->
    <template id="report_invoice_document_{mn}" inherit_id="account.report_invoice_document" priority="20">{tax_block}{terms_block}{qr_block}{sign_block}
    </template>
</odoo>
'''


def _invoice_paper_xml(d):
    mn   = d.get("name","my_module")
    dn   = d.get("display_name", mn)
    size = d.get("inv_paper_size","A4")
    orient = d.get("inv_orientation","portrait")
    # A4 portrait: 210x297mm  A4 landscape: 297x210mm  Letter: 215.9x279.4mm
    dims = {
        "A4-portrait":   (210, 297),
        "A4-landscape":  (297, 210),
        "A5-portrait":   (148, 210),
        "Letter-portrait": (215, 279),
        "Letter-landscape":(279, 215),
    }
    w, h = dims.get(f"{size}-{orient}", (210, 297))
    mt   = d.get("inv_margin_top",   15)
    mb   = d.get("inv_margin_bottom",10)
    ml   = d.get("inv_margin_left",  10)
    mr   = d.get("inv_margin_right", 10)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="paperformat_{mn}" model="report.paperformat">
        <field name="name">{dn} Paper Format</field>
        <field name="default" eval="False"/>
        <field name="format">{size}</field>
        <field name="page_height">{h}</field>
        <field name="page_width">{w}</field>
        <field name="orientation">{"Portrait" if orient=="portrait" else "Landscape"}</field>
        <field name="margin_top">{mt}</field>
        <field name="margin_bottom">{mb}</field>
        <field name="margin_left">{ml}</field>
        <field name="margin_right">{mr}</field>
        <field name="header_line" eval="False"/>
        <field name="header_spacing">0</field>
        <field name="dpi">90</field>
    </record>
</odoo>
'''


def _invoice_css(d):
    mn  = d.get("name","my_module")
    lay = d.get("invoice_layout","standard")
    pc  = d.get("invoice_primary_color","#875A7B")
    sc  = d.get("invoice_secondary_color","#f8f8f8")
    font = d.get("invoice_font","sans-serif")

    # Shared base
    base = f"""/* ── {d.get("display_name",mn)} Invoice Styles ── */
/* Layout: {lay} | Primary: {pc} | Font: {font} */

.o_report_invoice {{ font-family: {font}; }}
"""

    if lay == "minimalist":
        return base + f'''.{mn}-inv-header-minimalist {{
    display: flex; align-items: flex-start; justify-content: space-between;
    padding: 8mm 0 6mm; border-bottom: 0.5pt solid #ccc; margin-bottom: 6mm;
}}
.{mn}-inv-header-minimalist .inv-meta {{ text-align: right; font-size: 8pt; color: #555; line-height: 1.6; }}
.{mn}-inv-header-minimalist .inv-meta .company-name {{ font-size: 12pt; font-weight: 700; color: #111; display: block; }}
'''

    elif lay == "modern":
        return base + f'''.{mn}-inv-header-modern .mod-band {{
    background: {pc}; color: #fff; display: flex;
    align-items: center; padding: 6mm 8mm; margin: -10mm -10mm 0;
}}
.{mn}-inv-header-modern .mod-logo {{ margin-right: 8mm; }}
.{mn}-inv-header-modern .mod-logo img {{ filter: brightness(10); max-height: 40px; }}
.{mn}-inv-header-modern .mod-company {{ font-size: 8pt; line-height: 1.7; }}
.{mn}-inv-header-modern .mod-company strong {{ font-size: 13pt; display: block; letter-spacing: 0.5px; }}
.{mn}-inv-header-modern .mod-accent-line {{
    height: 3pt; background: {sc}; margin: 0 -10mm 6mm;
}}
.{mn}-inv-footer-modern {{
    margin-top: 8mm; padding-top: 4mm; border-top: 0.5pt solid {pc};
    font-size: 7.5pt; color: #666; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 2mm;
}}
'''

    elif lay == "classic":
        return base + f'''.{mn}-inv-header-classic .classic-logo-row {{
    display: flex; align-items: flex-start; gap: 8mm; padding-bottom: 4mm;
}}
.{mn}-inv-header-classic .classic-company-block h2 {{
    font-size: 14pt; margin: 0 0 2mm; color: #1a1a1a;
}}
.{mn}-inv-header-classic .classic-company-block p {{ font-size: 8pt; color: #444; line-height: 1.6; margin: 0; }}
hr.classic-rule {{ border: none; border-top: 1.5pt double {pc}; margin: 2mm 0; }}
.{mn}-inv-footer-classic {{
    margin-top: 6mm; font-size: 7.5pt; color: #555;
}}
.{mn}-inv-footer-classic .bank-details {{ margin-top: 2mm; }}
'''

    elif lay == "corporate":
        return base + f'''.{mn}-inv-header-corporate .corp-banner {{
    background: {pc}; color: #fff;
    display: flex; align-items: center; gap: 8mm;
    padding: 8mm 10mm; margin: -10mm -10mm 0;
}}
.{mn}-inv-header-corporate .corp-logo img {{ filter: brightness(10) grayscale(1); max-height: 48px; }}
.{mn}-inv-header-corporate .corp-company-name {{ font-size: 20pt; font-weight: 900; margin: 0; letter-spacing: 1px; }}
.{mn}-inv-header-corporate .corp-tagline {{ font-size: 8pt; opacity: 0.8; margin: 1mm 0 0; }}
.{mn}-inv-header-corporate .corp-contact-strip {{
    background: {sc}; display: flex; gap: 6mm; flex-wrap: wrap;
    padding: 3mm 10mm; margin: 0 -10mm 6mm; font-size: 7.5pt; color: #333;
}}
.{mn}-inv-footer-corporate .corp-footer-strip {{
    background: {pc}22; border-top: 2pt solid {pc};
    padding: 3mm 0; margin-top: 6mm; font-size: 7.5pt; color: #444;
    display: flex; justify-content: space-between; flex-wrap: wrap; gap: 2mm;
}}
.corp-page {{ margin-left: auto; color: #888; }}
'''

    elif lay == "letterhead":
        mt = d.get("inv_margin_top",15)
        mb = d.get("inv_margin_bottom",10)
        return base + f'''.{mn}-inv-letterhead-top-gutter {{ height: {mt}mm; }}
.{mn}-inv-letterhead-bottom-gutter {{ height: {mb}mm; }}
.{mn}-inv-footer-letterhead {{ font-size: 7.5pt; color: #666; }}
'''

    else:  # standard / boxed — minimal overrides
        return base + f'''/* Standard / Boxed layout uses Odoo built-in styles + these overrides */
.o_report_invoice .o_company_name {{ color: {pc}; }}
.o_report_invoice table thead th {{ background: {pc}22; color: #111; }}
'''


# ─── POS BUTTON DESIGNER ─────────────────────────────────────────────────────

def _pos_buttons_js(d, version):
    mn      = d.get("name","my_module")
    cn      = "".join(w.capitalize() for w in mn.split("_"))
    buttons = d.get("pos_buttons", [])
    v_num   = float(version.split(".")[0])

    if v_num >= 16:
        # OWL v2 / modern POS (v16+)
        components = []
        registrations = []
        for btn in buttons:
            bname   = btn.get("name","Custom Button")
            bkey    = bname.lower().replace(" ","_").replace("-","_")
            bclass  = "".join(w.capitalize() for w in bkey.split("_"))
            baction = btn.get("action","custom")
            bcolor  = btn.get("color","#875A7B")
            bicon   = btn.get("icon","*")
            seq     = btn.get("sequence", 10)

            if baction == "discount":
                action_body = f'''        const order = this.pos.get_order();
        if (order) {{
            const disc = parseFloat(prompt("{bname} — enter discount %", "10") || "0");
            if (disc >= 0 && disc <= 100) order.setDiscount(disc);
        }}'''
            elif baction == "note":
                action_body = f'''        const line = this.pos.get_order()?.get_selected_orderline();
        if (line) {{
            const note = prompt("{bname} — add note:");
            if (note !== null) line.set_note(note);
        }}'''
            elif baction == "split_bill":
                action_body = '''        this.pos.showScreen("SplitBillScreen");'''
            elif baction == "price_check":
                action_body = f'''        const barcode = prompt("{bname} — scan or enter barcode:");
        if (barcode) {{
            const product = this.pos.db.get_product_by_barcode(barcode);
            if (product) alert(product.display_name + ": " + this.pos.format_currency(product.lst_price));
            else alert("Product not found.");
        }}'''
            elif baction == "custom_action":
                action_body = f'''        // TODO: implement custom action for "{bname}"
        await this.env.services.rpc("/web/dataset/call_kw", {{
            model: "pos.session",
            method: "{mn}_{bkey}_action",
            args: [this.pos.pos_session.id],
            kwargs: {{}},
        }});'''
            else:
                action_body = f'''        console.log("{bname} pressed");'''

            components.append(f'''
class {cn}{bclass}Button extends Component {{
    static template = "{mn}.{cn}{bclass}Button";
    setup() {{
        this.pos = usePos();
    }}
    async onClick() {{
{action_body}
    }}
}}
ProductScreen.addControlButton({{
    component: {cn}{bclass}Button,
    condition: () => true,
    position: ["before", "SetPricelistButton"],
}});''')

        return f'''/** @odoo-module **/
/* ──────────────────────────────────────────────────────
   {d.get("display_name",mn)} — POS Custom Buttons
   Generated by Odoo Module Generator
   Version: {version}
────────────────────────────────────────────────────── */
import {{ Component }} from "@odoo/owl";
import {{ ProductScreen }} from "@point_of_sale/app/screens/product_screen/product_screen";
import {{ usePos }} from "@point_of_sale/app/store/pos_hook";
import {{ registry }} from "@web/core/registry";
{"".join(components) if components else """
// No buttons configured. Add buttons in the POS designer tab.
// Example:
// class MyButton extends Component {
//     static template = "my_module.MyButton";
//     setup() { this.pos = usePos(); }
//     onClick() { console.log("clicked"); }
// }
// ProductScreen.addControlButton({ component: MyButton, condition: () => true });
"""}'''

    elif v_num >= 14:
        # OWL v1 (v14–v15)
        components = []
        for btn in buttons:
            bname  = btn.get("name","Custom Button")
            bkey   = bname.lower().replace(" ","_").replace("-","_")
            bclass = "".join(w.capitalize() for w in bkey.split("_"))
            components.append(f'''
const {cn}{bclass}Button = PosComponent.extend({{
    template: "{mn}.{cn}{bclass}Button",
    onClick() {{
        // TODO: implement action for "{bname}"
        const order = this.env.pos.get_order();
        console.log("{bname} pressed", order);
    }},
}});
ProductScreen.addControlButton({{
    component: {cn}{bclass}Button,
    condition: function() {{ return true; }},
}});''')

        return f'''odoo.define('{mn}.pos_buttons', function(require) {{
    "use strict";
    /* {d.get("display_name",mn)} — POS Buttons (v14/v15 OWL v1) */
    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    {"".join(components) if components else "// No buttons configured."}
}});
'''

    else:
        # Legacy v13 and below
        components = []
        for btn in buttons:
            bname  = btn.get("name","Custom Button")
            bkey   = bname.lower().replace(" ","_")
            bclass = "".join(w.capitalize() for w in bkey.split("_"))
            components.append(f'''
    var {cn}{bclass}Btn = screens.ActionButtonWidget.extend({{
        template: '{mn}_{bkey}_button',
        button_click: function() {{
            console.log("{bname} pressed");
        }},
    }});
    screens.define_action_button({{ 'name': '{bkey}', klass: {cn}{bclass}Btn }});''')

        return f'''odoo.define('{mn}.pos_buttons', function(require) {{
    "use strict";
    /* {d.get("display_name",mn)} — POS Buttons (legacy v13-) */
    var screens = require('point_of_sale.screens');
    {"".join(components) if components else "// No buttons configured."}
}});
'''


def _pos_buttons_xml(d):
    mn      = d.get("name","my_module")
    cn      = "".join(w.capitalize() for w in mn.split("_"))
    buttons = d.get("pos_buttons", [])
    version = d.get("odoo_version","17.0")
    v_num   = float(version.split(".")[0])

    templates = []
    for btn in buttons:
        bname   = btn.get("name","Custom Button")
        bkey    = bname.lower().replace(" ","_").replace("-","_")
        bclass  = "".join(w.capitalize() for w in bkey.split("_"))
        bcolor  = btn.get("color","#875A7B")
        bicon   = btn.get("icon","*")

        if v_num >= 16:
            templates.append(f'''
    <t t-name="{mn}.{cn}{bclass}Button">
        <button class="control-button {mn}-pos-btn"
                style="--btn-color:{bcolor}"
                t-on-click="onClick">
            <span class="pos-btn-icon">{bicon}</span>
            <span class="pos-btn-label">{bname}</span>
        </button>
    </t>''')
        else:
            templates.append(f'''
    <t t-name="{mn}_{bkey}_button">
        <div class="actionbutton {mn}-pos-btn" style="background:{bcolor}">
            <span>{bicon} {bname}</span>
        </div>
    </t>''')

    if not templates:
        templates.append(f'\n    <!-- No buttons configured — add buttons in the POS tab -->')

    ns = 'templates' if v_num >= 16 else 'templates xml:space="preserve"'
    return f'''<?xml version="1.0" encoding="utf-8"?>
<{ns}>
{"".join(templates)}
<!-- POS button styles -->
<t t-name="{mn}.PosButtonStyles">
<style>
.{mn}-pos-btn {{
    background: var(--btn-color, #875A7B) !important;
    color: #fff !important;
    border-radius: 6px;
    font-weight: 600;
    min-width: 80px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 3px;
    padding: 8px 10px;
    transition: filter 0.15s;
}}
.{mn}-pos-btn:hover {{ filter: brightness(1.12); }}
.{mn}-pos-btn .pos-btn-icon {{ font-size: 18px; line-height: 1; }}
.{mn}-pos-btn .pos-btn-label {{ font-size: 10px; letter-spacing: 0.3px; }}
</style>
</t>
</{ns.split()[0]}>
'''


def _pos_config_model(d):
    mn = d.get("name","my_module")
    cn = "".join(w.capitalize() for w in mn.split("_"))
    return f'''# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosConfig{cn}(models.Model):
    """Extend POS configuration for {d.get("display_name",mn)} custom buttons."""
    _inherit = "pos.config"

    {mn}_buttons_enabled = fields.Boolean(
        string="Enable {d.get("display_name",mn)} Buttons",
        default=True,
        help="Show custom buttons on the POS product screen."
    )


class PosSession{cn}(models.Model):
    """Pass button config to POS session."""
    _inherit = "pos.session"

    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        result["search_params"]["fields"].append("{mn}_buttons_enabled")
        return result
'''

def github_api(method, url, token, json_body=None):
    import urllib.request, urllib.error
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "OdooModuleGenerator/2.0"
    }
    data = json.dumps(json_body).encode() if json_body else None
    req = urllib.request.Request("https://api.github.com" + url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return json.loads(body), e.code
        except:
            return {"message": body}, e.code


# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
        versions=list(VERSION_COMPAT.keys()),
        categories=CATEGORIES,
        common_depends=COMMON_DEPENDS,
        version_compat=json.dumps(VERSION_COMPAT))

@app.route("/api/version-info/<version>")
def version_info(version):
    c = VERSION_COMPAT.get(version)
    return (jsonify(c), 200) if c else (jsonify({"error":"Unknown version"}), 404)

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.json
    # Generate primary manifest (uses data["odoo_version"])
    manifest  = generate_manifest(data)
    structure = generate_file_structure(data)

    # If multiple versions requested, generate a manifest per version
    versions = data.get("odoo_versions", [])
    manifests = {}
    if len(versions) > 1:
        for v in versions:
            vdata = {**data, "odoo_version": v}
            manifests[v] = generate_manifest(vdata)
    else:
        manifests[data.get("odoo_version", "17.0")] = manifest

    return jsonify({"manifest": manifest, "manifests": manifests, "structure": structure})

@app.route("/api/download", methods=["POST"])
def download():
    data             = request.json
    mn               = data.get("name", "my_module")
    versions         = data.get("odoo_versions", [])
    edited_files     = data.get("edited_files", {})
    edited_manifests = data.get("edited_manifests", {})

    structure = generate_file_structure(data)
    structure.update(edited_files)

    buf = io.BytesIO()
    if len(versions) > 1:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for v in versions:
                mf     = edited_manifests.get(v) or generate_manifest({**data, "odoo_version": v})
                folder = f"{v}/{mn}/"
                zf.writestr(folder + "__manifest__.py", mf)
                for fp, content in structure.items():
                    if fp != "__manifest__.py":
                        zf.writestr(folder + fp, content)
        buf.seek(0)
        return send_file(buf, mimetype="application/zip", as_attachment=True,
                         download_name=f"{mn}_bundle.zip")
    else:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for fp, content in structure.items():
                zf.writestr(mn + "/" + fp, content)
        buf.seek(0)
        return send_file(buf, mimetype="application/zip", as_attachment=True,
                         download_name=mn + ".zip")

@app.route("/api/github/validate", methods=["POST"])
def github_validate():
    """Validate GitHub token and return user info"""
    token = request.json.get("token","").strip()
    if not token:
        return jsonify({"error":"No token provided"}), 400
    resp, status = github_api("GET", "/user", token)
    if status == 200:
        return jsonify({"login": resp.get("login"), "name": resp.get("name"), "avatar_url": resp.get("avatar_url"), "valid": True})
    return jsonify({"error": resp.get("message","Invalid token"), "valid": False}), 401

@app.route("/api/github/repos", methods=["POST"])
def github_repos():
    """List user repositories"""
    token = request.json.get("token","").strip()
    resp, status = github_api("GET", "/user/repos?per_page=100&sort=updated&affiliation=owner", token)
    if status == 200:
        repos = [{"name":r["name"],"full_name":r["full_name"],"private":r["private"],"url":r["html_url"],"default_branch":r.get("default_branch","main")} for r in resp]
        return jsonify({"repos": repos})
    return jsonify({"error": resp.get("message","Failed to fetch repos")}), status

@app.route("/api/github/create-repo", methods=["POST"])
def github_create_repo():
    """Create a new GitHub repository"""
    d = request.json
    token = d.get("token","").strip()
    payload = {
        "name": d.get("repo_name"),
        "description": d.get("description",""),
        "private": d.get("private", False),
        "auto_init": False,
        "has_issues": d.get("has_issues", True),
        "has_projects": d.get("has_projects", False),
        "has_wiki": d.get("has_wiki", False),
    }
    if d.get("org"):
        resp, status = github_api("POST", "/orgs/"+d["org"]+"/repos", token, payload)
    else:
        resp, status = github_api("POST", "/user/repos", token, payload)
    if status in (200, 201):
        return jsonify({"success": True, "repo": resp.get("full_name"), "url": resp.get("html_url"), "clone_url": resp.get("clone_url")})
    return jsonify({"error": resp.get("message","Failed to create repo"), "errors": resp.get("errors",[])}), status

@app.route("/api/github/push", methods=["POST"])
def github_push():
    """Push module files to GitHub repository"""
    d = request.json
    token = d.get("token","").strip()
    module_data = d.get("module_data",{})
    repo = d.get("repo","")  # "owner/repo"
    branch = d.get("branch","main")
    commit_msg = d.get("commit_message","feat: add Odoo module via generator")
    path_prefix = d.get("path_prefix","").strip("/")

    structure = generate_file_structure(module_data)

    # Get or create branch ref
    ref_resp, ref_status = github_api("GET", f"/repos/{repo}/git/ref/heads/{branch}", token)
    if ref_status == 404:
        # Try to get default branch SHA to create new branch
        repo_resp, _ = github_api("GET", f"/repos/{repo}", token)
        default_branch = repo_resp.get("default_branch","main")
        if default_branch != branch:
            main_ref, _ = github_api("GET", f"/repos/{repo}/git/ref/heads/{default_branch}", token)
            if "object" in main_ref:
                sha = main_ref["object"]["sha"]
                github_api("POST", f"/repos/{repo}/git/refs", token, {"ref": f"refs/heads/{branch}", "sha": sha})

    results = []
    errors = []
    for filepath, content in structure.items():
        full_path = (path_prefix + "/" + filepath).lstrip("/") if path_prefix else filepath
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        # Check if file exists (to get SHA for update)
        existing, ex_status = github_api("GET", f"/repos/{repo}/contents/{full_path}?ref={branch}", token)
        payload = {
            "message": commit_msg,
            "content": encoded,
            "branch": branch
        }
        if ex_status == 200 and "sha" in existing:
            payload["sha"] = existing["sha"]

        res, st = github_api("PUT", f"/repos/{repo}/contents/{full_path}", token, payload)
        if st in (200, 201):
            results.append(filepath)
        else:
            errors.append({"file": filepath, "error": res.get("message","Unknown error")})

    return jsonify({
        "success": len(errors) == 0,
        "pushed": len(results),
        "total": len(structure),
        "errors": errors,
        "repo_url": f"https://github.com/{repo}"
    })

@app.route("/api/github/load-module", methods=["POST"])
def github_load_module():
    """Load an existing module's __manifest__.py from GitHub"""
    d = request.json
    token = d.get("token","").strip()
    repo = d.get("repo","")
    module_path = d.get("module_path","").strip("/")
    branch = d.get("branch","main")

    manifest_path = (module_path + "/__manifest__.py").lstrip("/")
    resp, status = github_api("GET", f"/repos/{repo}/contents/{manifest_path}?ref={branch}", token)
    if status != 200:
        return jsonify({"error": "Could not load manifest: " + resp.get("message","")}), 404

    content = base64.b64decode(resp["content"]).decode("utf-8")
    parsed = parse_manifest(content)
    return jsonify({"manifest_raw": content, "parsed": parsed})

@app.route("/api/parse-manifest", methods=["POST"])
def parse_manifest_route():
    """Parse a pasted __manifest__.py content into structured data"""
    content = request.json.get("content","")
    parsed = parse_manifest(content)
    return jsonify({"parsed": parsed})


@app.route("/api/import-module", methods=["POST"])
def import_module():
    """
    Accept an uploaded Odoo module as:
      - A single .zip file   (field name: 'zip')
      - Multiple folder files (field name: 'files', webkitdirectory)
    Returns: { files, parsed, checks, compat, warnings }
    """
    target_version = request.form.get("target_version", "17.0")
    file_map = {}  # relative_path -> utf-8 string

    # ── 1. Read uploaded files ─────────────────────────────────────────
    if "zip" in request.files:
        zf_data = request.files["zip"].read()
        try:
            with zipfile.ZipFile(io.BytesIO(zf_data)) as zf:
                for name in zf.namelist():
                    if name.endswith("/"):
                        continue
                    try:
                        content = zf.read(name).decode("utf-8", errors="replace")
                    except Exception:
                        content = "<binary>"
                    file_map[name] = content
        except zipfile.BadZipFile:
            return jsonify({"error": "Invalid zip file"}), 400

    elif "files" in request.files:
        for fobj in request.files.getlist("files"):
            rel = fobj.filename.replace("\\", "/")
            try:
                content = fobj.read().decode("utf-8", errors="replace")
            except Exception:
                content = "<binary>"
            file_map[rel] = content
    else:
        return jsonify({"error": "No files uploaded. Send 'zip' or 'files'."}), 400

    if not file_map:
        return jsonify({"error": "Uploaded archive is empty"}), 400

    # ── 2. Normalise paths — strip common root prefix ─────────────────
    # e.g. "my_module/models/model.py"  →  "models/model.py"
    # Find the manifest to identify the module root
    manifest_path = None
    for p in file_map:
        parts = p.replace("\\","/").split("/")
        if parts[-1] == "__manifest__.py":
            manifest_path = p
            break
    # Fallback: accept __openerp__.py for very old modules
    if not manifest_path:
        for p in file_map:
            if p.replace("\\","/").split("/")[-1] == "__openerp__.py":
                manifest_path = p
                break

    if not manifest_path:
        # Still try to do structure check with whatever we have
        module_root = ""
    else:
        parts = manifest_path.replace("\\","/").split("/")
        module_root = "/".join(parts[:-1])  # everything before __manifest__.py

    def strip_root(path):
        p = path.replace("\\","/")
        if module_root and p.startswith(module_root + "/"):
            return p[len(module_root)+1:]
        return p

    normalised = {strip_root(k): v for k, v in file_map.items()}

    # ── 3. Parse manifest ──────────────────────────────────────────────
    manifest_content = normalised.get("__manifest__.py") or normalised.get("__openerp__.py","")
    parsed = parse_manifest(manifest_content) if manifest_content else {}
    manifest_version = parsed.get("odoo_version","")

    # ── 4. Structure checks ────────────────────────────────────────────
    KNOWN_DIRS = {"models","views","controllers","report","wizard","static",
                  "security","data","demo","tests","migrations","i18n","locale","doc"}
    files_set = set(normalised.keys())
    top_dirs  = {p.split("/")[0] for p in files_set if "/" in p}

    checks = []

    def chk(name, ok, msg, level="ok"):
        checks.append({"name":name, "ok":ok,
                        "level": "ok" if ok else level, "msg":msg})

    chk("__manifest__.py present",
        "__manifest__.py" in files_set or "__openerp__.py" in files_set,
        "__manifest__.py found at module root" if manifest_path else
        "No __manifest__.py or __openerp__.py found — not a valid Odoo module",
        "error")

    chk("__init__.py present",
        "__init__.py" in files_set,
        "__init__.py found at module root" if "__init__.py" in files_set
        else "__init__.py missing — Odoo won't load the module",
        "error")

    name_ok = bool(parsed.get("name","").strip())
    chk("Manifest 'name' field",   name_ok,
        f"name = '{parsed.get('name','')}'" if name_ok else "Missing 'name' key in manifest", "error")

    ver_ok  = bool(parsed.get("version","").strip())
    chk("Manifest 'version' field", ver_ok,
        f"version = '{parsed.get('version','')}'" if ver_ok else "Missing 'version' key", "warn")

    dep_ok  = bool(parsed.get("depends"))
    chk("Manifest 'depends' field", dep_ok,
        "depends = " + str(parsed.get("depends",[])) if dep_ok else "Missing 'depends' — defaulting to [] is risky", "warn")

    lic_ok  = bool(parsed.get("license","").strip())
    chk("Manifest 'license' field", lic_ok,
        f"license = '{parsed.get('license','')}'" if lic_ok else "No 'license' key", "warn")

    inst_ok = parsed.get("installable", None)
    chk("installable = True",
        inst_ok is not False,
        "installable is True" if inst_ok else ("installable is explicitly False — module won't install" if inst_ok is False else "installable not set (defaults True)"),
        "warn")

    unknown_dirs = top_dirs - KNOWN_DIRS - {""}
    chk("No unknown top-level directories",
        len(unknown_dirs) == 0,
        "All directories follow Odoo conventions" if not unknown_dirs
        else f"Unexpected directories: {', '.join(sorted(unknown_dirs))} — may be fine but unusual",
        "warn")

    # Syntax-check all .py files (basic: try compile)
    py_errors = []
    for fp, src in normalised.items():
        if fp.endswith(".py") and src != "<binary>":
            try:
                compile(src, fp, "exec")
            except SyntaxError as e:
                py_errors.append(f"{fp}: {e}")
    chk("Python syntax (all .py files)",
        len(py_errors)==0,
        f"{sum(1 for f in files_set if f.endswith('.py'))} .py files, no syntax errors" if not py_errors
        else "; ".join(py_errors[:3]) + (" ..." if len(py_errors)>3 else ""),
        "error")

    # Check for security CSV if models present
    has_models_dir = any(p.startswith("models/") for p in files_set)
    has_security   = any("ir.model.access" in p for p in files_set)
    chk("Security ACL (ir.model.access.csv)",
        not has_models_dir or has_security,
        "security/ir.model.access.csv present" if has_security
        else ("No models/ dir — ACL not required" if not has_models_dir
              else "models/ dir found but no ir.model.access.csv — users may lack access"),
        "warn")

    # ── 5. Compatibility check vs target version ───────────────────────
    tv = target_version
    tv_num = float(tv.split(".")[0]) if tv else 17.0
    compat_info = VERSION_COMPAT.get(tv, VERSION_COMPAT["17.0"])
    compat = []

    def cmp(name, ok, msg, level="ok"):
        compat.append({"name":name,"ok":ok,"level":"ok" if ok else level,"msg":msg})

    # Version match
    if manifest_version:
        mv_num = float(manifest_version.split(".")[0]) if manifest_version else None
        version_match = (manifest_version == tv)
        cmp("Manifest version matches target",
            version_match,
            f"Manifest: {manifest_version} → target: {tv}" + ("" if version_match else f" — will need version bump to {tv}.x.x.x"),
            "warn")
    else:
        cmp("Manifest version field", False, "No version field — cannot verify compatibility", "warn")

    # assets key
    manifest_has_assets = "'assets'" in manifest_content or '"assets"' in manifest_content
    assets_valid = (tv_num >= 16) or (not manifest_has_assets)
    cmp("'assets' manifest key",
        assets_valid,
        f"'assets' key requires v16+ — target is {tv}" + ("" if assets_valid else " — use 'qweb' key instead"),
        "error" if not assets_valid else "ok")

    # qweb key
    manifest_has_qweb = "'qweb'" in manifest_content or '"qweb"' in manifest_content
    qweb_ok = not (manifest_has_qweb and tv_num >= 16)
    cmp("'qweb' manifest key deprecated",
        qweb_ok,
        f"'qweb' key is {'valid' if tv_num < 16 else 'DEPRECATED in v16+'} for target {tv}",
        "warn" if not qweb_ok else "ok")

    # cloc_exclude
    manifest_has_cloc = "cloc_exclude" in manifest_content
    cloc_ok = not (manifest_has_cloc and tv_num < 18)
    cmp("'cloc_exclude' key (v18+)",
        cloc_ok,
        f"'cloc_exclude' {'valid' if tv_num >= 18 else 'only available in v18+'} for target {tv}",
        "warn" if not cloc_ok else "ok")

    # AGPL-3
    lic = parsed.get("license","")
    agpl_ok = not (lic == "AGPL-3" and tv_num < 18)
    cmp("AGPL-3 license (v18+ only)",
        agpl_ok,
        f"License AGPL-3 {'is available' if tv_num >= 18 else 'is NOT available before v18'} in target {tv}",
        "error" if not agpl_ok else "ok")

    # Python version
    py_req = compat_info.get("python","3.10+")
    cmp(f"Python {py_req} required by {tv}",
        True,
        f"Target {tv} requires Python {py_req} — verify server environment")

    # Old API (@api.one, @api.multi)
    old_api_used = any(
        ("@api.one" in src or "@api.multi" in src)
        for fp, src in normalised.items()
        if fp.endswith(".py") and src != "<binary>"
    )
    old_api_ok = not (old_api_used and tv_num >= 14)
    cmp("Old API (@api.one / @api.multi)",
        old_api_ok,
        f"@api.one / @api.multi {'found — these were removed in v14' if old_api_used else 'not found'} — target {tv}",
        "error" if not old_api_ok else "ok")

    # OWL version heuristics
    owl_v1_used = "PosComponent" in "".join(normalised.values()) or \
                  "owl.Component" in "".join(v for k,v in normalised.items() if k.endswith(".js"))
    owl_ok = not (owl_v1_used and tv_num >= 16)
    cmp("OWL version compatibility",
        owl_ok,
        f"OWL v1 patterns {'detected — target {tv} requires OWL v2 (@odoo/owl)' if (owl_v1_used and tv_num>=16) else 'not detected'} ",
        "warn" if not owl_ok else "ok")

    # Check depends are reasonable (just flag unknown ones)
    deps = parsed.get("depends",[])
    ok_depends = {"base","mail","web","account","sale","purchase","stock","mrp","hr",
                  "project","crm","website","point_of_sale","fleet","maintenance","helpdesk",
                  "timesheet","calendar","contacts","utm","portal","product","sale_management",
                  "account_accountant","l10n_generic_coa","note","lunch","survey","gamification",
                  "payment","delivery","mrp_account","quality_control","sign","spreadsheet",
                  "discuss","knowledge","studio","im_livechat","website_sale","mass_mailing"}
    unknown_deps = [d for d in deps if d not in ok_depends and not d.startswith("l10n_")]
    cmp("Dependencies recognised",
        len(unknown_deps)==0,
        f"All {len(deps)} depend(s) recognised" if not unknown_deps
        else f"Unrecognised depend(s): {', '.join(unknown_deps[:5])} — may be custom or typos",
        "warn")

    # ── 6. Build response ──────────────────────────────────────────────
    # Only return text files (skip binary placeholders) in file list
    file_list = [{"path":k,"size":len(v),"binary": v=="<binary>"}
                 for k,v in sorted(normalised.items())]
    text_files = {k:v for k,v in normalised.items() if v != "<binary>"}

    errors   = [c for c in checks+compat if c["level"]=="error"]
    warnings = [c for c in checks+compat if c["level"]=="warn"]

    return jsonify({
        "ok":            len(errors) == 0,
        "manifest_raw":  manifest_content,
        "parsed":        parsed,
        "files":         file_list,
        "text_files":    text_files,
        "checks":        checks,
        "compat":        compat,
        "error_count":   len(errors),
        "warn_count":    len(warnings),
        "target_version":target_version,
        "module_name":   parsed.get("name",""),
    })


def parse_manifest(content):
    """Robust best-effort parse of an Odoo __manifest__.py dict."""
    result = {}
    if not content:
        return result
    try:
        # ── Simple string scalars ────────────────────────────────────
        for key in ["name","summary","author","website","category","license",
                    "currency","version"]:
            # Handles both 'key' and "key", single or double-quoted value
            m = re.search(r"""['"]\s*""" + key + r"""\s*['"]\s*:\s*u?['"](.*?)['"]""",
                          content)
            if m:
                result[key] = m.group(1).strip()

        # ── Description (may be triple-quoted) ───────────────────────
        m = re.search(r"""['"]\s*description\s*['"]\s*:\s*u?(?:'''(.*?)'''|\"\"\"(.*?)\"\"\"|'([^']*)'|"([^"]*)")""",
                      content, re.DOTALL)
        if m:
            result["description"] = next((g for g in m.groups() if g is not None), "").strip()

        # ── Price ────────────────────────────────────────────────────
        m = re.search(r"""['"]\s*price\s*['"]\s*:\s*([\d.]+)""", content)
        if m:
            result["price"] = m.group(1)

        # ── Booleans ─────────────────────────────────────────────────
        for key in ["installable", "auto_install", "application"]:
            m = re.search(r"""['"]\s*""" + key + r"""\s*['"]\s*:\s*(True|False)""", content)
            if m:
                result[key] = m.group(1) == "True"

        # ── Depends list (multi-line safe) ────────────────────────────
        m = re.search(r"""['"]\s*depends\s*['"]\s*:\s*\[([^\]]*)\]""", content, re.DOTALL)
        if m:
            result["depends"] = re.findall(r"""['"]([^'"]+)['"]""", m.group(1))

        # ── Split version → odoo_version + custom_version ─────────────
        v = result.get("version", "")
        if v:
            parts = v.split(".")
            if len(parts) >= 2:
                try:
                    float(parts[0] + "." + parts[1])
                    result["odoo_version"]   = parts[0] + "." + parts[1]
                    result["custom_version"] = ".".join(parts[2:]) if len(parts) > 2 else "1.0.0"
                except ValueError:
                    pass

        # ── Feature flags from data[] ─────────────────────────────────
        data_m = re.search(r"""['"]\s*data\s*['"]\s*:\s*\[([^\]]*)\]""", content, re.DOTALL)
        if data_m:
            df = data_m.group(1)
            result["has_security"]        = "ir.model.access" in df
            result["has_views"]           = "_views.xml"       in df
            result["has_menus"]           = "_menus.xml"       in df
            result["has_wizard"]          = "wizard"           in df
            result["has_reports"]         = "report/"          in df
            result["has_data"]            = "_data.xml"        in df
            result["has_cron"]            = "_cron.xml"        in df
            result["has_email_templates"] = "_email_templates" in df
            result["has_config"]          = "res_config_settings" in df
            result["has_pricing"]         = "_pricelists.xml"  in df
            result["has_invoice"]         = "_invoice"         in df

        result["has_js"]          = ("'assets'" in content or '"assets"' in content)
        result["pricing_enabled"] = "price" in result

    except Exception as e:
        result["_parse_error"] = str(e)
    return result


if __name__ == "__main__":
    # NOTE: port 80 requires root / CAP_NET_BIND_SERVICE on Linux
    # Run: sudo python app.py   OR   sudo setcap 'cap_net_bind_service=+ep' $(which python3)
    app.run(debug=False)
