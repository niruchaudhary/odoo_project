# -*- coding: utf-8 -*-

import requests
from odoo import api, models
import base64


class IzibizService(models.AbstractModel):
    _name = 'izibiz.service'
    _description = 'Service for İZİBİZ Integration'

    def _get_config(self):
        """Retrieve configuration values from ir.config_parameter"""
        # breakpoint()
        config = self.env['ir.config_parameter'].sudo()
        name =  {
            'username': self.env.company.izibiz_username,
            'password': self.env.company.izibiz_password,
            'application_name': self.env.company.izibiz_application_name,
            'base_url': self.env.company.izibiz_base_url,
        }
        print(name, "name")
        return name

    def login(self):
        """Authenticate with İZİBİZ and retrieve a session ID"""
        config = self._get_config()
        url = f"{config['base_url']}/AuthenticationWS"
        headers = {
            'Content-Type': 'text/xml;charset=UTF-8',
            'SOAPAction': '""'
        }
        payload = f"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://schemas.i2i.com/ei/wsdl">
               <soapenv:Header/>
               <soapenv:Body>
                  <tns:LoginRequest>
                     <REQUEST_HEADER>
                        <SESSION_ID>-1</SESSION_ID>
                        <APPLICATION_NAME>{config['application_name']}</APPLICATION_NAME>
                     </REQUEST_HEADER>
                     <USER_NAME>{config['username']}</USER_NAME>
                     <PASSWORD>{config['password']}</PASSWORD>
                  </tns:LoginRequest>
               </soapenv:Body>
            </soapenv:Envelope>
        """

        response = requests.post(url, headers=headers, data=payload)

        if response.status_code == 200:
            session_id = self._parse_response(response.text, 'SESSION_ID')
            return session_id
        else:
            raise Exception(f"Login failed: {response.text}")

    def check_customer_vat_on_gib(self, vat):
        """Check if the customer is registered on the e-Fatura system."""
        config = self._get_config()
        url = f"{config['base_url']}/AuthenticationWS"
        headers = {
            'Content-Type': 'text/xml;charset=UTF-8',
            'SOAPAction': 'GetGibUserList'
        }

        # XML Payload without the XML declaration
        payload = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://schemas.i2i.com/ei/wsdl">
           <soapenv:Header/>
           <soapenv:Body>
              <tns:CheckUserRequest>
                 <REQUEST_HEADER>
                    <SESSION_ID>{self.login()}</SESSION_ID>
                    <APPLICATION_NAME>{config['application_name']}</APPLICATION_NAME>
                 </REQUEST_HEADER>
                 <USER>
                    <IDENTIFIER>4840847211</IDENTIFIER>
                 </USER>
                 <DOCUMENT_TYPE>INVOICE</DOCUMENT_TYPE>
              </tns:CheckUserRequest>
           </soapenv:Body>
        </soapenv:Envelope>
        """

        response = requests.post(url, headers=headers, data=payload)

        if response.status_code == 200:
            if '<STATUS>true</STATUS>' in response.text:
                return True
            return False
        else:
            raise Exception(f"Error querying VAT number: {response.text}")

    def fetch_invoice_pdf(self, session_id, uuid):
        """Fetch the invoice PDF from GIB using the UUID."""
        config = self._get_config()
        url = f"{config['base_url']}/EIArchiveWS"
        headers = {
            'Content-Type': 'text/xml;charset=UTF-8',
            'SOAPAction': 'GetDocument'
        }

        # XML Payload to fetch the PDF
        payload = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:arc="http://schemas.i2i.com/ei/wsdl">
           <soapenv:Header/>
           <soapenv:Body>
              <arc:GetDocumentRequest>
                 <REQUEST_HEADER>
                    <SESSION_ID>{session_id}</SESSION_ID>
                    <APPLICATION_NAME>{config['application_name']}</APPLICATION_NAME>
                 </REQUEST_HEADER>
                 <UUID>{uuid}</UUID>
              </arc:GetDocumentRequest>
           </soapenv:Body>
        </soapenv:Envelope>
        """

        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            # Extract the PDF content from the response
            start = response.text.find("<CONTENT>") + len("<CONTENT>")
            end = response.text.find("</CONTENT>")
            pdf_base64 = response.text[start:end]

            # Decode the Base64-encoded PDF
            return base64.b64decode(pdf_base64)
        else:
            raise Exception(f"Error fetching PDF from GIB: {response.text}")


    @staticmethod
    def _parse_response(response_text, tag):
        """Parse a specific tag from the SOAP response."""
        start = response_text.find(f"<{tag}>") + len(tag) + 2
        end = response_text.find(f"</{tag}>")
        return response_text[start:end]

    def send_invoice(self, move_id, session_id, invoice_xml, invoice_type='e_archive'):
        """Send an invoice to İZİBİZ"""
        config = self._get_config()

        # Determine endpoint and headers based on invoice type
        if invoice_type == 'e_invoice':
            endpoint = "/EInvoiceWS?wsdl=null"
            headers = {
                'Content-Type': 'text/xml;charset=UTF-8',
                'SOAPAction': '/EInvoiceWS/EInvoice/SendInvoice'
            }
            payload = f"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ei="http://schemas.i2i.com/ei/wsdl">
               <soapenv:Header/>
               <soapenv:Body>
                  <ei:SendInvoiceRequest>
                     <REQUEST_HEADER>
                        <SESSION_ID>{session_id}</SESSION_ID>
                        <APPLICATION_NAME>{config['application_name']}</APPLICATION_NAME>
                        <COMPRESSED>N</COMPRESSED>
                     </REQUEST_HEADER>
                     <INVOICE>
                        <CONTENT>{invoice_xml}</CONTENT>
                     </INVOICE>
                  </ei:SendInvoiceRequest>
               </soapenv:Body>
            </soapenv:Envelope>
            """
        else:
            endpoint = "/EIArchiveWS/EFaturaArchive?wsdl=null"
            headers = {
                'Content-Type': 'text/xml;charset=UTF-8',
                'SOAPAction': 'WriteToArchive'
            }
            payload = f"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:arc="http://schemas.i2i.com/ei/wsdl/archive">
               <soapenv:Header/>
               <soapenv:Body>
                  <arc:ArchiveInvoiceWriteRequest>
                     <arc:REQUEST_HEADER>
                        <arc:SESSION_ID>{session_id}</arc:SESSION_ID>
                        <arc:APPLICATION_NAME>{config['application_name']}</arc:APPLICATION_NAME>
                        <arc:COMPRESSED>N</arc:COMPRESSED>
                     </arc:REQUEST_HEADER>
                     <arc:INVOICE_PROPERTIES>
                        <arc:EARSIV_FLAG>Y</arc:EARSIV_FLAG>
                        <arc:EARSIV_PROPERTIES>
                           <arc:EARSIV_TYPE>NORMAL</arc:EARSIV_TYPE>
                           <arc:SUB_STATUS>NEW</arc:SUB_STATUS>
                           <arc:SERI>ABC</arc:SERI>
                           <arc:EARSIV_EMAIL_FLAG>Y</arc:EARSIV_EMAIL_FLAG>
                           <arc:EARSIV_EMAIL>{move_id.partner_id.email or 'customer@example.com'}</arc:EARSIV_EMAIL>
                           <arc:EARSIV_SMS_FLAG>N</arc:EARSIV_SMS_FLAG>
                        </arc:EARSIV_PROPERTIES>
                        <arc:INVOICE_CONTENT>{invoice_xml}</arc:INVOICE_CONTENT>
                        <arc:ARCHIVE_NOTE>This is a sample e-archive note.</arc:ARCHIVE_NOTE>
                     </arc:INVOICE_PROPERTIES>
                  </arc:ArchiveInvoiceWriteRequest>
               </soapenv:Body>
            </soapenv:Envelope>
            """

        # Send the request
        url = f"{config['base_url']}{endpoint}"
        response = requests.post(url, headers=headers, data=payload)

        # Handle the response
        if response.status_code == 200:
            return self._parse_response(response.text, 'UUID')
        else:
            raise Exception(f"Invoice submission failed: {response.text}")

    def fetch_e_delivery_pdf(self, session_id, uuid):
        """Fetch the e-Delivery (e-İrsaliye) PDF from GIB using the UUID."""
        config = self._get_config()
        url = f"{config['base_url']}/EIrsaliyeWS"
        headers = {
            'Content-Type': 'text/xml;charset=UTF-8',
            'SOAPAction': 'GetDespatchAdvice'
        }

        # XML Payload to fetch the e-Delivery document
        payload = f"""
        <?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsdl="http://schemas.i2i.com/ei/wsdl">
           <soapenv:Header/>
           <soapenv:Body>
              <wsdl:LoadDespatchAdviceRequest>
                 <REQUEST_HEADER>
                    <SESSION_ID>{session_id}</SESSION_ID>
                    <COMPRESSED>N</COMPRESSED>
                    <APPLICATION_NAME>{config['application_name']}</APPLICATION_NAME>
                 </REQUEST_HEADER>
                 <DESPATCHADVICE>
                    <ID></ID>
                    <UUID></UUID>
                    <CONTENT>
                    
                    </CONTENT>
                 </DESPATCHADVICE>
              </wsdl:LoadDespatchAdviceRequest>
           </soapenv:Body>
        </soapenv:Envelope>
        """

        response = requests.post(url, headers=headers, data=payload)

        if response.status_code == 200:
            # Extract the Base64-encoded PDF content from the response
            start = response.text.find("<CONTENT>") + len("<CONTENT>")
            end = response.text.find("</CONTENT>")
            pdf_base64 = response.text[start:end]

            # Decode the Base64-encoded PDF
            return base64.b64decode(pdf_base64)
        else:
            raise Exception(f"Error fetching e-Delivery PDF: {response.text}")
