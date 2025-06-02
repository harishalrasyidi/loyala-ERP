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
    harga_jual = fields.Float(string='Harga Jual', compute='_compute_harga_jual', store=True, readonly=True)
    profit = fields.Float(string='Profit', compute='_compute_harga_jual', store=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')

    max_overlap = fields.Integer(
        string='Maksimal Projek Yang Dapat Digunakan Dalam Satu Waktu',
        default=5,
        help='Kapasitas Produksi Maksimal yang Dapat Dijalankan Secara Bersamaan'
    )

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
            request.harga_jual = request.var_cost + (request.var_cost) * (request.margin_pct / 100)
            request.profit = request.harga_jual - (request.var_cost)
        

    def button_run_feasibility(self):
        for request in self:
            overlapping_count = self.search_count([
                ('date_deadline', '=', request.date_deadline),
                ('state', '!=', 'cancelled'),
                ('id', '!=', request.id),
            ])
            
            total_overlap = overlapping_count + 1 
            request.feasibility_ok = total_overlap <= (request.max_overlap or 1)

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

class CreateQuotasi(models.Model):
    _name = 'loyala.create.quotasi'
    _description = 'Create Quotasi from Project Request'

    request_id = fields.Many2one('loyala.project.request', string='Project Request', required=True)
    quotasi_id = fields.Many2one('sale.order', string='Quotasi', readonly=True)

    def action_create_quotasi(self):
        for record in self:
            if not record.request_id:
                raise UserError("No project request selected.")
            if not record.request_id.partner_id:
                raise UserError("No partner defined in the project request.")
            if not record.request_id.component_line_ids:
                raise UserError("No components defined in the project request.")
            try:
                order_vals = {
                    'partner_id': record.request_id.partner_id.id,
                    'date_order': fields.Date.today(),
                    'order_line': [(0, 0, {
                        'product_id': record.request_id.bom_id.product_tmpl_id.product_variant_id.id,
                        'product_uom_qty': record.request_id.product_qty,
                        'price_unit': record.request_id.harga_jual,
                    })],
                    # for line in record.request_id.component_line_ids]
                }
                order = self.env['sale.order'].create(order_vals)
                record.quotasi_id = order.id
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.order',
                    'res_id': order.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            except Exception as e:
                _logger.error("Failed to create quotation: %s", str(e))
                raise UserError(f"Failed to create quotation: {str(e)}")

    # def action_create_quotasi(self):
    #     for record in self:
    #         if not record.request_id:
    #             raise UserError("No project request selected.")
    #         if not record.request_id.partner_id:
    #             raise UserError("No partner defined in the project request.")
    #         # Suppose you have a field: selected_bom_product_ids (Many2many to product.product)
    #         if not record.request_id.request_id.bom_id:
    #             raise UserError("No BOM products selected.")
    #         try:
    #             order_lines = []
    #             for product in record.request_id.bom_id:
    #                 order_lines.append((0, 0, {
    #                     'product_id': product.id,
    #                     'product_uom_qty': record.request_id.product_qty,  # or any qty you want
    #                     'price_unit': record.request_id.harga_jual,          # or any price you want
    #                 }))
    #             order_vals = {
    #                 'partner_id': record.request_id.partner_id.id,
    #                 'date_order': fields.Date.today(),
    #                 'order_line': order_lines,
    #             }
    #             order = self.env['sale.order'].create(order_vals)
    #             record.quotasi_id = order.id
    #             return {
    #                 'type': 'ir.actions.act_window',
    #                 'res_model': 'sale.order',
    #                 'res_id': order.id,
    #                 'view_mode': 'form',
    #                 'target': 'current',
    #             }
    #         except Exception as e:
    #             _logger.error("Failed to create quotation: %s", str(e))
    #             raise UserError(f"Failed to create quotation: {str(e)}")


    

    
