# from odoo import models, api


# class SaleSubscription(models.Model):

#     _inherit = 'sale.order'

    # def set_close(self):
    #     res = super(SaleSubscription, self).set_close()
    #     branch_id = False
    #     pricelists = self.env['product.pricelist'].sudo().search(
    #         [('public_pricelist', '=', True)])
    #     for sub in self:
    #         branch_id = sub.partner_id.patient_id.branch_id
    #         related_pricelists = pricelists.filtered(lambda pricelist: branch_id in pricelist.branch_ids)
    #         pricelist = related_pricelists and related_pricelists[0]
    #         if pricelist:
    #             sub.pricelist_id = pricelist.id
    #             sub.partner_id.patient_id.property_product_pricelist = pricelist.id
    #         sub.partner_id.patient_id._compute_active_subscription()
    #     return res
    
    # @api.onchange('pricelist_id')
    # def _onchange_pricelist_id(self):
    #     for sub in self:
    #         if sub.pricelist_id:
    #             sub.partner_id.patient_id.property_product_pricelist = sub.pricelist_id.id
