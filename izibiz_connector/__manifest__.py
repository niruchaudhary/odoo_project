# -*- coding: utf-8 -*-

{
    'name': "Sanarise E-Dönüşüm (Izibiz)",
    'version': '1.0.0',
    'license': 'LGPL-3',
    'author': 'Waleed Chayeb - Sanarise',
    'website': 'https://sanarise.com.tr',
    'category': 'Integrations',
    'depends': ['base', 'account', 'web', 'account_reports'],
    'data': [
        "views/res_config_settings.xml",
        "views/account_move.xml",
        'security/ir.model.access.csv',
        'views/e_defter_views.xml',
        'views/e_defter.xml',
        'views/e_defter_wizard_views.xml',
        'views/csv_import_wizard_views.xml',
        'views/stock_picking.xml',
     ],
    'assets': {
        'web.assets_backend': [
            '/izibiz_connector/static/src/js/heder_button.js',
            '/izibiz_connector/static/src/xml/heder_button.xml',
        ],
        # 'web.assets_backend': [
        #         '/izibiz_connector/static/src/css/status_styles.css',
        #     ],
    },
    'installable': True,
    'application': True,
}

