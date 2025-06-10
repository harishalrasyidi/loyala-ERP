{
    'name': 'Monitoring Operasional',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Module for monitoring operational activities',
    'description': 'This module provides functionalities for monitoring operational activities for loyala garment',
    'depends': [
        'base',
        'project',
        'stock',
        'mrp'
    ],
    'data':[
        'security/ir.model.access.csv',
        'views/monitoring_operasional_views.xml'
    ],
    'installable': True,
    'application': True,
    'icon': '../monitoring_operasional/static/description/dogecoin.png',
}