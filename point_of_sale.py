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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

import netsvc
from osv import fields, osv
from tools.translate import _
from decimal import Decimal
import decimal_precision as dp


class FiscalDocHeader(osv.osv):
   _inherit = "fiscaldoc.header"
   _columns = {
               'pos_order_id': fields.many2one('pos.order', 'Vendita Al Banco'),
               }
   
FiscalDocHeader()


class FiscalDocRighe(osv.osv):
   _inherit = "fiscaldoc.righe"

   _columns = {
               'pos_order_line_id': fields.many2one('pos.order.line', 'Riga Vendita Al Banco'),
               }

FiscalDocRighe()


class pos_order(osv.osv):
    _inherit = "pos.order"
    
    _columns = {
                'doc_id':  fields.many2one('fiscaldoc.header', 'Documento', select=True),
                }


    def action_invoice(self, cr, uid, ids, context=None):
        #import pdb;pdb.set_trace()
        param_id = context.get('param_id', False)
        """Create a invoice of order  """
        parametri = self.pool.get('pos.make.payment').browse(cr, uid, param_id)[0]
        inv_ref = self.pool.get('fiscaldoc.header')
        inv_line_ref = self.pool.get('fiscaldoc.righe')
        product_obj = self.pool.get('product.product')
        inv_ids = []
        
        for order in self.pool.get('pos.order').browse(cr, uid, ids, context=context):
            if order.doc_id: # questo controllo server a saltare le righe fatturate 
                inv_ids.append(order.doc_id.id) # va cambiata la definizione del campo in modo che punti ai fiscaldoc e non ad account.invoice
                continue

            if not order.partner_id:
                raise osv.except_osv(_('Error'), _('Inserire il Cliente'))

            acc = order.partner_id.property_account_receivable.id
            numdoc = inv_ref.trova_numdoc(cr, uid, ids, parametri.tipo_doc.id, parametri.payment_date, parametri.progr.id)
            
            testata = {
                'data_documento': parametri.payment_date,
                'tipo_doc': parametri.tipo_doc.id,
                'progr': parametri.progr.id,
                'numdoc': numdoc,
                'magazzino_id' : parametri.tipo_doc.deposito_default.id,
                'causale_del_trasporto_id' : parametri.tipo_doc.causale_del_trasporto_id.id,
                'partner_id': parametri.partner_id.id,
            }
           
            testata.update(inv_ref.onchange_numdoc(cr, uid, ids, parametri.tipo_doc.id, parametri.payment_date, parametri.progr.id, numdoc)['value'])
            testata.update(inv_ref.onchange_partner_id(cr, uid, ids, order.partner_id.id, context)['value'])
#            inv_id = inv_ref.create(cr, uid, inv, context=context)  A ME SE NON CI SONO RIGHE NON CREA IL DOCUMENTO QUINDI CICLA DA SUBITO S
# SULL'ORDINE PER INSERIRE LE RIGHE DEL DOCUMENTO
            righe = []
            riga = {}
            uom = False
            
            for line in order.lines:
                riga = {
                        'product_id': line.product_id.id,
                         
                }
                riga.update(inv_line_ref.onchange_articolo(cr, uid, ids, line.product_id.id, testata['listino_id'], line.qty, parametri.partner_id.id, testata['data_documento'], uom)['value'])
                riga.update({                       
                             'quantity': line.qty,
                        'product_uom_qty':line.qty,
                        'product_uos_qty':line.qty,
                        'product_prezzo_unitario':line.price_unit,
                        'discount_riga':line.discount,
                        'prezzo_netto':line.price_unit - line.price_ded,
                        'totale_riga':line.price_subtotal, })
                righe.append((0, 0, riga))
            vals = testata
            # import pdb;pdb.set_trace()
            vals.update({'righe_articoli':righe})
            inv_id = inv_ref.create(cr, uid, vals, context)
            picking_id = inv_ref.browse(cr, uid, inv_id).picking_ids.id         
            self.write(cr, uid, [order.id], {'doc_id': inv_id, 'state': 'invoiced', 'picking_id':picking_id}, context=context)
            inv_ids.append(inv_id)
                    
# NON SERVE                inv_line_ref.create(cr, uid, inv_line, context=context)
        # qui lavorava sul workflow delle fatture vecchie        
      #  for i in inv_ids:
      #      wf_service = netsvc.LocalService("workflow")
      #      wf_service.trg_validate(uid, 'account.invoice', i, 'invoice_open', cr)
        return inv_ids
        
pos_order()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
