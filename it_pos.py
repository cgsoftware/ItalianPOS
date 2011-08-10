# -*- encoding: utf-8 -*-

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

import netsvc
from osv import fields, osv
from tools.translate import _
from decimal import Decimal
import decimal_precision as dp

class pos_order_line(osv.osv):
    
    _inherit = "pos.order.line"
    
    def onchange_product_id(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False):
        
        import pdb;pdb.set_trace()
        
        res = super (pos_order_line, self).onchange_product_id(cr, uid, ids, pricelist, product_id, qty=0, partner_id=False)
        
        product_obj = self.pool.get('product.product').browse(cr, uid, product_id)
        
        codici_agg = product_obj.codici_agg.ean
        
        
        if codici_agg:
            product = product_obj.read(cr, uid, product_id)
            product_name = product[0]['name']
            price = self.price_by_product(cr, uid, 0, pricelist_id[0]['pricelist_id'][0], product_id[0], 1)
            vals = {'product_id': product_id,
                    'price_unit': price,
                    'qty': qty,
                    'name': product_name,
                    'order_id': order,
            }
            line_id = self.create(cr, uid, vals)
        else:
            warning = {
                                    'title': 'ATTENZIONE !',
                                    'message':'Codice non trovato',
                                    
                                    }      
        return {'warning': warning}
        
        
        #if product_id:    
pos_order_line()