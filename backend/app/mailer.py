"""Envoi de courriels (facultatif). Sans SMTP_HOST, rien n'est envoyé : l'administration transmet les liens d'invitation
(affichage et export CSV). Ce module n'a pas pu être testé contre un vrai serveur SMTP dans l'environnement de livraison."""
import smtplib
from email.message import EmailMessage
from .config import settings


def smtp_enabled() -> bool:
    return bool(settings.smtp_host)


def send_mail(to: str, subject: str, body: str) -> tuple[bool, str]:
    if not smtp_enabled():
        return False, "SMTP non configuré"
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        return True, "envoyé"
    except Exception as e:  # réseau, authentification, etc.
        return False, f"échec d'envoi : {e.__class__.__name__}"


def invitation_body(name: str, link: str, days: int) -> str:
    return (f"Bonjour {name},\n\nVotre établissement a transmis vos informations à AgriConnect, qui les a vérifiées.\n"
            f"Activez votre compte, choisissez votre mot de passe et acceptez les conditions d'utilisation ici :\n{link}\n\n"
            f"Ce lien est personnel et valable {days} jours.\n\nL'équipe AgriConnect")


def reset_body(name: str, link: str, hours: int) -> str:
    return (f"Bonjour {name},\n\nUne demande de réinitialisation du mot de passe de votre compte AgriConnect a été reçue.\n"
            f"Si vous êtes à l'origine de cette demande, choisissez un nouveau mot de passe ici :\n{link}\n\n"
            f"Ce lien est personnel, à usage unique et valable {hours} heure(s). Si vous n'êtes pas à l'origine de la demande, ignorez ce message.\n\n"
            f"L'équipe AgriConnect")
