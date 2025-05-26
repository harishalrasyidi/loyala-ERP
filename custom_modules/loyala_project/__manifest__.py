# custom_modules/loyala_project/__manifest__.py
{
    'name': 'Loyala Project',
    'version': '1.0',
    'summary': 'Feasibility Check untuk Project',
    'description': 'Aplikasi untuk melakukan feasibility check pada project',
    'author': 'Loyala',
    'website': '',
    'category': 'Project',
    'sequence': 10,
    'depends': [
        'sale_management',  # quotation & order
        'mrp',              # BOM & scheduling
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/project_request_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'icon': 'loyala_project/static/description/icon.png',
    'tags': ['project', 'custom', 'feasibility'],
}
