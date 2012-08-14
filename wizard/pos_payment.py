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

from osv import osv, fields
from tools.translate import _
import ftplib
import os
import sys
import traceback




class pos_make_payment(osv.osv_memory):
    _inherit = 'pos.make.payment'
    _columns = {
                'tipo_doc':fields.many2one('fiscaldoc.causalidoc', 'Tipo Doc.'),
                'progr':fields.many2one('fiscaldoc.tipoprogressivi', 'Progressivo'),
                'incassato': fields.float('Incassato', digits=(16,2), required= True),
                'abbuono': fields.float('Abbuono', digits=(16,2), required= False),
                'st_scontrino':fields.boolean('Stampa Scontrino', required=False), 
                }
    
    _defaults = {  
        'st_scontrino': True,
        }
    
    def cerca_causale(self, cr, uid, fields, context):
        #import pdb;pdb.set_trace()
        causali = self.pool.get('fiscaldoc.causalidoc').search(cr, uid, [('tipo_documento', '=', 'FA')])
        return causali[0]
    
    def cerca_prog(self, cr, uid, fields, res, context):
        #import pdb;pdb.set_trace()
        if 'tipo_doc' in fields:
            prog_id = self.pool.get('fiscaldoc.causalidoc').browse(cr, uid, [res['tipo_doc'] ])[0].progr_id_default.id
        return prog_id

    
    def default_get(self, cr, uid, fields, context=None):
       res = super(pos_make_payment, self).default_get(cr, uid, fields, context)
       if 'tipo_doc' in fields:
                res['tipo_doc'] = self.cerca_causale(cr, uid, fields, context) or False
       if 'progr' in fields:
            res['progr'] = self.cerca_prog(cr, uid, fields, res, context) or False  
       return res
   
    def changed_causale(self, cr, uid, ids, tipo_doc):
       # import pdb;pdb.set_trace()
       if tipo_doc:
           prog_id = self.pool.get('fiscaldoc.causalidoc').browse(cr, uid, [tipo_doc ])[0].progr_id_default.id
           return {'value': {'progr':prog_id}}
       
    def check(self, cr, uid, ids, context=None):
        #import pdb;pdb.set_trace()
        """Check the order:
        if the order is not paid: continue payment,
        if the order is paid print invoice (if wanted) or ticket.
        """
        param = self.browse(cr, uid, ids)[0]
        journal = self.pool.get('account.journal').browse(cr,uid,param.journal)
        order_obj = self.pool.get('pos.order')
        if context is None:
            context = {}
        active_id = context and context.get('active_id', False)
        order = order_obj.browse(cr, uid, active_id, context=context)
        amount = order.amount_total - order.amount_paid
        data = self.read(cr, uid, ids, context=context)[0]
        if data['is_acc']:
            amount = self.pool.get('product.product').browse(cr, uid, data['product_id'], context=context).list_price

        if amount != 0.0:
            order_obj.write(cr, uid, [active_id], {'invoice_wanted': data['invoice_wanted'], 'partner_id': data['partner_id']}, context=context)
            order_obj.add_payment(cr, uid, active_id, data, context=context)

        if order_obj.test_paid(cr, uid, [active_id]):
            #import pdb;pdb.set_trace()
            if data['partner_id'] and data['invoice_wanted']:
                #import pdb;pdb.set_trace()
                context.update({'param_id':ids})
                # order_obj.create_picking(cr, uid, [active_id], context=context)
                id_fatt = order_obj.action_invoice(cr, uid, [active_id], context=context) # modificata la chiamata gli manda anche le info di memoria               
                context.update({'active_ids':order.doc_id.id})
                if context.get('return', False):
                    order_obj.write(cr, uid, [active_id], {'state':'done'}, context=context)
                else:
                    
                    order_obj.write(cr, uid, [active_id], {'state':'invoiced'}, context=context)
                return self.create_invoice(cr, uid, id_fatt, context=context)
                # 
            else:
                #import pdb;pdb.set_trace()
                context.update({'flag': True})
                order_obj.action_paid(cr, uid, [active_id], context=context)
                if context.get('return', False):
                    order_obj.write(cr, uid, [active_id], {'state':'done'}, context=context)
                else:
                    order_obj.write(cr, uid, [active_id], {'state':'paid'}, context=context)
                if journal.file_scontrino and param.st_scontrino:
                #
                    return  self.emetti_scontrino(cr, uid, ids,amount, context=context)
                else:
                    return self.print_report(cr, uid, ids, context=context)
        else:
            
            #import pdb;pdb.set_trace()
            pass
        #import pdb;pdb.set_trace()
        context.update({'flag': True})
        # Todo need to check
        order_obj.action_paid(cr, uid, [active_id], context=context)
        order_obj.write(cr, uid, [active_id], {'state': 'advance'}, context=context)
        if journal.file_scontrino and param.st_scontrino:
                #
                 #   return  self.emetti_scontrino(cr, uid, ids,amount, context=context)
                 return {'type': 'ir.actions.act_window_close'} 
        else:
                    return self.print_report(cr, uid, ids, context=context)
    
    
    def emetti_scontrino(self, cr, uid, ids,amount, context=None):
        #import pdb;pdb.set_trace()
        param = self.browse(cr, uid, ids)[0]
        journal = self.pool.get('account.journal').browse(cr,uid,param.journal)
        
        order_obj = self.pool.get('pos.order')
        
        if context is None:
            context = {}
        active_id = context and context.get('active_id', False)
        order = order_obj.browse(cr, uid, active_id, context=context)
        #amount = order.amount_total - order.amount_paid
        #scontr = """OPENSF \r\n """
        scontr = """"""
        for riga in order.lines:
            importo = riga.price_subtotal_incl
            #import pdb;pdb.set_trace()
            record = "PLU,"
            record += riga.product_id.name[:15]+ ","
            record += str(round(riga.price_subtotal_incl/riga.qty,2))+ ",1,"
            record += str(int(riga.qty)) + "\r\n "
            scontr += record
        scontr += "CASH \r\n"
        ret_file_name = '/home/openerp/scontrini/'  +journal.file_scontrino+".txt"
        fp = open(ret_file_name, 'wb+')
        fp.write(scontr)
        fp.close()
        # ha scritto il file, bisogna capire se il nome è lo stesso per le varie postazioni     
        # e quindi bisognerà rinominarlo in fase fi ftp   
        #import pdb;pdb.set_trace()
        ftp = ftplib.FTP()
        ftp.connect(journal.ip_registratore, journal.porta_ftp_cassa)
        print ftp.getwelcome()    
        try:
            try:
                ftp.login('giuseppe', 'Cristina1507')
                #ftp.cwd(some_directory)
                # move to the desired upload directory
                print "Currently in:", ftp.pwd()
                print "Uploading..."+ ret_file_name,
                fullname = ret_file_name
                name = os.path.split(fullname)[1]
                f = open(fullname, "rb")
                ftp.storbinary('STOR ' + name, f)
                f.close()
                print "OK"        
                print "Files:"
                #print ftp.retrlines('LIST')
            finally:
                print "Quitting... "
                ftp.quit()
        except:
            traceback.print_exc()            
        return {'type': 'ir.actions.act_window_close'}   

 


    def create_invoice(self, cr, uid, ids, context=None):
        """
          Create  a invoice
        """
        if context is None:
            context = {}        
        param = self.browse(cr, uid, ids)[0]    
        data = {}
        data['ids'] = context.get('active_ids', [])
        if data['ids']:
            data['ids'] = [data['ids']]
        
        doc = self.pool.get('fiscaldoc.header').browse(cr, uid, data['ids'])[0]
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = {'danr':doc.name,
                        'anr':doc.name,
                        'dadata':doc.data_documento,
                  'adata':doc.data_documento,
                  'sconto':1,
                  'prezzi':1,
                  'agente':0,
                  'name':doc.name
                  }
        used_context = {'danr':doc.name,
                        'anr':doc.name,
                        'dadata':doc.data_documento,
                  'adata':doc.data_documento,
                  'sconto':1,
                  'prezzi':1,
                  'agente':0,
                  'name':doc.name
                  }
        data['form']['parameters'] = used_context
        fatture = self.pool.get('fiscaldoc.header')
        active_ids = context and context.get('active_ids', [])
        Primo = True
        if active_ids:
            for doc in fatture.browse(cr, uid, [active_ids], context=context):
                if Primo:
                    Primo = False
                    IdTipoSta = doc.tipo_doc.id
                    TipoStampa = doc.tipo_doc.tipo_modulo_stampa.report_name
                #import pdb;pdb.set_trace()
                else:
                  if IdTipoSta <> doc.tipo_doc.id:
                      raise osv.except_osv(_('ERRORE !'), _('Devi Selezionare documenti con la stessa Causale Documento'))
        #import pdb;pdb.set_trace()
        return {
                'type': 'ir.actions.report.xml',
                'report_name': TipoStampa,
                'datas': data,
            }

       

pos_make_payment()
