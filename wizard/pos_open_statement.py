# -*- coding: utf-8 -*-

from osv import osv
from tools.translate import _

class pos_open_statement(osv.osv_memory):
    _inherit = 'pos.open.statement' 
  
    def open_statement(self, cr, uid, ids, context=None):
        """
             Open the statements
             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param context: A standard dictionary
             @return : Blank Directory
        """
        data = {}
        mod_obj = self.pool.get('ir.model.data')
        statement_obj = self.pool.get('account.bank.statement')
        sequence_obj = self.pool.get('ir.sequence')
        journal_obj = self.pool.get('account.journal')
        if context is None:
            context = {}
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        cr.execute("SELECT DISTINCT journal_id FROM pos_journal_users "
                    "WHERE user_id = %s ORDER BY journal_id"% (uid, ))
        j_ids = map(lambda x1: x1[0], cr.fetchall())
        journal_ids = journal_obj.search(cr, uid, [('auto_cash', '=', True), ('type', '=', 'cash'), ('id', 'in', j_ids)], context=context)

        for journal in journal_obj.browse(cr, uid, journal_ids, context=context):
            ids = statement_obj.search(cr, uid, [('state', '!=', 'confirm'), ('user_id', '=', uid), ('journal_id', '=', journal.id)], context=context)
            if len(ids):
                raise osv.except_osv(_('Message'), _('You can not open a Cashbox for "%s".\nPlease close its related cash register.') %(journal.name))

            number = ''
            if journal.sequence_id:
                number = sequence_obj.get_id(cr, uid, journal.sequence_id.id)
            else:
                number = sequence_obj.get(cr, uid, 'account.cash.statement')

            data.update({'journal_id': journal.id,
                         'company_id': company_id,
                         'user_id': uid,
                         'state': 'draft',
                         'name': number })
            #import pdb;pdb.set_trace()
            statement_id = statement_obj.create(cr, uid, data, context=context)
            ok = self.cash_iniziale(cr, uid, statement_id,journal, context=context)
            statement_obj.button_open(cr, uid, [statement_id], context)

        tree_res = mod_obj.get_object_reference(cr, uid, 'account', 'view_bank_statement_tree')
        tree_id = tree_res and tree_res[1] or False
        form_res = mod_obj.get_object_reference(cr, uid, 'account', 'view_bank_statement_form2')
        form_id = form_res and form_res[1] or False
        search_id = mod_obj.get_object_reference(cr, uid, 'point_of_sale', 'view_pos_open_cash_statement_filter')

        return {
            'domain': "[('state', '=', 'open'),('user_id', '=', "+ str(uid) +")]",
            'name': 'Open Statement',
            'view_type': 'form',
            'view_mode': 'tree, form',
            'search_view_id': search_id and search_id[1] or False ,
            'res_model': 'account.bank.statement',
            'views': [(tree_id, 'tree'), (form_id, 'form')],
            'context': {'search_default_open': 1},
            'type': 'ir.actions.act_window'
        }
        
    def cash_iniziale(self, cr, uid, statement_id,journal, context=None): 
        statement_obj = self.pool.get('account.bank.statement')    
        if statement_id:
            registro=statement_obj.browse(cr,uid,statement_id)
            ids_giornali = statement_obj.search(cr, uid, [('state', '=', 'confirm'), ('user_id', '=', uid), ('journal_id', '=', journal.id),('closing_date','<=',registro.date)],order="closing_date desc", context=context)
            if ids_giornali:
                ids_giornali = ids_giornali[0]
                chiuso = statement_obj.browse(cr,uid,ids_giornali)
                if chiuso.ending_details_ids:
                    # cancella le righe che ha memorizzato di default
                    for ape in registro.starting_details_ids:
                        ok = self.pool.get('account.cashbox.line').unlink(cr,uid,[ape.id])
                    for riga_chiusa in chiuso.ending_details_ids:
                        riga_ape = {
                                  'number':riga_chiusa.number,
                                  'pieces':riga_chiusa.pieces,
                                  'subtotal':riga_chiusa.subtotal,
                                  'starting_id':statement_id,
                                  }
                        id_riga = self.pool.get('account.cashbox.line').create(cr,uid,riga_ape)
                    ok = statement_obj.write(cr,uid,[statement_id],{'balance_start':chiuso.balance_end})
                        
                
            
        return True   
    
pos_open_statement()
  