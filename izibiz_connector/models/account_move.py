# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import base64
import logging
from odoo.modules import get_module_resource
from odoo.exceptions import UserError
import os
import uuid

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # GIB Status Field
    gib_status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent to GIB'),
        ('validated', 'Validated'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string="GIB Status", default='draft')

    # PDF Attachment
    gib_pdf_attachment_id = fields.Many2one('ir.attachment', string="GIB PDF", readonly=True)

    def action_send_to_gib(self):
        service = self.env['izibiz.service']

        # Authenticate and get session ID
        session_id = service.login()

        for record in self:
            if record.move_type != 'out_invoice':
                raise UserError(_("This action is only available for customer invoices."))

            if not record.partner_id.vat:
                raise UserError(_("Customer VAT (Tax ID) is required to send to GIB."))

            # Query Customer VAT Number
            is_efatura = service.check_customer_vat_on_gib(record.partner_id.vat)

            # Set invoice type
            invoice_type = 'e_invoice' if is_efatura else 'e_archive'

            # Generate Base64-encoded XML content
            xml_content = self._generate_invoice_xml(record)

            try:
                uuid = service.send_invoice(record, session_id, xml_content, invoice_type)
                record.gib_status = 'sent'
                record.message_post(body=_("Invoice sent successfully. UUID: %s") % uuid)
            except Exception as e:
                raise UserError(_("Error sending invoice: %s") % e)

    # Method to Download GIB PDF
    def action_download_gib_pdf(self):
        if not self.gib_pdf_attachment_id:
            raise UserError(_("No GIB PDF is available for this invoice."))

        # Return the PDF attachment for download
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.gib_pdf_attachment_id.id}?download=true',
            'target': 'self',
        }

    # Method to Validate Invoice and Fetch PDF
    def _validate_invoice_and_fetch_pdf(self, service, session_id, uuid):
        try:
            pdf_content = service.fetch_invoice_pdf(session_id, uuid)
            if pdf_content:
                attachment = self.env['ir.attachment'].create({
                    'name': f"{self.name}.pdf",
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': 'account.move',
                    'res_id': self.id,
                    'mimetype': 'application/pdf',
                })
                print(attachment, "attachment\n\n\n\n\n")
                self.gib_pdf_attachment_id = attachment.id
                print(self.gib_pdf_attachment_id, "self.gib_pdf_attachment_id\n\n\n\n\n\n\n\n")
                self.gib_status = 'validated'
                self.message_post(body=_("Invoice validated and PDF received from GIB."))
        except Exception as e:
            raise UserError(_("Error fetching PDF from GIB: %s") % e)

    # Button to Cancel GIB Request
    def action_cancel_gib_request(self):
        for record in self:
            if record.gib_status != 'sent':
                raise UserError(_("Only invoices sent to GIB can be cancelled."))
            record.gib_status = 'cancelled'
            record.message_post(body=_("GIB request cancelled."))

    def encode_invoice_to_base64(self, invoice_xml):
        """Encode the generated invoice XML to Base64 format."""
        try:
            invoice_bytes = invoice_xml.encode('utf-8')
            base64_bytes = base64.b64encode(invoice_bytes)
            return base64_bytes.decode('utf-8')
        except Exception as e:
            _logger.error("Error encoding invoice to Base64: %s", e)
            raise UserError(_("Error encoding invoice to Base64."))

    def fetch_xslt(self):
        # Dynamically get the file path
        file_path = get_module_resource('izibiz_connector', 'static', 'INVOICE', 'X012025020928210.txt')

        # Check if the file exists
        if not os.path.isfile(file_path):
            raise UserError(_("The required file is missing: %s") % file_path)

        # Read and return the file content
        with open(file_path, "rb") as pdf_file:
            return pdf_file.read()


    def _generate_invoice_xml(self, record):
        """Generate UBL-TR XML for the invoice."""
        name = record.name
        invoice_name = name.replace("/", "")
        # Generate a UUID based on the invoice name
        unique_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, invoice_name))

        # Print the generated UUID for debugging
        print(invoice_name, unique_uuid, "invoice_name and UUID\n\n\n\n\n")
        invoice_xml = f"""
        <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                 xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                 xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
            <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
            <cbc:CustomizationID>TR1.2</cbc:CustomizationID>
            <cbc:ProfileID>TEMELFATURA</cbc:ProfileID>
            <cbc:ID>{invoice_name}</cbc:ID>
            <cbc:CopyIndicator>false</cbc:CopyIndicator>
            <cbc:UUID>{unique_uuid}</cbc:UUID>
            <cbc:IssueDate>{fields.Date.today()}</cbc:IssueDate>
            <cbc:IssueTime>09:28:04</cbc:IssueTime>
            <cbc:InvoiceTypeCode>SATIS</cbc:InvoiceTypeCode>
            <cbc:Note>BU BİR NOTTUR</cbc:Note>
            <cbc:DocumentCurrencyCode>{record.currency_id.name}</cbc:DocumentCurrencyCode>
            <cbc:LineCountNumeric>1</cbc:LineCountNumeric>
    <cac:AdditionalDocumentReference>
        <cbc:ID>7f0ba363-61a5-4a2c-b071-c5e457451edb</cbc:ID>
        <cbc:IssueDate>2025-01-02</cbc:IssueDate>
        <cbc:DocumentType>XSLT</cbc:DocumentType>
        <cac:Attachment>
            <cbc:EmbeddedDocumentBinaryObject characterSetCode="UTF-8" encodingCode="Base64"
                                              filename="X012025020928210.xslt" mimeCode="application/xml">
                                              {record.fetch_xslt()}
                
            </cbc:EmbeddedDocumentBinaryObject>
        </cac:Attachment>
        </cac:AdditionalDocumentReference>
    <cac:AdditionalDocumentReference>
        <cbc:ID>1</cbc:ID>
        <cbc:IssueDate>2025-01-02</cbc:IssueDate>
        <cbc:DocumentTypeCode>SendingType</cbc:DocumentTypeCode>
        <cbc:DocumentType>KAGIT</cbc:DocumentType>
    </cac:AdditionalDocumentReference>
        <cac:Signature>
        <cbc:ID schemeID="VKN_TCKN">4840847211</cbc:ID>
        <cac:SignatoryParty>
            <cac:PartyIdentification>
                <cbc:ID schemeID="VKN">4840847211</cbc:ID>
            </cac:PartyIdentification>
            <cac:PostalAddress>
                <cbc:StreetName>Altayçeşme Mh. Çamlı Sk. DAP Royal Center</cbc:StreetName>
                <cbc:BuildingName/>
                <cbc:BuildingNumber>A Blok Kat15</cbc:BuildingNumber>
                <cbc:CitySubdivisionName>MALTEPE</cbc:CitySubdivisionName>
                <cbc:CityName>ISTANBUL</cbc:CityName>
                <cbc:PostalZone>34843</cbc:PostalZone>
                <cbc:Region>MALTEPE</cbc:Region>
                <cac:Country>
                    <cbc:Name>TR</cbc:Name>
                </cac:Country>
            </cac:PostalAddress>
        </cac:SignatoryParty>
        <cac:DigitalSignatureAttachment>
            <cac:ExternalReference>
                <cbc:URI>#Signature_BED2025000000001</cbc:URI>
            </cac:ExternalReference>
        </cac:DigitalSignatureAttachment>
    </cac:Signature>
<cac:AccountingSupplierParty>
        <cac:Party>
            <cbc:WebsiteURI>www.izibiz.com.tr</cbc:WebsiteURI>
            <cac:PartyIdentification>
                <cbc:ID schemeID="VKN">{record.partner_id.vat}</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyIdentification>
                <cbc:ID schemeID="MERSISNO">0484084721100010</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyIdentification>
                <cbc:ID schemeID="TICARETSICILNO">873195</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyName>
                <cbc:Name>İZİBİZ BİLİŞİM TEKNOLOJİLERİ ANONİM ŞİRKETİ</cbc:Name>
            </cac:PartyName>
            <cac:PostalAddress>
                <cbc:StreetName>Yıldız Teknik Üniversitesi Teknoloji Geliştirme Bölgesi D2 Blok Z07</cbc:StreetName>
                <cbc:BuildingName/>
                <cbc:BuildingNumber>C-1 Blok</cbc:BuildingNumber>
                <cbc:CitySubdivisionName>MALTEPE</cbc:CitySubdivisionName>
                <cbc:CityName>ISTANBUL</cbc:CityName>
                <cbc:PostalZone>34220</cbc:PostalZone>
                <cbc:Region>MALTEPE</cbc:Region>
                <cac:Country>
                    <cbc:Name>TR</cbc:Name>
                </cac:Country>
            </cac:PostalAddress>
            <cac:PartyTaxScheme>
                <cac:TaxScheme>
                    <cbc:Name>KÜÇÜKYALI655</cbc:Name>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:Contact>
                <cbc:Telephone>(850) 811 11 99</cbc:Telephone>
                <cbc:Telefax/>
                <cbc:ElectronicMail>operasyonekibi@izibiz.com.tr</cbc:ElectronicMail>
            </cac:Contact>
        </cac:Party>
    </cac:AccountingSupplierParty>
    <cac:AccountingCustomerParty>
        <cac:Party>
            <cac:PartyIdentification>
                <cbc:ID schemeID="VKN">1111111157</cbc:ID>
            </cac:PartyIdentification>
            <cac:PartyName>
                <cbc:Name>İZİBİZ BİLİŞİM TEKNOLOJİLERİ ANONİM ŞİRKETİ</cbc:Name>
            </cac:PartyName>
            <cac:PostalAddress>
                <cbc:StreetName>ALTAYÇEŞME MAH. ÇAMLI SK. 16 A/66 MALTEPE İSTANBUL TÜRKİYE</cbc:StreetName>
                <cbc:BuildingName/>
                <cbc:BuildingNumber/>
                <cbc:CitySubdivisionName>MALTEPE</cbc:CitySubdivisionName>
                <cbc:CityName>İSTANBUL</cbc:CityName>
                <cbc:PostalZone/>
                <cbc:Region/>
                <cac:Country>
                    <cbc:Name>TÜRKİYE</cbc:Name>
                </cac:Country>
            </cac:PostalAddress>
            <cac:PartyTaxScheme>
                <cac:TaxScheme>
                    <cbc:Name>KÜÇÜKYALI VERGİ DAİRESİ MÜD.</cbc:Name>
                </cac:TaxScheme>
            </cac:PartyTaxScheme>
            <cac:Contact>
                <cbc:Telephone/>
                <cbc:Telefax/>
                <cbc:ElectronicMail/>
            </cac:Contact>
            <cac:Person>
                <cbc:FirstName>ADI</cbc:FirstName>
                <cbc:FamilyName>SOYADI</cbc:FamilyName>
            </cac:Person>
        </cac:Party>
    </cac:AccountingCustomerParty>
     <cac:PaymentMeans>
        <cbc:PaymentMeansCode>46</cbc:PaymentMeansCode>
        <cac:PayeeFinancialAccount>
            <cbc:ID>TR680006701000000025265337</cbc:ID>
            <cbc:CurrencyCode>TRY</cbc:CurrencyCode>
            <cac:FinancialInstitutionBranch>
                <cbc:Name>İZMİR ŞUBE</cbc:Name>
                <cac:FinancialInstitution>
                    <cbc:Name>ZİRAAT BANKASI</cbc:Name>
                </cac:FinancialInstitution>
            </cac:FinancialInstitutionBranch>
        </cac:PayeeFinancialAccount>
    </cac:PaymentMeans>
    <cac:TaxTotal>
        <cbc:TaxAmount currencyID="TRY">59.40</cbc:TaxAmount>
        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="TRY">110.00</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="TRY">44.00</cbc:TaxAmount>
            <cbc:CalculationSequenceNumeric>1</cbc:CalculationSequenceNumeric>
            <cbc:Percent>40.00</cbc:Percent>
            <cac:TaxCategory>
                <cac:TaxScheme>
                    <cbc:Name>ÖTV 1.LİSTE</cbc:Name>
                    <cbc:TaxTypeCode>0071</cbc:TaxTypeCode>
                </cac:TaxScheme>
            </cac:TaxCategory>
        </cac:TaxSubtotal>
        <cac:TaxSubtotal>
            <cbc:TaxableAmount currencyID="TRY">154.00</cbc:TaxableAmount>
            <cbc:TaxAmount currencyID="TRY">15.40</cbc:TaxAmount>
            <cbc:CalculationSequenceNumeric>1</cbc:CalculationSequenceNumeric>
            <cbc:Percent>10.00</cbc:Percent>
            <cac:TaxCategory>
                <cac:TaxScheme>
                    <cbc:Name>KDV</cbc:Name>
                    <cbc:TaxTypeCode>0015</cbc:TaxTypeCode>
                </cac:TaxScheme>
            </cac:TaxCategory>
        </cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:LegalMonetaryTotal>
        <cbc:LineExtensionAmount currencyID="TRY">110.00</cbc:LineExtensionAmount>
        <cbc:TaxExclusiveAmount currencyID="TRY">110.00</cbc:TaxExclusiveAmount>
        <cbc:TaxInclusiveAmount currencyID="TRY">169.40</cbc:TaxInclusiveAmount>
        <cbc:AllowanceTotalAmount currencyID="TRY">0.00</cbc:AllowanceTotalAmount>
        <cbc:ChargeTotalAmount currencyID="TRY">0.00</cbc:ChargeTotalAmount>
        <cbc:PayableAmount currencyID="TRY">169.40</cbc:PayableAmount>
    </cac:LegalMonetaryTotal>
    <cac:InvoiceLine>
        <cbc:ID>1</cbc:ID>
        <cbc:Note/>
        <cbc:InvoicedQuantity unitCode="C62">1</cbc:InvoicedQuantity>
        <cbc:LineExtensionAmount currencyID="TRY">110.00</cbc:LineExtensionAmount>
        <cac:TaxTotal>
            <cbc:TaxAmount currencyID="TRY">59.40</cbc:TaxAmount>
            <cac:TaxSubtotal>
                <cbc:TaxableAmount currencyID="TRY">110.00</cbc:TaxableAmount>
                <cbc:TaxAmount currencyID="TRY">15.40</cbc:TaxAmount>
                <cbc:CalculationSequenceNumeric>1</cbc:CalculationSequenceNumeric>
                <cbc:Percent>10.00</cbc:Percent>
                <cac:TaxCategory>
                    <cac:TaxScheme>
                        <cbc:Name>KDV</cbc:Name>
                        <cbc:TaxTypeCode>0015</cbc:TaxTypeCode>
                    </cac:TaxScheme>
                </cac:TaxCategory>
            </cac:TaxSubtotal>
            <cac:TaxSubtotal>
                <cbc:TaxableAmount currencyID="TRY">110.00</cbc:TaxableAmount>
                <cbc:TaxAmount currencyID="TRY">44.00</cbc:TaxAmount>
                <cbc:CalculationSequenceNumeric>1</cbc:CalculationSequenceNumeric>
                <cbc:Percent>40.00</cbc:Percent>
                <cac:TaxCategory>
                    <cac:TaxScheme>
                        <cbc:Name>ÖTV 1.LİSTE</cbc:Name>
                        <cbc:TaxTypeCode>0071</cbc:TaxTypeCode>
                    </cac:TaxScheme>
                </cac:TaxCategory>
            </cac:TaxSubtotal>
        </cac:TaxTotal>
        <cac:Item>
            <cbc:Name>kalem</cbc:Name>
        </cac:Item>
        <cac:Price>
            <cbc:PriceAmount currencyID="TRY">110</cbc:PriceAmount>
        </cac:Price>
    </cac:InvoiceLine>
 </Invoice>
        """

        base64_invoice = self.encode_invoice_to_base64(invoice_xml)
        return base64_invoice
