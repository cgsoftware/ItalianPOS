# -*- coding: utf-8 -*-

from osv import osv
from tools.translate import _
from pychart.area_doc import doc
import time


class account_cash_statement(osv.osv):
    
    _inherit = 'account.bank.statement'
    
    def button_confirm_bank(self, cr, uid, ids, context=None):
        done = []
        obj_seq = self.pool.get('ir.sequence')
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            company_currency_id = st.journal_id.company_id.currency_id.id
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error !'),
                        _('Please verify that an account is defined in the journal.'))

            if not st.name == '/':
                st_number = st.name
            else:
                if st.journal_id.sequence_id:
                    c = {'fiscalyear_id': st.period_id.fiscalyear_id.id}
                    st_number = obj_seq.get_id(cr, uid, st.journal_id.sequence_id.id, context=c)
                else:
                    st_number = obj_seq.get(cr, uid, 'account.bank.statement')

            for line in st.move_line_ids:
                if line.state <> 'valid':
                    raise osv.except_osv(_('Error !'),
                            _('The account entries lines are not in valid state.'))              
                
            # da qui cambia tutto deve sommare e scrivere in contabilità una sola registrazione corrispettivi
            tot_cassa=0            
            tot_iva = {}
            tot_ricavi = {}
            for st_line in st.line_ids:
                iva,ricavo,cassa = self.legge_dati_pos(cr, uid, st_line.pos_statement_id, context)
                #import pdb;pdb.set_trace()
                tot_cassa+=cassa
                if iva:
                    for iv in iva:
                        if tot_iva.get(iv,False):
                            tot_iva[iv]['imposta']+= iva[iv]['imposta']
                            tot_iva[iv]['imponibile']+= iva[iv]['imponibile']
                        else:
                            tot_iva[iv]={}
                            tot_iva[iv]['imposta'] = iva[iv]['imposta']
                            tot_iva[iv]['imponibile'] = iva[iv]['imponibile']
                if ricavo:
                    for ric in ricavo:
                        if tot_ricavi.get(ric,False):
                            tot_ricavi[ric]+=ricavo[ric]
                        else:
                            tot_ricavi[ric]=ricavo[ric]
            if tot_iva and tot_ricavi and tot_cassa:
                #import pdb;pdb.set_trace()
                st_number = self.scrive_reg(cr, uid, st, tot_iva,tot_ricavi,tot_cassa,st.journal_id, context)
                # crea registrazione e poi deve leggere 
                            
#                # controlla analitica 
#                if st_line.analytic_account_id:
#                    if not st.journal_id.analytic_journal_id:
#                        raise osv.except_osv(_('No Analytic Journal !'),_("You have to define an analytic journal on the '%s' journal!") % (st.journal_id.name,))
#                if not st_line.amount:
#                    continue
#                st_line_number = self.get_next_st_line_number(cr, uid, st_number, st_line, context)
#                self.create_move_from_st_line(cr, uid, st_line.id, company_currency_id, st_line_number, context)

           # self.write(cr, uid, [st.id], {'name': st_number}, context=context)
           # self.log(cr, uid, st.id, _('Statement %s is confirmed, journal items are created.') % (st_number,))
            done.append(st.id)
        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)

    def scrive_reg(self,cr,uid,doc,tot_iva,tot_ricavi,tot_cassa,journal_cash_id,context):
        #import pdb;pdb.set_trace()
        move_obj= self.pool.get('account.move')
        
        riga_head = {
                     'ref':doc.name,
                     'date':doc.date,
                     'causale_id':journal_cash_id.causale_id.id,

                     }
        defa = move_obj.default_get(cr, uid, ['period_id','state','name','company_id'], context=None) 
        riga_head.update(defa)      
        value = move_obj.onchange_causale_id(cr,uid,[],journal_cash_id.causale_id.id,defa.get('period_id',False),doc.date,context)
        value['value']['ref']= doc.name+' '+  value['value']['ref']
        #riga_head['name']= value['value']['ref']
        #import pdb;pdb.set_trace()
        riga_head.update(value['value'])        
        id_reg = move_obj.create(cr,uid,riga_head,context)
        if id_reg:           
            move_head= move_obj.browse(cr,uid,id_reg)             
            scritto = self.scrive_account_move_line(cr, uid,move_head,doc,tot_iva,tot_ricavi,tot_cassa,journal_cash_id, context)
            if scritto[1]:
               #import pdb;pdb.set_trace()
               notok= move_obj.button_validate(cr,uid,[id_reg],context)
               if notok==False:
                    # DEVI SCRIVERE L'ID DI REGISTRAZIONE
                    #ok = self.pool.get('fiscaldoc.header').write(cr,uid,[doc.id],{'registrazione':id_reg})              
                    #scritto[0] = scritto[0]+ "  Documento "+ doc.name + "  CONTABILIZZATO ALLA REGISTRAZIONE "+ move_head.name +'\n'
                    pass
               else:
                     #import pdb;pdb.set_trace()
                     #scritto[0] =  scritto[0]+ "  Documento "+ doc.name + "  CONTABILIZZATO ALLA REGISTRAZIONE "+ move_head.name +' MA NON VALIDATO \n'
                     pass
        return scritto


    def scrive_account_move_line(self,cr, uid,move_head,doc,tot_iva,tot_ricavi,tot_cassa,journal_cash_id, context):
        
        def default_riga(move_head,doc):
            riga = {
                    'name': move_head.ref,
                    'period_id':move_head.period_id.id,
                    'journal_id':move_head.journal_id.id,
                    #'partner_id':doc.partner_id.id,
                    'move_id':move_head.id,
                    'date':move_head.date,
                    'ref':move_head.ref,
                    'causale_id':move_head.causale_id.id,                    
                    }
            return riga
        #riga = default_riga(move_head,doc)
        #riga['pagamento_id']=doc.pagamento_id.id
        #import pdb;pdb.set_trace()
        testo_log =''
        righe={}
        for riga_art in tot_ricavi:
                riga = default_riga(move_head,doc)
                riga['credit']=0
                riga['debit']=0
                segno = "AV"       
                if segno=="DA":
                        #segno dare
                        riga['credit']+=0
                        riga['debit']+=tot_ricavi[riga_art]
                else:
                        #segno dare
                        riga['credit']+=tot_ricavi[riga_art]     
                        riga['debit']+=0
                riga['account_id']= riga_art
               # import pdb;pdb.set_trace()
                print "riga ricavo ", riga
                id_riga = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA RICAVO
                if not id_riga:
                         flag_scritto= False
        #cicla sulle righe iva adesso e scrive le stesse
        for riga_iva in tot_iva:
            segno = move_head.causale_id.segno_conto_iva
            conto = move_head.causale_id.conto_iva.id
            codice =riga_iva
            riga['account_id']=conto
            riga['imponibile']=tot_iva[codice]['imponibile']
            riga['account_tax_id']=codice
            if segno=="DA":
             #segno dare
             riga['credit']=0
             riga['debit']=tot_iva[codice]['imposta']
            else:
             #segno dare
             riga['credit']=tot_iva[codice]['imposta']       
             riga['debit']=0
            #import pdb;pdb.set_trace()
            print "riga iva ", riga
            id_riga = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA IVA
            if not id_riga:
                 flag_scritto= False
        # scrive il conto cassa
        riga = default_riga(move_head,doc)
        segno = "DA"       
        if segno=="DA":
            #segno dare
            riga['credit']=0
            riga['debit']=tot_cassa     
        else:
            #segno dare
            riga['credit']=tot_cassa     
            riga['debit']=0
        riga['account_id']= journal_cash_id.default_credit_account_id.id
        riga['totdocumento']=tot_cassa
        
        #import pdb;pdb.set_trace()
        print "riga cassa ", riga
        id_riga = self.pool.get('account.move.line').create(cr,uid,riga) # RIGA CLIENTE
        if not id_riga:
             flag_scritto= False
        #cicla sulle righe iva adesso e scrive le stesse
            
            
        
        
        
        
        
        return [testo_log,True]


    
    
    def button_confirm_cash(self, cr, uid, ids, context=None):
        self.button_confirm_bank(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")}, context=context)

    def button_cancel(self, cr, uid, ids, context=None):
        cash_box_line_pool = self.pool.get('account.cashbox.line')
        super(account_cash_statement, self).button_cancel(cr, uid, ids, context=context)
        for st in self.browse(cr, uid, ids, context):
            for end in st.ending_details_ids:
                cash_box_line_pool.write(cr, uid, [end.id], {'number': 0})
        return True




    def legge_dati_pos(self,cr,uid,pos_order_id,contex=None):
        iva ={}
        ricavi ={}
        cassa = 0
        if pos_order_id and not pos_order_id.doc_id: # salta quello che è diventato documento di vendita
            for line in pos_order_id.lines:
                conto = self.cerca_controp(line)
                cassa += line.price_subtotal_incl
                ricavo  = line.price_subtotal
                imposta = line.price_subtotal_incl-line.price_subtotal
                righe_tasse_articolo = self.pool.get('account.fiscal.position').map_tax(cr, uid, False, line.product_id.taxes_id)
                if righe_tasse_articolo: 
                    codiva = righe_tasse_articolo[0]
                else:
                    codiva=0
                iv = iva.get(codiva,False)
                if iv:
                    iva[codiva]['imposta']+=imposta
                    iva[codiva]['imponibile']+=ricavo
                else:
                    iva[codiva]={
                                 'imposta':imposta,
                                 'imponibile':ricavo,
                                 }
                    
                co = ricavi.get(conto,False)
                if co:
                    ricavi[conto]+=ricavo
                else:
                    ricavi[conto]=ricavo
        #import pdb;pdb.set_trace()
        return iva,ricavi,cassa
    
    
    def cerca_controp(self,riga_doc):
            conto_id = False
            if riga_doc.product_id.categ_id.property_account_income_categ:
                conto_id = riga_doc.product_id.categ_id.property_account_income_categ.id
            if not conto_id:
                raise osv.except_osv(_('Error !'),
                        _('Non Esiste contropartita Valida  per "%s" ') % riga_doc.name)
                
            return conto_id
    
account_cash_statement()    