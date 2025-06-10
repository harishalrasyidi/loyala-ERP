from odoo import models, fields, api
from odoo.exceptions import UserError

class MonitoringOperasional(models.Model):
    _inherit = 'mrp.production'

    stock_quantity = fields.Float(string='Stok Tersedia', compute='_compute_stock_quantity', store=True)
    project_id = fields.Many2one('project.project', string='Project Terkait', help='Project dari manufaktur yang terjadi')
    custom_state = fields.Selection([
        ('trimming', 'Trimming'),
        ('sewing', 'Sewing'),
        ('bordir_paint', 'Bordir/Paint'),
        ('finishing', 'Finishing'),
    ], string='Manufacturing Stage', default='trimming', tracking=True)

    @api.depends('bom_id')
    def _compute_stock_quantity(self):
        for record in self:
            total_stock = 0.0
            if record.bom_id:
                for line in record.bom_id.bom_line_ids:
                    product = line.product_id
                    stock = product.with_context(warehouse=record.warehouse_id.id).qty_available
                    total_stock += stock
                record.stock_quantity = total_stock
            else:
                record.stock_quantity = 0.0

    def write(self, vals):
        res = super(MonitoringOperasional, self).write(vals)
        # Update or create corresponding mrp.stock.report record
        for record in self:
            if record.state not in ['done', 'cancel']:
                report = self.env['mrp.stock.report'].search([
                    ('production_id', '=', record.id)
                ], limit=1)
                if report:
                    report.write({
                        'custom_state': record.custom_state,
                    })
                else:
                    self.env['mrp.stock.report'].create({
                        'production_id': record.id,
                        'custom_state': record.custom_state,
                    })
            else:
                # Remove report if order is done or cancelled
                self.env['mrp.stock.report'].search([
                    ('production_id', '=', record.id)
                ]).unlink()
        return res

    @api.model
    def create(self, vals):
        record = super(MonitoringOperasional, self).create(vals)
        # Create corresponding mrp.stock.report record
        if record.state not in ['done', 'cancel']:
            self.env['mrp.stock.report'].create({
                'production_id': record.id,
                'custom_state': record.custom_state,
            })
        return record

class StockReport(models.Model):
    _name = 'mrp.stock.report'
    _description = 'Laporan Stok Manufaktur'

    name = fields.Char(string='Referensi', default='New')
    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', domain="[('state', 'not in', ['done', 'cancel'])]")
    product_id = fields.Many2one(related='production_id.product_id', string='Produk', readonly=True)
    project_id = fields.Many2one(related='production_id.project_id', string='Project', readonly=True)
    stock_quantity = fields.Float(related='production_id.stock_quantity', string='Stok Tersedia', readonly=True)
    custom_state = fields.Selection(related='production_id.custom_state', string='Manufacturing Stage', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('mrp.stock.report') or 'New'
        return super(StockReport, self).create(vals)