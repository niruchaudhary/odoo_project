import base64
import csv
from io import StringIO
from odoo import models, fields, api, exceptions

class ImportCSVWizard(models.TransientModel):
    _name = 'import.csv.wizard'
    _description = 'Import CSV Wizard'

    file = fields.Binary(string='CSV File', required=True)
    file_name = fields.Char(string='File Name')

    def import_csv(self):
        if not self.file_name.endswith('.csv'):
            raise exceptions.UserError('Please upload a valid CSV file.')

        csv_data = base64.b64decode(self.file).decode('utf-8')
        csv_reader = csv.DictReader(StringIO(csv_data))
        print(csv_reader, "csv_reader\n\n\n\n\n\n\n\n\n\n\n\n")

        for row in csv_reader:
            self.env['e.defter'].create({
                'name': row.get('Description'),
                'date': row.get('Date'),
                'amount': float(row.get('Amount', 0)),
                'account': row.get('Account'),
            })
