from odoo import models, fields, api
from odoo.exceptions import UserError

class ProjectRequest(models.Model):
    _name = 'loyala.project.request'
    _description = 'Project Request'

    name = fields.Char(string="Request Reference", default='New')
    partner_id = fields.Many2one('res.partner', string="Customer")
    date_deadline = fields.Date(string="Deadline")
    hpp_unit = fields.Float(string="HPP per Unit", compute="_compute_costs")
    var_cost = fields.Float(string="Variable Cost", compute="_compute_costs")
    sample_cost = fields.Float(string="Sample Cost", compute="_compute_costs")
    margin_pct = fields.Float(string="Margin (%)", default=20.0)
    feasibility_ok = fields.Boolean(string="Feasible?", compute="_compute_feasibility", store=True)

    bom_id = fields.Many2one('mrp.bom', string="Bill of Materials")
    product_qty = fields.Float(string="Qty Requested", default=1.0)

    @api.depends('standard_price', 'margin_pct')
    def _compute_price_reference(self):
        for product in self:
            product.price_reference = product.standard_price

    @api.depends('bom_id', 'product_qty')
    def _compute_costs(self):
        for rec in self:
            if rec.bom_id:
                # Hitung HPP via BOM
                total_bom_cost = sum(line.product_id.standard_price * line.product_qty
                                     for line in rec.bom_id.bom_line_ids)
                rec.hpp_unit = total_bom_cost
                # Contoh variable + sample cost sederhana
                rec.var_cost = total_bom_cost * 0.1
                rec.sample_cost = total_bom_cost * 0.05
            else:
                # Pastikan selalu ada nilai, meski tidak ada BOM
                rec.hpp_unit = 0.0
                rec.var_cost = 0.0
                rec.sample_cost = 0.0

    @api.depends('date_deadline')
    def _compute_feasibility(self):
        for rec in self:
            # Jika deadline belum di-set, anggap belum feasible
            if not rec.date_deadline:
                rec.feasibility_ok = False
                continue

            # Cari work orders yang overlap dengan deadline
            Workorder = self.env['mrp.workorder']
            conflicts = Workorder.search([
                ('date_planned_start', '<=', rec.date_deadline),
                ('expected_date',      '>=', fields.Date.today()),
            ])
            # Kalau ada konflik → tidak feasible
            rec.feasibility_ok = not bool(conflicts)


    def button_run_feasibility(self):
        for rec in self:
            rec._compute_costs()
            rec._compute_feasibility()

    @api.constrains('feasibility_ok')
    def _check_feasibility(self):
        for rec in self:
            if not rec.feasibility_ok:
                raise UserError("Project tidak feasible, silakan ubah deadline atau BOM.")
