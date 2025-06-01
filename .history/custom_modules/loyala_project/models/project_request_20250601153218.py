from odoo import api, fields, models

class LoyalaProjectRequest(models.Model):
    _name = 'loyala.project.request'
    _description = 'Loyala Project Request'

    name = fields.Char(string='Request Name', required=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Partner')
    date_deadline = fields.Date(string='Deadline')
    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', required=True)
    product_qty = fields.Float(string='Product Quantity', default=1.0)
    component_line_ids = fields.One2many('loyala.project.request.line', 'request_id', string='Components')
    hpp_unit = fields.Float(string='HPP Produk', compute='_compute_costs', store=True, readonly=True)
    var_cost = fields.Float(string='Variable Cost', compute='_compute_costs', store=True, readonly=True)
    sample_cost = fields.Float(string='Harga Sample', compute='_compute_costs', store=True, readonly=True)
    margin_pct = fields.Float(string='Margin (%)', default=20.0)
    harga_jual = fields.Float(string='Harga Jual', compute='_compute_costs', store=True, readonly=True)

   
    feasibility_ok = fields.Boolean(string='Feasibility Approved', readonly=True)

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if self.bom_id:
            # Populate component lines from BOM
            lines = [(5, 0, 0)]  # Clear existing lines
            for bom_line in self.bom_id.bom_line_ids:
                lines.append((0, 0, {
                    'component_id': bom_line.product_id.id,
                    'quantity': bom_line.product_qty * self.product_qty,
                    'price': bom_line.product_id.standard_price,
                }))
            self.component_line_ids = lines

    @api.depends('component_line_ids.subtotal')
    def _compute_costs(self):
        for request in self:
            if request.component_line_ids:
                total_cost = sum(line.subtotal for line in request.component_line_ids)
                request.hpp_unit = total_cost / request.product_qty if request.product_qty else 0.0
                request.var_cost = request.hpp_unit * request.product_qty * 1.1  # 10% overhead
                request.sample_cost = request.hpp_unit * 2.0  # Double unit cost for sample
            else:
                request.hpp_unit = 0.0
                request.var_cost = 0.0
                request.sample_cost = 0.0

    @api.depends('hpp_unit', 'var_cost', 'margin_pct')
    def _compute_harga_jual(self):
        for request in self:
            request.harga_jual = (request.hpp_unit + request.var_cost) * (1 + request.margin_pct / 100)
        

    def button_run_feasibility(self):
        for request in self:
            request.feasibility_ok = True

class LoyalaProjectRequestLine(models.Model):
    _name = 'loyala.project.request.line'
    _description = 'Loyala Project Request Line'

    request_id = fields.Many2one('loyala.project.request', string='Request', required=True, ondelete='cascade')
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