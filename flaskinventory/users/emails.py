from flask import current_app, url_for, render_template
from flaskinventory import mail
from flask_mail import Message

def send_reset_email(user):
    token = user.get_reset_token()
    subject = 'Password Reset Request'
    msg = Message(subject,
                  sender=current_app.config['MAIL_DEFAULT_SENDER'], recipients=[user.email])

    msg.html = render_template('emails/reset.html', token=token, subject=subject)
    msg.body = f'''To reset your password visit the following link:
        {url_for('users.reset_token', token=token, _external=True)}

        If you did not make this request then simply ignore this email and no changes will be made.
        '''

    mail.send(msg)


def send_verification_email(user):
    token = user.get_invite_token()
    subject = 'OPTED Meteor: Please verify your email address'
    msg = Message(subject,
                sender=current_app.config['MAIL_USERNAME'], recipients=[user.email])

    msg.html = render_template('emails/verify.html', token=token, subject=subject)

    mail.send(msg)

def send_invite_email(user):
    token = user.get_invite_token()
    subject = 'OPTED: Invitation to join Meteor'
    msg = Message(subject=subject,
                  sender=current_app.config['MAIL_USERNAME'], recipients=[user.email])

    msg.html = render_template('emails/invitation.html', subject=subject, token=token)

    mail.send(msg)


def send_accept_email(entry):
    if 'Entry' in entry['dgraph.type']:
        entry['dgraph.type'].remove('Entry')
    
    entry['dgraph.type'] = entry['dgraph.type'][0]

    if 'channel' in entry:
        name_pretty = f'{entry["name"]} ({entry["channel"]["name"]})'
    else:
        name_pretty = f'{entry["name"]} ({entry["dgraph.type"]})'
    
    entry["name"] = name_pretty

    subject = f'Meteor: {name_pretty} now public!'
    msg = Message(subject=subject,
                  sender=current_app.config['MAIL_USERNAME'], recipients=[entry['entry_added']['email']])

    msg.html = render_template('emails/entry_accepted.html', subject=subject, entry=entry)

    mail.send(msg)