# custom_modules/loyala_project/__manifest__.py
{
    'name': 'Check Harga',
    'version': '2.0',
    'summary': 'Check Harga dan Feasibility Project',
    'description': 'Aplikasi untuk melakukan check harga dan feasibility check pada project',
    'author': 'Loyala',
    'website': '',
    'category': 'Project',
    'sequence': 10,
    'depends': [
        'sale_management',  # quotation & order
        'mrp',              # BOM & scheduling
        'stock',            # inventory management
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
