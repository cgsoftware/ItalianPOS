# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Italian Point of Sale',
    'version': '1.0',
    'category': 'Generic Modules/Sales & Purchases',
    'description': """
Main features :
 - Questo modulo adatta il Point of Sale per la gestione 
   di un punto vendita in Italia
    """,
    'author': 'CgSoftware S.a.s.',
    'depends': ['sale', 'delivery', 'ItalianFiscalDocument'],
    'update_xml': ['pos_it_view.xml',
                   'wizard/pos_payment.xml',
                   'wizard/evade_ordini.xml',
                   'res_user.xml',
                   'account_cash_statement.xml',
                   'security/ir.model.access.csv'],
    #'demo_xml': ['point_of_sale_demo.xml','account_statement_demo.xml'],
    #'test': ['test/point_of_sale_test.yml',
    #        'test/point_of_sale_report.yml',
    #],
    'installable': True,
    
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
