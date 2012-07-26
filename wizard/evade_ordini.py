# -*- coding: utf-8 -*-

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

import netsvc
from osv import fields, osv
from tools.translate import _
from decimal import Decimal
import decimal_precision as dp
from DAV.davmove import MOVE

class pos_evade_ordini(osv.osv_memory):
    _name = 'pos.evade_ordini'
    _description = 'Evasione Ordini nel modulo Pos'


    def __get_posorder(self,cr, uid, context=None):
        if context is None:
            context = {}      
        active_id = context and context.get('active_id', False) or False
        if active_id:
            res=active_id
        return res
    
    def __get_partner(self,cr, uid, context=None):
        if context is None:
            context = {}      
        active_id = context and context.get('active_id', False) or False
        if active_id:
            order = self.pool.get('pos.order').browse(cr, uid, active_id, context=context)
            move_obj = self.pool.get('stock.move')
            if  order.partner_id:        
            # è il primo record deve inserire prima una testata
                res = order.partner_id.id
                   
        #import pdb;pdb.set_trace()
        return res 
    
    
    def __get_active_stock_moves(self,cr, uid, context=None):
        if context is None:
            context = {}
        
        active_id = context and context.get('active_id', False) or False
        if active_id:
            order = self.pool.get('pos.order').browse(cr, uid, active_id, context=context)
            move_obj = self.pool.get('stock.move')
            if  order.partner_id:        
                #import pdb;pdb.set_trace()
                res = []
                cerca = [('partner_id','=',order.partner_id.id)]
                move_ids = move_obj.search(cr,uid,cerca)
                if move_ids:
                 for move in move_obj.browse(cr, uid, move_ids):
                    if move.state in ('done', 'cancel'):
                        continue
                    else:           
                        res.append(self.__create_partial_move_memory(move))
            
        return res
    
    def __create_partial_move_memory(self, riga):
        
                if riga.partner_id.bloccato:
                    #import pdb;pdb.set_trace() 
                    raise osv.except_osv(_('Invalid action !'), _('CLIENTE BLOCCATO PER MOTIVI AMMINISTRATIVI !'))
                    rg_eva={}
                else:
                    rg_eva = {
                          'name':riga.name,
                          'product_id':riga.product_id.id,
                          'product_qty':riga.product_qty,
                          'qty_ship':riga.product_qty,
                          'picking_id':riga.picking_id.id,
                          'company_id':riga.company_id.id,
                          'partner_id':riga.partner_id.id,
                          'origin':riga.origin,
                          'riga_mov_id':riga.id,
                          'sale_line_id':riga.sale_line_id.id,
                          }
                 #import pdb;pdb.set_trace()
                return rg_eva
    
    _columns = {
                'pos_order_id':fields.many2one('pos.order', 'Ordine', required=True), 
                'partner_id':fields.many2one('res.partner', 'Cliente', required=True), 
                'move_ids':fields.one2many('stock.move', 'field_id', 'Righe Ordini da Evadere', required=False), 
                    }
    
    
    _defaults = {

                 'move_ids' : __get_active_stock_moves,
                 'partner_id':__get_partner,
                 'pos_order_id':__get_posorder,
 
                 }
    
    
    def view_init(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        super(pos_make_payment, self).view_init(cr, uid, fields_list, context=context)
        active_id = context and context.get('active_id', False) or False
        if active_id:
            order = self.pool.get('pos.order').browse(cr, uid, active_id, context=context)
            if not order.partner_id:
                raise osv.except_osv(_('Error!'),_(' Indicare Il Cliente  '))
        
        return True

    def check_sottoscorta(self,cr, uid, ids,context=None):
        ok = True
        #import pdb;pdb.set_trace() 
        if not context:
            context={}           
        if ids:
            testa = self.pool.get('evasione.ordini').browse(cr,uid,ids)
            testa = testa[0]
            mov_riga = self.pool.get('stock.move')
            riga1= testa.righe_da_evadere[0]
            company_id = riga1.partner_id.company_id
            if company_id.flag_no_neg: 
                for riga in testa.righe_da_evadere:
                    if riga.product_id.type=='product':
                        context['location']= mov_riga.browse(cr,uid,riga.riga_mov_id).location_id.id
                        if riga.product_id.qty_available-riga.qty_ship <0:
                            ok=False
        return ok
  
    def genera(self, cr, uid, ids, context=None):
        if self.check_sottoscorta(cr, uid, ids, context):
            testa = self.browse(cr,uid,ids)
            if testa.move_ids:
                for move in testa.move_ids:
                    riga = {
                            'name': fields.char('Line Description', size=512),
                            'company_id': fields.many2one('res.company', 'Company', required=True),
                            'notice': fields.char('Discount Notice', size=128, required=True),                            
                            'product_id': move.product_id.id,
                            'price_unit': move.sale_line_id.price_unit,
                            'qty': qty_ship,                            
                            'discount': fields.float('Discount (%)', digits=(16, 2)),
                            'order_id': testa.pos_order_id.id,                            
                            }
                     
                    id_line_pos = self.pool.get('pos.order.line').create(cr,uid,riga)
                    ok = self.pool.get('pos.order').write(cr,uid,[testa.pos_order_id.id],{'picking_id':MOVE.picking_id.id,'pickings':MOVE.picking_id.id})
        return {'type': 'ir.actions.act_window_close'}
    
pos_evade_ordini()


class pos_evasione_ordini_righe(osv.osv_memory):
    _name = 'pos_evasione.ordini.righe'
    _description = 'Legge tutte le righe di un cliente da evadere'
    _columns = {
                'consegna':fields.boolean('Consegna'), 
                'name': fields.char('Name', size=64, required=True, select=True),
                'testa': fields.many2one('pos.evade_ordini', 'Tipo Documento', required=True, ondelete='cascade', select=True,),
                'product_id': fields.many2one('product.product', 'Articolo', required=True, select=True, domain=[('type','<>','service')]),
                'product_qty': fields.float('Qta Prevista', digits_compute=dp.get_precision('Product UoM'), required=True,),
                'qty_ship':fields.float(("in Consegna"),digits_compute=dp.get_precision('Product UoM'),required=True),
                'picking_id': fields.many2one('stock.picking', 'Referimeti', select=True),        
                'company_id': fields.many2one('res.company', 'Azienda', required=True, select=True),
                'partner_id': fields.related('picking_id','address_id','partner_id',type='many2one', relation="res.partner", string="Cli/For", store=True, select=True),
                'backorder_id': fields.related('picking_id','backorder_id',type='many2one', relation="stock.picking", string="Back Order", select=True),
                'origin': fields.related('picking_id','origin',type='char', size=64, relation="stock.picking", string="Origine", store=True),
                'riga_mov_id':fields.float("id riga mov"),
                'sale_line_id': fields.many2one('sale.order.line', 'Sales Order Line', ondelete='set null', select=True),
         
    }
    
    
     
pos_evasione_ordini_righe()    
