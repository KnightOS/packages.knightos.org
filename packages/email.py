import smtplib
import pystache
import os
import html.parser
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
from flask import url_for

from packages.database import db
from packages.objects import User
from packages.config import _cfg, _cfgi

def send_confirmation(user):
    if _cfg("smtp-host") == "":
        return
    smtp = smtplib.SMTP(_cfg("smtp-host"), _cfgi("smtp-port"))
    smtp.login(_cfg("smtp-user"), _cfg("smtp-password"))
    with open("emails/confirm-account") as f:
        message = MIMEText(html.parser.HTMLParser().unescape(\
            pystache.render(f.read(), { 'user': user, "domain": _cfg("domain"), 'confirmation': user.confirmation })))
    message['X-MC-Important'] = "true"
    message['X-MC-PreserveRecipients'] = "false"
    message['Subject'] = "Confirm your account on the KnightOS Package Index"
    message['From'] = "packages@knightos.org"
    message['To'] = user.email
    smtp.sendmail("packages@knightos.org", [ user.email ], message.as_string())
    smtp.quit()

def send_confirmation(user):
    if _cfg("smtp-host") == "":
        return
    smtp = smtplib.SMTP(_cfg("smtp-host"), _cfgi("smtp-port"))
    smtp.login(_cfg("smtp-user"), _cfg("smtp-password"))
    with open("emails/password-reset") as f:
        message = MIMEText(html.parser.HTMLParser().unescape(\
            pystache.render(f.read(), { 'user': user, "domain": _cfg("domain"), 'confirmation': user.passwordReset })))
    message['X-MC-Important'] = "true"
    message['X-MC-PreserveRecipients'] = "false"
    message['Subject'] = "Reset your password for the KnightOS Package Index"
    message['From'] = "packages@knightos.org"
    message['To'] = user.email
    smtp.sendmail("packages@knightos.org", [ user.email ], message.as_string())
    smtp.quit()

def send_new_pacakge_email(package):
    if _cfg("smtp-host") == "":
        return
    smtp = smtplib.SMTP(_cfg("smtp-host"), _cfgi("smtp-port"))
    smtp.login(_cfg("smtp-user"), _cfg("smtp-password"))
    with open("emails/new-package") as f:
        message = MIMEText(html.parser.HTMLParser().unescape(\
                pystache.render(f.read(), { 'url': _cfg("protocol") + "://" + _cfg("domain") + url_for("html.package", name=package.name, repo=package.repo) })))
    targets = [u.email for u in User.query.filter(User.admin == True)]
    message['X-MC-Important'] = "true"
    message['X-MC-PreserveRecipients'] = "false"
    message['Subject'] = "New package pending approval"
    message['From'] = "packages@knightos.org"
    message['To'] = ';'.join(targets)
    smtp.sendmail("packages@knightos.org", targets, message.as_string())
    smtp.quit()
