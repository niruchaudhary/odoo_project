from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class EDefterWizard(models.TransientModel):
    _name = 'e.defter.wizard'
    _description = 'E-Defter Wizard'

    journal_ids = fields.Many2many(
        'account.move.line',
        string="Journal Items",
        domain="[('date', '>=', date_from), ('date', '<=', date_to)]"
    )
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        """Ensure journal items are filtered based on date range."""
        if self.date_from and self.date_to:
            journal_items = self.env['account.move.line'].search([
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ])
            self.journal_ids = [(6, 0, journal_items.ids)]
        else:
            self.journal_ids = [(5, 0, 0)]

    def action_save_as_draft(self):
        _logger.info(f"Saving E-Defter: Journals {self.journal_ids.ids}, Dates: {self.date_from} to {self.date_to}")
        return {'type': 'ir.actions.act_window_close'}

    def action_download_xml(self):
        _logger.info(f"Downloading XML: Journals {self.journal_ids.ids}, Dates: {self.date_from} to {self.date_to}")
        return {'type': 'ir.actions.act_window_close'}

    def action_send_to_gib(self):
        _logger.info(f"Sending to GIB: Journals {self.journal_ids.ids}, Dates: {self.date_from} to {self.date_to}")
        return {'type': 'ir.actions.act_window_close'}