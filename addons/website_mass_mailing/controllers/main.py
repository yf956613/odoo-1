# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route, request
from odoo.osv import expression
from odoo.addons.mass_mailing.controllers.main import MassMailController


class MassMailController(MassMailController):

    @route('/website_mass_mailing/is_subscriber', type='json', website=True, auth="public")
    def is_subscriber(self, list_id, **post):
        email = None
        if not request.env.user._is_public():
            email = request.env.user.email
        elif request.session.get('mass_mailing_email'):
            email = request.session['mass_mailing_email']

        is_subscriber = False
        if email:
            contacts_count = request.env['mailing.contact.subscription'].sudo().search_count([('list_id', 'in', [int(list_id)]), ('contact_id.email', '=', email), ('opt_out', '=', False)])
            is_subscriber = contacts_count > 0

        return {'is_subscriber': is_subscriber, 'email': email}

    @route('/website_mass_mailing/subscribe', type='json', website=True, auth="public")
    def subscribe(self, list_id, email, **post):
<<<<<<< HEAD
        ContactSubscription = request.env['mailing.contact.subscription'].sudo()
        Contacts = request.env['mailing.contact'].sudo()
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        List_contact_rel = request.env['mail.mass_mailing.list_contact_rel'].sudo()
        Contacts = request.env['mail.mass_mailing.contact'].sudo()
=======
        Contacts = request.env['mail.mass_mailing.contact'].sudo()
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        name, email = Contacts.get_name_email(email)

<<<<<<< HEAD
        subscription = ContactSubscription.search([('list_id', '=', int(list_id)), ('contact_id.email', '=', email)], limit=1)
        if not subscription:
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        list_contact_rel = List_contact_rel.search([('list_id', '=', int(list_id)), ('contact_id.email', '=', email)], limit=1)
        if not list_contact_rel:
=======
        contact_ids = Contacts.search([
            ('list_ids', 'in', [int(list_id)]),
            ('email', '=', email),
        ], limit=1)
        if not contact_ids:
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
            # inline add_to_list as we've already called half of it
<<<<<<< HEAD
            contact_id = Contacts.search([('email', '=', email)], limit=1)
            if not contact_id:
                contact_id = Contacts.create({'name': name, 'email': email})
            ContactSubscription.create({'contact_id': contact_id.id, 'list_id': int(list_id)})
        elif subscription.opt_out:
            subscription.opt_out = False
||||||| f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
            contact_id = Contacts.search([('email', '=', email)], limit=1)
            if not contact_id:
                contact_id = Contacts.create({'name': name, 'email': email})
            List_contact_rel.create({'contact_id': contact_id.id, 'list_id': int(list_id)})
        elif list_contact_rel.opt_out:
            list_contact_rel.opt_out = False
=======
            Contacts.create({'name': name, 'email': email, 'list_ids': [(6,0,[int(list_id)])]})
        elif contact_ids.opt_out:
            contact_ids.opt_out = False
>>>>>>> parent of f296992317e... [IMP] web_editor,*: Refactoring the wysiwyg editor and 'html' field
        # add email to session
        request.session['mass_mailing_email'] = email
        mass_mailing_list = request.env['mailing.list'].sudo().browse(list_id)
        return {'toast_content': mass_mailing_list.toast_content}

    @route(['/website_mass_mailing/get_content'], type='json', website=True, auth="public")
    def get_mass_mailing_content(self, newsletter_id, **post):
        PopupModel = request.env['website.mass_mailing.popup'].sudo()
        data = self.is_subscriber(newsletter_id, **post)
        domain = expression.AND([request.website.website_domain(), [('mailing_list_id', '=', newsletter_id)]])
        mass_mailing_popup = PopupModel.search(domain, limit=1)
        if mass_mailing_popup:
            data['popup_content'] = mass_mailing_popup.popup_content
        else:
            data.update(PopupModel.default_get(['popup_content']))
        return data

    @route(['/website_mass_mailing/set_content'], type='json', website=True, auth="user")
    def set_mass_mailing_content(self, newsletter_id, content, **post):
        PopupModel = request.env['website.mass_mailing.popup']
        domain = expression.AND([request.website.website_domain(), [('mailing_list_id', '=', newsletter_id)]])
        mass_mailing_popup = PopupModel.search(domain, limit=1)
        if mass_mailing_popup:
            mass_mailing_popup.write({'popup_content': content})
        else:
            PopupModel.create({
                'mailing_list_id': newsletter_id,
                'popup_content': content,
                'website_id': request.website.id,
            })
        return True
