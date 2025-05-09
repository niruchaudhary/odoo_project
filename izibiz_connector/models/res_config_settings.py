# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    izibiz_username = fields.Char(string="İZİBİZ Username")
    izibiz_password = fields.Char(string="İZİBİZ Password")
    izibiz_application_name = fields.Char(string="Application Name")
    izibiz_base_url = fields.Char(string="İZİBİZ Base URL", default="https://efaturatest.izibiz.com.tr")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    izibiz_username = fields.Char(
        string="İZİBİZ Username",
        related="company_id.izibiz_username",
        readonly=False
    )
    izibiz_password = fields.Char(
        string="İZİBİZ Password",
        related="company_id.izibiz_password",
        readonly=False
    )
    izibiz_application_name = fields.Char(
        string="Application Name",
        related="company_id.izibiz_application_name",
        readonly=False
    )
    izibiz_base_url = fields.Char(
        string="İZİBİZ Base URL",
        related="company_id.izibiz_base_url",
        readonly=False
    )