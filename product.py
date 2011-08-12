# -*- encoding: utf-8 -*-
import netsvc
import pooler, tools
import math

from tools.translate import _

from osv import fields, osv



class product_multicode(osv.osv):
    _name = 'product.multicode'
    _description = 'Codici aggiuntivi per prodotto'
    
    _columns = {
                 'product_id': fields.many2one('product.product', 'Articolo', required=True, ondelete='cascade', select=True),
                 'codice_aggiuntivo': fields.char('BarCode', size=128, required=True),
                 'stampa_etich':fields.boolean('Stampa Etichetta'),
                 }
    

product_multicode()

class product_product(osv.osv):
    _inherit = 'product.product'
    
    _columns = {
                'righe_codici': fields.one2many('product.multicode', 'product_id', 'Righe Codici Aggiuntivi', required=False),
                }

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        #import pdb;pdb.set_trace()
        result = super(product_product, self).name_search(cr, user, name, args, operator, context, limit)
        if not result:
            # NON HA TROVATO NULLA CON LE REGOLE STANDARD ORA CERCA SUI CODICI AGGIUNTIVI
            id_codice = self.pool.get('product.multicode').search(cr, user, [('codice_aggiuntivo', '=', name)])
            if id_codice:
                # ha trovato delle righe dovrebbe essere sempre e comunque una
                ids = self.pool.get('product.multicode').browse(cr, user, id_codice)[0].product_id.id
                ids = [ids]                
                result = self.name_get(cr, user, ids, context=context)

        return result
    
    
    def _check_codice(self, cr, uid, ids, context=None):
        ok = True
     #   for product in self.browse(cr, uid, ids, context=context):
     #       for riga_cod in product.righe_codici:
     #           name = riga_cod.codice_aggiuntivo
     #           result = self.name_search(cr, uid, name)
     #           if result:
     #             #  ok = False
        pass
                    

        return ok


    _constraints = [(_check_codice, 'Codice Non valido o Presente in altro Articolo', ['Codici Aggiuntivi'])]  
product_product()

