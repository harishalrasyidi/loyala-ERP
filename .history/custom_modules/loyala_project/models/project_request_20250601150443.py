from odoo import api, fields, models

class ProductPriceEstimation(models.Model):
    _name = 'product.price.estimation'
    _description = 'Product Price Estimation'

    name = fields.Char(string='Estimation Name', required=True, default='New')
    product_id = fields.Many2one('product.product', string='Reference Product', required=True)
    component_line_ids = fields.One2many('product.price.estimation.line', 'estimation_id', 
                                        string='Components')
    total_price = fields.Float(string='Total Price', compute='_compute_total_price', store=True)

    @api.depends('component_line_ids.subtotal')
    def _compute_total_price(self):
        for estimation in self:
            estimation.total_price = sum(line.subtotal for line in estimation.component_line_ids)

class ProductPriceEstimationLine(models.Model):
    _name = 'product.price.estimation.line'
    _description = 'Product Price Estimation Line'

    estimation_id = fields.Many2one('product.price.estimation', string='Estimation', 
                                    required=True, ondelete='cascade')
    component_id = fields.Many2one('product.product', string='Component', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    price = fields.Float(string='Price', compute='_compute_price', store=True)
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('component_id')
    def _compute_price(self):
        for line in self:
            line.price = line.component_id.standard_price if line.component_id else 0.0

    @api.depends('quantity', 'price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price

    @api.onchange('component_id')
    def _onchange_component_id(self):
        if self.component_id:
            self.price = self.component_id.standard_price