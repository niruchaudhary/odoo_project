from odoo import models, fields
import base64
import csv
import logging
_logger = logging.getLogger(__name__)

import io
import chardet

class CSVImportWizard(models.TransientModel):
    _name = 'csv.import.wizard'
    _description = 'Wizard to Import CSV File'

    file = fields.Binary(string='CSV File', required=True)
    filename = fields.Char(string='File Name')

    def import_csv(self):
        if not self.file:
            return

        raw_data = base64.b64decode(self.file)
        detected_encoding = chardet.detect(raw_data)['encoding']

        decoded_file = raw_data.decode(detected_encoding or 'utf-8')
        file_input = io.StringIO(decoded_file, newline=None)

        reader = csv.DictReader(file_input, delimiter=';', quotechar='"', doublequote=True, skipinitialspace=True)

        model = self.env['e.defter']
        created_records = self.env['e.defter']

        for row in reader:
            try:
                # Resolve Many2one field 'enteredby'
                enteredby_name = row.get('enteredby')
                enteredby_id = None
                if enteredby_name:
                    enteredby = self.env['res.users'].search([('name', '=', enteredby_name)], limit=1)
                    enteredby_id = enteredby.id if enteredby else None

                # Create the record
                record = model.create({
                    'detailref': row.get('detailref'),
                    'entryref': row.get('entryref'),
                    'linenumber': row.get('linenumber'),
                    'linenumbercounter': row.get('linenumbercounter'),
                    'accmainid': row.get('accmainid'),
                    'accmainiddesc': row.get('accmainiddesc'),
                    'accsubid': row.get('accsubid'),
                    'accsubdesc': row.get('accsubdesc'),
                    'amount': row.get('amount'),
                    'debitcreditcode': row.get('debitcreditcode'),
                    'postingdate': row.get('postingdate'),
                    'documenttype': row.get('documenttype'),
                    'doctypedesc': row.get('doctypedesc'),
                    'documentnumber': row.get('documentnumber'),
                    'documentreference': row.get('documentreference'),
                    'entrynumbercounter': row.get('entrynumbercounter'),
                    'documentdate': row.get('documentdate'),
                    'paymentmethod': row.get('paymentmethod'),
                    'detailcomment': row.get('detailcomment'),
                    'erpno': row.get('erpno'),
                    'divisionno': row.get('divisionno'),
                    'enteredby': enteredby_id,
                    'entereddate': row.get('entereddate'),
                    'entrynumber': row.get('entrynumber'),
                    'entrycomment': row.get('entrycomment'),
                })
                created_records |= record
            except Exception as e:
                _logger.error(f"Error processing row: {row}\n{e}")
                self.env.cr.rollback()
                continue

        if created_records:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Imported Records',
                'res_model': 'e.defter',
                'view_mode': 'tree',
                'domain': [('id', 'in', created_records.ids)],
                'target': 'current',
            }

        return {'type': 'ir.actions.act_window_close'}