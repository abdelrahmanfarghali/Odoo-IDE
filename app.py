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


# ─── MANIFEST GENERATOR ──────────────────────────────────────────────────────

def generate_manifest(data):
    version = data.get("odoo_version","17.0")
    compat = VERSION_COMPAT.get(version, VERSION_COMPAT["17.0"])
    module_name = data.get("name","my_module")
    mod_version = version + "." + (data.get("custom_version") or "1.0.0")
    depends = data.get("depends",["base"]) or ["base"]

    data_files = []
    if data.get("has_security"):     data_files.append("security/ir.model.access.csv")
    if data.get("has_views"):        data_files.append("views/"+module_name+"_views.xml")
    if data.get("has_menus"):        data_files.append("views/"+module_name+"_menus.xml")
    if data.get("has_wizard"):       data_files.append("wizard/"+module_name+"_wizard_views.xml")
    if data.get("has_reports"):      data_files += ["report/"+module_name+"_report.xml","report/"+module_name+"_templates.xml"]
    if data.get("has_data"):         data_files.append("data/"+module_name+"_data.xml")
    if data.get("has_cron"):         data_files.append("data/"+module_name+"_cron.xml")
    if data.get("has_email_templates"): data_files.append("data/"+module_name+"_email_templates.xml")
    if data.get("has_config"):       data_files.append("views/res_config_settings_views.xml")
    if data.get("has_pricing"):      data_files.append("data/"+module_name+"_pricelists.xml")

    demo_files = ["demo/"+module_name+"_demo.xml"] if data.get("has_demo") else []

    L = ["# -*- coding: utf-8 -*-", "{"]
    dn = data.get("display_name") or data.get("name","My Module")
    L.append("    'name': '" + dn + "',")
    L.append("    'version': '" + mod_version + "',")
    if data.get("summary"):     L.append("    'summary': '" + data["summary"].replace("'","\\'") + "',")
    if data.get("description"):
        L.append("    'description': '''")
        L.append(data["description"].replace("'","\\'"))
        L.append("    ''',")
    if data.get("author"):      L.append("    'author': '" + data["author"] + "',")
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

    if "assets" in compat["manifest_keys"] and (data.get("has_js") or data.get("has_css") or data.get("has_qweb")):
        L.append("    'assets': {")
        if data.get("has_js") or data.get("has_css"):
            L.append("        'web.assets_backend': [")
            if data.get("has_css"): L.append("            '"+module_name+"/static/src/css/"+module_name+".css',")
            if data.get("has_js"):  L.append("            '"+module_name+"/static/src/js/"+module_name+".js',")
            L.append("        ],")
        if data.get("has_qweb"):
            L.append("        'web.assets_qweb': [")
            L.append("            '"+module_name+"/static/src/xml/"+module_name+"_templates.xml',")
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
        S["models/__init__.py"] = "# -*- coding: utf-8 -*-\nfrom . import "+safe+"\n"
        ml = ["# -*- coding: utf-8 -*-","from odoo import models, fields, api","",
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
        S["wizard/__init__.py"] = "# -*- coding: utf-8 -*-\nfrom . import "+wn+"\n"
        S["wizard/"+wn+".py"] = _wizard_py(data)
        S["wizard/"+wn+"_views.xml"] = _wizard_xml(data)
    if data.get("has_controllers"):
        inits.append("controllers")
        S["controllers/__init__.py"] = "# -*- coding: utf-8 -*-\nfrom . import main\n"
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
        S["static/src/css/"+mn+".css"] = "/* "+data.get("display_name",mn)+" Styles */\n"
    if data.get("has_qweb"):
        S["static/src/xml/"+mn+"_templates.xml"] = _qweb(data)
    if data.get("has_demo"):
        S["demo/"+mn+"_demo.xml"] = '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <!-- Demo data -->\n</odoo>\n'
    S["static/description/index.html"] = _desc_html(data)
    S["__init__.py"] = "# -*- coding: utf-8 -*-\n" + ("\n".join("from . import "+i for i in inits)+"\n" if inits else "")
    return S

def _views_xml(d):
    mn = d.get("name","my_module"); ml = d.get("model_name","my.model"); mid = ml.replace(".","_")
    dn = d.get("display_name",mn)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<odoo>
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
    return f'''<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_{mn}_root" name="{dn}" sequence="100"/>
    <menuitem id="menu_{mn}_main" name="{dn}" parent="menu_{mn}_root" action="action_{mid}" sequence="10"/>
</odoo>
'''

def _security(d):
    ml = d.get("model_name","my.model"); mid = ml.replace(".","_")
    return f"id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\naccess_{mid}_user,{ml} User,model_{mid},base.group_user,1,1,1,0\naccess_{mid}_manager,{ml} Manager,model_{mid},base.group_system,1,1,1,1\n"

def _wizard_py(d):
    mn = d.get("name","my_module"); cn = "".join(w.capitalize() for w in mn.replace(" ","_").split("_"))
    return f"# -*- coding: utf-8 -*-\nfrom odoo import models, fields, api\n\nclass {cn}Wizard(models.TransientModel):\n    _name = '{mn.lower().replace(' ','_')}.wizard'\n    _description = '{d.get('display_name',mn)} Wizard'\n\n    name = fields.Char(string='Name')\n\n    def action_confirm(self):\n        return {{'type': 'ir.actions.act_window_close'}}\n"

def _wizard_xml(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); dn = d.get("display_name",mn)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<odoo>
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
    return f"# -*- coding: utf-8 -*-\nfrom odoo import http\nfrom odoo.http import request\n\nclass {cn}Controller(http.Controller):\n\n    @http.route(['/{mn}'], type='http', auth='public', website=True)\n    def index(self, **kwargs):\n        return request.render('{mn}.index_template', {{}})\n"

def _report_action(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); ml = d.get("model_name","my.model"); dn = d.get("display_name",mn)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <report id="report_{mn}" model="{ml}" string="{dn} Report" name="{mn}.report_template" file="{mn}_report" report_type="qweb-pdf"/>\n</odoo>\n'

def _report_template(d):
    return '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <template id="report_template">\n        <t t-call="web.html_container">\n            <t t-foreach="docs" t-as="doc">\n                <t t-call="web.external_layout">\n                    <div class="page"><h2><t t-esc="doc.name"/></h2></div>\n                </t>\n            </t>\n        </t>\n    </template>\n</odoo>\n'

def _cron(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); dn = d.get("display_name",mn)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <record id="ir_cron_{mn}" model="ir.cron">\n        <field name="name">{dn} Scheduled Action</field>\n        <field name="state">code</field>\n        <field name="code">model.your_cron_method()</field>\n        <field name="interval_number">1</field>\n        <field name="interval_type">days</field>\n        <field name="numbercall">-1</field>\n        <field name="active">True</field>\n    </record>\n</odoo>\n'

def _email_template(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); ml = d.get("model_name","my.model"); mid = ml.replace(".","_"); dn = d.get("display_name",mn)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <record id="email_template_{mn}" model="mail.template">\n        <field name="name">{dn} Email</field>\n        <field name="model_id" ref="model_{mid}"/>\n        <field name="subject">{dn} Notification</field>\n        <field name="body_html"><![CDATA[<p>Dear <t t-out="object.name"/>,</p><p>Notification from {dn}.</p>]]></field>\n        <field name="auto_delete" eval="True"/>\n    </record>\n</odoo>\n'

def _config_views(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); dn = d.get("display_name",mn)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <record id="res_config_settings_view_{mn}" model="ir.ui.view">\n        <field name="name">res.config.settings.view.{mn}</field>\n        <field name="model">res.config.settings</field>\n        <field name="inherit_id" ref="base_setup.action_general_configuration"/>\n        <field name="arch" type="xml">\n            <xpath expr="//div[hasclass(\'settings\')]" position="inside">\n                <div class="app_settings_block" data-string="{dn}" data-key="{mn}">\n                    <h2>{dn} Settings</h2>\n                </div>\n            </xpath>\n        </field>\n    </record>\n</odoo>\n'

def _pricelist_data(d):
    mn = d.get("name","my_module").lower().replace(" ","_"); dn = d.get("display_name",mn)
    currency = d.get("currency","EUR")
    return f'<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <!-- Pricelist configuration for {dn} -->\n    <!-- Add pricelist rules below -->\n    <!-- Example: -->\n    <!-- <record id="pricelist_{mn}_standard" model="product.pricelist">\n        <field name="name">{dn} Standard</field>\n        <field name="currency_id" ref="base.{currency.lower()}"/>\n    </record> -->\n</odoo>\n'

def _js(d, version):
    mn = d.get("name","my_module").lower().replace(" ","_"); cn = "".join(w.capitalize() for w in mn.split("_"))
    v = float(version.split(".")[0])
    if v >= 16:
        return f'/** @odoo-module **/\nimport {{ Component }} from "@odoo/owl";\nimport {{ registry }} from "@web/core/registry";\n\nclass {cn}Widget extends Component {{\n    static template = "{mn}.widget_template";\n    setup() {{}}\n}}\n\nregistry.category("view_widgets").add("{mn}_widget", {cn}Widget);\n'
    elif v >= 14:
        return f"odoo.define('{mn}.widget', function(require) {{\n    \"use strict\";\n    const {{ Component }} = owl;\n    const {{ registry }} = require(\"@web/core/registry\");\n    class {cn}Widget extends Component {{}}\n    registry.category(\"view_widgets\").add(\"{mn}_widget\", {cn}Widget);\n}});\n"
    else:
        return f"odoo.define('{mn}.js', function(require) {{\n    \"use strict\";\n    var Widget = require('web.Widget');\n    var {cn}Widget = Widget.extend({{\n        template: '{mn}_widget',\n        init: function(parent, options) {{ this._super.apply(this, arguments); }},\n        start: function() {{ return this._super.apply(this, arguments); }}\n    }});\n    return {cn}Widget;\n}});\n"

def _qweb(d):
    mn = d.get("name","my_module").lower().replace(" ","_")
    return f'<?xml version="1.0" encoding="utf-8"?>\n<templates xml:space="preserve">\n    <t t-name="{mn}.widget_template">\n        <div class="{mn}_widget"><!-- Widget content --></div>\n    </t>\n</templates>\n'

def _desc_html(d):
    dn = d.get("display_name",d.get("name","My Module")); sm = d.get("summary",""); desc = d.get("description","")
    return f'<!DOCTYPE html>\n<html>\n<head><meta charset="utf-8"/></head>\n<body>\n<h1>{dn}</h1>\n<p>{sm}</p>\n<p>{desc}</p>\n</body>\n</html>\n'


# ─── GITHUB HELPERS ──────────────────────────────────────────────────────────

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

def parse_manifest(content):
    """Best-effort parse of an Odoo manifest Python dict"""
    result = {}
    try:
        # Extract key-value pairs with regex
        patterns = {
            "name": r"['\"]name['\"]\s*:\s*['\"]([^'\"]+)['\"]",
            "version": r"['\"]version['\"]\s*:\s*['\"]([^'\"]+)['\"]",
            "summary": r"['\"]summary['\"]\s*:\s*['\"]([^'\"]+)['\"]",
            "author": r"['\"]author['\"]\s*:\s*['\"]([^'\"]+)['\"]",
            "website": r"['\"]website['\"]\s*:\s*['\"]([^'\"]+)['\"]",
            "category": r"['\"]category['\"]\s*:\s*['\"]([^'\"]+)['\"]",
            "license": r"['\"]license['\"]\s*:\s*['\"]([^'\"]+)['\"]",
            "price": r"['\"]price['\"]\s*:\s*([\d.]+)",
            "currency": r"['\"]currency['\"]\s*:\s*['\"]([^'\"]+)['\"]",
        }
        for key, pattern in patterns.items():
            m = re.search(pattern, content)
            if m: result[key] = m.group(1)

        # Booleans
        for key in ["installable","auto_install","application"]:
            m = re.search(r"['\"]"+key+r"['\"]\s*:\s*(True|False)", content)
            if m: result[key] = m.group(1) == "True"

        # Depends list
        m = re.search(r"['\"]depends['\"]\s*:\s*\[([^\]]+)\]", content, re.DOTALL)
        if m:
            deps = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
            result["depends"] = deps

        # Split version into odoo_version + custom
        v = result.get("version","")
        if v:
            parts = v.split(".")
            if len(parts) >= 2:
                result["odoo_version"] = parts[0]+"."+parts[1]
                result["custom_version"] = ".".join(parts[2:]) if len(parts) > 2 else "1.0.0"

        # Detect features from data files
        data_m = re.search(r"['\"]data['\"]\s*:\s*\[([^\]]+)\]", content, re.DOTALL)
        if data_m:
            data_files = data_m.group(1)
            result["has_security"] = "ir.model.access" in data_files
            result["has_views"] = "_views.xml" in data_files
            result["has_menus"] = "_menus.xml" in data_files
            result["has_wizard"] = "wizard" in data_files
            result["has_reports"] = "report/" in data_files
            result["has_data"] = "_data.xml" in data_files
            result["has_cron"] = "_cron.xml" in data_files
            result["has_email_templates"] = "_email_templates" in data_files
            result["has_config"] = "res_config_settings" in data_files
            result["has_pricing"] = "_pricelists.xml" in data_files

        result["has_js"] = "'assets'" in content or '"assets"' in content
        result["pricing_enabled"] = "price" in result

    except Exception as e:
        result["_parse_error"] = str(e)
    return result


if __name__ == "__main__":
    # NOTE: port 80 requires root / CAP_NET_BIND_SERVICE on Linux
    # Run: sudo python app.py   OR   sudo setcap 'cap_net_bind_service=+ep' $(which python3)
    app.run(debug=False, host="0.0.0.0", port=8060)
