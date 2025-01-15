from odoo import models, fields, api
from odoo.exceptions import ValidationError

class DocMgtConfigWizard(models.TransientModel):
    _name = "doc.mgt.config.wizard"
    _description = "Document Management Configuration"
    
    def _default_doc_mgt_config_id(self):
        return self.env['doc.mgt.config'].search([], limit=1).id
        
    doc_mgt_config_id = fields.Many2one("doc.mgt.config", default="_default_doc_mgt_config_id")
    def _default_memo_type_id(self):
        if self.doc_mgt_config_id.memo_type_id:
            return self.doc_mgt_config_id.memo_type_id
        else:
            return False
    
    memo_type_id = fields.Many2one("memo.type", compute="_compute_memo_type_id", inverse="_inverse_memo_type_id")
    
    memo_config_ids = fields.Many2many("memo.config",
                                       "memo_config_wizard_rel",
                                       "doc_mgt_config_wizard_id",
                                       "memo_config_ids",
                                        string="Memo Configurations", 
                                        domain="[('memo_type', '=', memo_type_id)]")
   
    @api.depends('doc_mgt_config_id.memo_type_id')
    def _compute_memo_type_id(self):
        self.ensure_one()
        if self.doc_mgt_config_id:
            self.memo_type_id = self.doc_mgt_config_id.memo_type_id if  self.doc_mgt_config_id.memo_type_id else False
        else:
            self.memo_type_id = False

    def _inverse_memo_type_id(self):
        self.ensure_one()
        if not self.doc_mgt_config_id and self.memo_type_id:
            rec = self.env["doc.mgt.config"].search([('memo_type_id', '=', self.memo_type_id.id)], limit=1).id
            if rec:
                self.doc_mgt_config_id = rec
            else:
                self.doc_mgt_config_id = self.env['doc.mgt.config'].create({'memo_type_id': self.memo_type_id.id}).id

    
    @api.onchange('memo_type_id')
    def onchange_memo_configs(self):
        if self.memo_type_id:
            self.memo_config_ids = [(6, 0, self.env['memo.config'].search([('memo_type', '=', self.memo_type_id.id)]).ids)]
        else:
            self.memo_config_ids = False

    def close_memo_config_wizard(self):
        if self.memo_type_id:
            if not self.doc_mgt_config_id:
                rec = self.env['doc.mgt.config'].search([], limit=1).write({'memo_type_id': self.memo_type_id.id})
                if not rec:
                    rec = self.env['doc.mgt.config'].create({'memo_type_id': self.memo_type_id.id})
                self.doc_mgt_config_id = rec
                return
            elif self.doc_mgt_config_id and (self.memo_type_id != self.doc_mgt_config_id.memo_type_id):
                 self.env['doc.mgt.config'].write({'memo_type_id': self.memo_type_id.id})
                 return
            else:
                return

        else:
            return

    @api.model
    def default_get(self, fields):
        res = super(DocMgtConfigWizard, self).default_get(fields)
        rec = self.env['doc.mgt.config'].search([], limit=1)
        if rec:
            rec_dict = {'doc_mgt_config_id': rec.id}
            if rec.memo_type_id:
                rec_dict.update({'memo_type_id': rec.memo_type_id.id})
            res.update(rec_dict)
        return res