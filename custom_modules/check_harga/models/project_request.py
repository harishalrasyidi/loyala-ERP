from odoo import api, fields, models
from datetime import date
from odoo.exceptions import UserError

class LoyalaProjectRequest(models.Model):
    _name = 'loyala.project.request'
    _description = 'Loyala Project Request'

    name = fields.Char(string='Request Name', required=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Partner')
    date_deadline = fields.Date(string='Deadline', required=True, help='Tanggal Deadline Tidak Boleh Sebelum Hari Ini')
    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', required=True)
    product_qty = fields.Float(string='Product Quantity', default=20.0, help='Jumlah Produk yang Diminta Minimal 1 Kodi')
    component_line_ids = fields.One2many('loyala.project.request.line', 'request_id', string='Components')
    component_line_ids_per_product = fields.One2many('loyala.project.request.line.per.product', 'request_id', string='Components per Product')

    #hitung harga pokok produksi (HPP) dan biaya variabel
    hpp_unit = fields.Float(string='HPP Produk', compute='_compute_costs', store=True, readonly=True)
    var_cost = fields.Float(string='Variable Cost', compute='_compute_costs', store=True, readonly=True)
    sample_cost = fields.Float(string='Harga Sample', compute='_compute_costs', store=True, readonly=True)
    margin_pct = fields.Float(string='Margin (%)', default=20.0)
    harga_jual = fields.Float(string='Harga Jual', compute='_compute_harga_jual', store=True, readonly=True)
    profit = fields.Float(string='Profit', compute='_compute_harga_jual', store=True, readonly=True)
    total_cost = fields.Float(string='Total Biaya Keseluruhan', compute='_compute_costs', store=True, readonly=True)
    total_cost_per_product = fields.Float(string='Total Biaya per Product', compute='_compute_costs', store=True, readonly=True)

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

    @api.onchange('product_qty')
    def _onchange_product_qty(self):
        if self.product_qty < 20:
            self.product_qty = 20.0

    @api.onchange('bom_id', 'product_qty')
    def _onchange_bom_id(self):
        if self.bom_id:
            if self.product_qty < 20:
                self.product_qty = 20.0
            lines = [(5, 0, 0)] 
            for bom_line in self.bom_id.bom_line_ids:
                lines.append((0, 0, {
                    'component_id': bom_line.product_id.id,
                    'quantity': bom_line.product_qty * self.product_qty,
                    'price': bom_line.product_id.standard_price,
                }))
            self.component_line_ids = lines
            # per product
            lines_per_product = [(5, 0, 0)] 
            for bom_line in self.bom_id.bom_line_ids:
                lines_per_product.append((0, 0, {
                    'component_id': bom_line.product_id.id,
                    'quantity': bom_line.product_qty,
                    'price': bom_line.product_id.standard_price,
                }))
            self.component_line_ids_per_product = lines_per_product
        else:
            self.component_line_ids = [(5, 0, 0)]
            self.component_line_ids_per_product = [(5, 0, 0)]

    @api.onchange('date_deadline')
    def _onchange_date_deadline(self):
        self.feasibility_ok = False  # Reset feasibility status on date change
        if self.date_deadline and self.date_deadline < date.today():
            raise UserError("Tanggal Deadline Tidak Boleh Sebelum Hari Ini.")

    @api.depends('component_line_ids.subtotal', 'component_line_ids_per_product.subtotal')
    def _compute_costs(self):
        for request in self:
            self._compute_main_costs(request)
            self._compute_per_product_costs(request)

    def _compute_main_costs(self, request):
        if request.component_line_ids:
            total_cost = sum(line.subtotal for line in request.component_line_ids)
            request.hpp_unit = total_cost / request.product_qty if request.product_qty else 0.0
            request.var_cost = request.hpp_unit * 1.1  # 10% overhead
            request.sample_cost = request.hpp_unit * 2.0 if request.hpp_unit > 500000 else 500000
            request.total_cost = total_cost
        else:
            request.hpp_unit = 0.0
            request.var_cost = 0.0
            request.sample_cost = 0.0
            request.total_cost = 0.0

    def _compute_per_product_costs(self, request):
        if request.component_line_ids_per_product:
            total_cost_per_product = sum(line.subtotal for line in request.component_line_ids_per_product)
            request.total_cost_per_product = total_cost_per_product
        else:
            request.total_cost_per_product = 0.0

    @api.constrains('product_qty')
    def _check_product_qty(self):
        for rec in self:
            if rec.product_qty < 20:
                raise UserError("Pemesanan Minimal 1 Kodi atau 20 Produk.")

    @api.constrains('date_deadline')
    def _check_date_deadline(self):
        for rec in self:
            if rec.date_deadline and rec.date_deadline < date.today():
                raise UserError("Deadline cannot be before today.")

    @api.constrains('margin_pct')
    def _check_margin_pct(self):
        for rec in self:
            if rec.margin_pct < 10.0:
                raise UserError("Margin (%) tidak bisa kurang dari 10%.")

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

class LoyalaProjectRequestLinePerProduct(models.Model):
    _name = 'loyala.project.request.line.per.product'
    _description = 'Loyala Project Request Line Per Product'

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

    request_id = fields.Many2one('loyala.project.request', string='Project Request', required=True, 
                default=lambda self: self.env.context.get('active_id'))
    quotasi_id = fields.Many2one('sale.order', string='Quotasi', readonly=True)

    def action_create_quotasi(self):
        for record in self:
            if not record.request_id:
                raise UserError("No project request selected.")
            if not record.request_id.partner_id:
                raise UserError("No partner defined in the project request.")
            if not record.request_id.component_line_ids:
                raise UserError("No components defined in the project request.")
            if not record.request_id.feasibility_ok:
                raise UserError("Quotation cannot be created until the feasibility check is passed.")
            try:
                order_vals = {
                    'partner_id': record.request_id.partner_id.id,
                    'date_order': fields.Date.today(),
                    'order_line': [(0, 0, {
                        'product_id': record.request_id.bom_id.product_tmpl_id.product_variant_id.id,
                        'product_uom_qty': record.request_id.product_qty,
                        'price_unit': record.request_id.harga_jual,
                    })],
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