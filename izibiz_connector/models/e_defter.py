from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class EDefter(models.Model):
    _name = 'e.defter'
    _description = 'E-Defter Report'

    # Basic Fields
    detailref = fields.Many2one('account.move.line', string="Journal Item ID")
    entryref = fields.Many2one('account.move', string="Journal Entry ID")
    linenumber = fields.Integer(string="Line Number")
    linenumbercounter = fields.Integer(string="Line Number Counter")
    accmainid = fields.Integer(string="Account Main ID", store=True)
    accmainiddesc = fields.Char(string="Account Main ID Description", store=True)
    accsubid = fields.Float(string="Account Sub ID", store=True)
    accsubdesc = fields.Char(string="Account Sub Description", store=True)
    amount = fields.Float(string="Amount", compute="_compute_amount", store=True)
    debitcreditcode = fields.Selection([('D', 'Debit'), ('C', 'Credit')], string="Debit/Credit Code",
                                       compute="_compute_debit_credit", store=True)
    postingdate = fields.Date(string="Posting Date", related='entryref.date', store=True)
    documenttype = fields.Selection([
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('check', 'Czech'),
        ('voucher', 'Promissory note'),
        ('shipment', 'Freight'),
        ('order-vendor', 'Vendor Order Form'),
        ('order-customer', 'Customer Order Document'),
        ('other', 'Other')
    ], string='Document Type', required=True)
    doctypedesc = fields.Char(string="Document Type Description", related="entryref.ref", store=True)
    documentnumber = fields.Integer(string="Document Number", store=True)
    documentreference = fields.Integer(string="Document Reference", compute="_compute_document_reference", store=True)
    entrynumbercounter = fields.Integer(string="Entry Number Counter")
    documentdate = fields.Date(string="Document Date", compute="_compute_document_date", store=True)
    paymentmethod = fields.Char(string="Payment Method", compute="_compute_payment_method", store=True)
    detailcomment = fields.Char(string="Detail Comment", compute="_compute_detail_comment", store=True)
    erpno = fields.Many2one('res.company', string="Company", related='entryref.company_id', store=True)
    divisionno = fields.Many2one('account.analytic.account', string="Division")
    enteredby = fields.Many2one('res.users', string="Entered By", related="entryref.create_uid", store=True)
    entereddate = fields.Datetime(string="Entered Date", related="entryref.create_date", store=True)
    entrynumber = fields.Integer(string="Entry Number", store=True)
    entrycomment = fields.Char(string="Entry Comment", store=True)

    def action_open_form(self):
        """Opens a new form view to create or edit an e.defter record."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create New E-Defter',
            'res_model': 'e.defter',
            'view_mode': 'form',
            'view_id': self.env.ref('izibiz_connector.view_edefter_form').id,
            'target': 'new',
        }

    @api.model
    def generate_e_defter_button(self, ids=None):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'e.defter.wizard',
            'view_mode': 'form',
            'views': [(self.env.ref('izibiz_connector.view_e_defter_wizard_form').id, 'form')],
            'target': 'new',
            'context': {'default_journal_ids': [(6, 0, [])], 'default_fiscal_period_id': False},
        }

    def action_save(self):
        """Custom save logic for E-Defter."""
        _logger.info("E-Defter saved successfully.")
        return True

    @api.depends('detailref')
    def _compute_amount(self):
        for rec in self:
            if rec.detailref:
                rec.amount = rec.detailref.debit - rec.detailref.credit

    @api.depends('detailref')
    def _compute_debit_credit(self):
        for rec in self:
            if rec.detailref:
                rec.debitcreditcode = 'D' if rec.detailref.debit > 0 else 'C'

    @api.depends('entryref')
    def _compute_document_reference(self):
        for rec in self:
            rec.documentreference = rec.entryref.ref or rec.entryref.name or ''

    @api.depends('entryref')
    def _compute_document_date(self):
        for rec in self:
            rec.documentdate = rec.entryref.invoice_date or rec.entryref.date

    @api.depends('detailref')
    def _compute_payment_method(self):
        for rec in self:
            payment = rec.detailref.payment_id
            rec.paymentmethod = payment.payment_method_id.name if payment else ''

    @api.depends('detailref')
    def _compute_detail_comment(self):
        for rec in self:
            # Use valid fields from account.move.line or set a default value
            rec.detailcomment = rec.detailref.name or ''
