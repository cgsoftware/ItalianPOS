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

class res_user(osv.osv):
    _inherit = "res.users"
    
    _columns = {
                'shop_id': fields.many2one('sale.shop', 'Negozio Standard', required=False),
                'magazzino_id':fields.many2one('stock.location', 'Magazzino Standard', required=False),
                'tipo_doc':fields.many2one('fiscaldoc.causalidoc', 'Documento Standard', required=False,),
                }

res_user()

class pos_order(osv.osv):
    _inherit = "pos.order"
    
    
    def _shop_get(self, cr, uid, context=None):
        """ To get  Shop  for this order
        @return: Shop id  """
        user = self.pool.get('res.users').browse(cr,uid,uid)
        res = self.pool.get('sale.shop').search(cr, uid, [])
        i = 0
        a = -1
        #import pdb;pdb.set_trace()
        if res:
            if user.shop_id:
               
               for re in res:
                   a+=1
                   if re == user.shop_id.id:
                       i=a
        if a== -1:
            return False
        else:           
            return  res[i] or False
    
    
    
    def _amount_all(self, cr, uid, ids, name, args, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_paid': 0.0,
                'amount_return':0.0,
                'amount_tax':0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for payment in order.statement_ids:
                res[order.id]['amount_paid'] +=  payment.amount
                res[order.id]['amount_return'] += (payment.amount < 0 and payment.amount or 0)
            for line in order.lines:
                val1 += line.price_subtotal
                if order.price_type != 'tax_excluded':
                    res[order.id]['amount_tax'] = reduce(lambda x, y: x+round(y['amount'], 2),
                        tax_obj.compute_inv(cr, uid, line.product_id.taxes_id,
                            line.price_unit * \
                            (1-(line.discount or 0.0)/100.0), line.qty),
                            res[order.id]['amount_tax'])
                elif line.qty != 0.0:
                    for c in tax_obj.compute_all(cr, uid, line.product_id.taxes_id, \
                                                 line.price_unit * (1-(line.discount or 0.0)/100.0), \
                                                 line.qty,  line.product_id, line.order_id.partner_id)['taxes']:
                        val += c.get('amount', 0.0)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_total'] = res[order.id]['amount_tax'] + cur_obj.round(cr, uid, cur, val1)
        return res
    
    
    _columns = {
                'doc_id':  fields.many2one('fiscaldoc.header', 'Documento', select=True),
                'amount_tax': fields.function(_amount_all, method=True, string='Taxes', digits_compute=dp.get_precision('Point Of Sale'), multi='all'),
                'amount_total': fields.function(_amount_all, method=True, string='Total', multi='all'),
                'amount_paid': fields.function(_amount_all, string='Paid', states={'draft': [('readonly', False)]}, readonly=True, method=True, digits_compute=dp.get_precision('Point Of Sale'), multi='all'),
                'amount_return': fields.function(_amount_all, 'Returned', method=True, digits_compute=dp.get_precision('Point Of Sale'), multi='all'),
                
                }


    _defaults = {

        'shop_id': _shop_get,
        
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
                'magazzino_destinazione_id': parametri.tipo_doc.deposito_destinazione_default.id,
                'causale_del_trasporto_id' : parametri.tipo_doc.causale_del_trasporto_id.id,
                'partner_id': parametri.partner_id.id,
            }
           
            testata.update(inv_ref.onchange_numdoc(cr, uid, ids, parametri.tipo_doc.id, parametri.payment_date, parametri.progr.id, numdoc)['value'])
            testata.update(inv_ref.onchange_partner_id(cr, uid, ids, order.partner_id.id, context)['value'])
            #import pdb;pdb.set_trace()
            if not testata.get('pagamento_id',False):
                    testata['pagamento_id']= order.shop_id.payment_default_id.id
#            inv_id = inv_ref.create(cr, uid, inv, context=context)  A ME SE NON CI SONO RIGHE NON CREA IL DOCUMENTO QUINDI CICLA DA SUBITO S
# SULL'ORDINE PER INSERIRE LE RIGHE DEL DOCUMENTO
            righe = []
            riga = {}
            uom = False
            
            for line in order.lines:
                riga = {
                        'product_id': line.product_id.id,                         
                }
                riga.update(inv_line_ref.onchange_articolo(cr, uid, ids, line.product_id.id, testata['listino_id'], line.qty, parametri.partner_id.id, testata['data_documento'], uom,context)['value'])
                                        
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

class pos_order_line(osv.osv):
     _inherit = "pos.order.line"


     def _amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        res = dict([(i, {}) for i in ids])
        account_tax_obj = self.pool.get('account.tax')

        self.price_by_product_multi(cr, uid, ids)
        for line in self.browse(cr, uid, ids, context=context):
            for f in field_names:
                if f == 'price_subtotal':
                    if line.discount != 0.0:
                        res[line.id][f] = line.price_unit * line.qty * (1 - (line.discount or 0.0) / 100.0)
                    else:
                        res[line.id][f] = line.price_unit * line.qty
                elif f == 'price_subtotal_incl':
                    taxes = [t for t in line.product_id.taxes_id]
                    if line.qty == 0.0:
                        res[line.id][f] = 0.0
                        continue
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    #import pdb;pdb.set_trace()
                    computed_taxes = account_tax_obj.compute_all(cr, uid, taxes, price, line.qty)
                    
                    cur = line.order_id.pricelist_id.currency_id
                    res[line.id][f] = self.pool.get('res.currency').round(cr, uid, cur, computed_taxes['total_included'])
        return res
     
     
     _columns = {
                 #'price_unit': fields.float('Unit Price', digits=(16, 2)),
                 #'price_unit': fields.function(_get_amount, method=True, string='Unit Price', store=True),
                # 'price_unit':fields.float('Unit Price',digits_compute=dp.get_precision('Sale Price')),
                 'price_subtotal': fields.function(_amount_line_all, method=True, multi='pos_order_line_amount', string='Subtotal w/o Tax'),
                 'price_subtotal_incl': fields.function(_amount_line_all, method=True, multi='pos_order_line_amount', string='Subtotal'),
                
                 }
     #def onchange_product_id(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False):
     #   
     #   product_obj = self.pool.get('product.product')
     #   riga_art = product_obj.browse(cr, uid, product_id)
     #   uom = riga_art.product_tmpl_id.uom_id
     #   
     #   import pdb;pdb.set_trace()
     #   
     #   price = self.price_by_product(cr, uid, ids, pricelist, product_id, qty, partner_id)
     #   
     #   self.write(cr, uid, ids, {'price_unit':price})
     #   
     #   pos_stot = (price * qty)
     #   return {'value': {'price_unit': price, 'price_subtotal_incl': pos_stot}}
    
     def price_by_product(self, cr, uid, ids, pricelist, product_id, qty=0, partner_id=False):
        
        if not product_id:
            return 0.0
        if not pricelist:
            raise osv.except_osv(_('No Pricelist !'),
                _('You have to select a pricelist in the sale form !\n' \
                'Please set one before choosing a product.'))
        p_obj = self.pool.get('product.product').browse(cr, uid, [product_id])[0]
        #import pdb;pdb.set_trace()
        uom_id = p_obj.product_tmpl_id.uom_id.id
        #uom_id2 = p_obj.uom_po_id.id
        price = self.pool.get('product.pricelist').price_get(cr, uid,
            [pricelist], product_id, qty or 1.0, partner_id, {'uom': uom_id})[pricelist]
        unit_price=price or p_obj.list_price
        if unit_price is False:
            raise osv.except_osv(_('No valid pricelist line found !'),
                _("Couldn't find a pricelist line matching this product" \
                " and quantity.\nYou have to change either the product," \
                " the quantity or the pricelist."))
        return unit_price
        #return {'value': {'product_uom': uom_id}} 
        
    
pos_order_line()


class account_journal(osv.osv):
    _inherit = 'account.journal'
    _columns = {
                'ip_registratore':fields.char('Ip Reg. Cassa', size=64, required=False, readonly=False),
                'porta_ftp_cassa': fields.integer('Porta Cassa'),
                'file_scontrino':fields.char('Nome File Scontrino', size=30, required=False, readonly=False), 
                }
    
account_journal()


class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'
    
    def _documento(self, cr, uid, ids, field_names, arg, context=None):
        #import pdb;pdb.set_trace()
        res={}
        for riga_pag in self.browse(cr,uid,ids,context):
            if riga_pag.pos_statement_id.doc_id:
                #import pdb;pdb.set_trace()
                res[riga_pag.id]=riga_pag.pos_statement_id.doc_id.name
            else:
                #import pdb;pdb.set_trace()
                res[riga_pag.id] = ''
        #import pdb;pdb.set_trace()
        return res
    
    
    _columns = {
                #'doc_id': fields.related('pos_statement_id','doc_id', type='many2one', relation='pos.order', string='Documento'),
                'doc_id': fields.function(_documento, method=True, type='char', size=64, string='Documento', store=True),
                                }
account_bank_statement_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
