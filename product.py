# -*- encoding: utf-8 -*-
import netsvc
import pooler, tools
import math

from tools.translate import _

from osv import fields, osv

class product(osv.osv):
    _inherit='product.product'
    
    _columns = {
                'codici_agg':fields.many2one('product.ean','Codice di collegamento alla tabella EAN'),
                #'EAN':fields.char('Codice EAN',size=100,required=True),
                }
product()

class codici_ean(osv.osv):
    _name = 'product.codici'
    _description = 'Codici aggiuntivi per prodotto'
    
    _columns = {
                 'name':fields.char('Nome Codifica',size=15,required=True),
                 'ean': fields.char('EAN13', size=13),
                 
                 }
    
def _check_ean_key(self, cr, uid, ids, context=None):
        for product in self.browse(cr, uid, ids, context=context):
            res = check_ean(product.ean.ean)
        return res

_constraints = [(_check_ean_key, 'Error: Invalid ean code', ['ean13'])]

def check_ean(eancode):
    if not eancode:
        return True
    if len(eancode) <> 13:
        return False
    try:
        int(eancode)
    except:
        return False
    oddsum=0
    evensum=0
    total=0
    eanvalue=eancode
    reversevalue = eanvalue[::-1]
    finalean=reversevalue[1:]

    for i in range(len(finalean)):
        if is_pair(i):
            oddsum += int(finalean[i])
        else:
            evensum += int(finalean[i])
    total=(oddsum * 3) + evensum

    check = int(10 - math.ceil(total % 10.0)) %10

    if check != int(eancode[-1]):
        return False
    return True

codici_ean()

