from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import strip_tags
import smtplib
from email.message import EmailMessage
import os
from pathlib import Path
from datetime import datetime


def send_booking_confirmation_email(*args):
    """Send booking confirmation email.

    Usage:
      send_booking_confirmation_email(user, movie, theater, seats_list)
    or
      send_booking_confirmation_email(booking)

    The function will detect the form based on the first argument.
    """
    # Normalize args
    if len(args) == 1:
        booking = args[0]
        user = getattr(booking, 'user', None)
        movie = getattr(booking, 'movie', None)
        theater = getattr(booking, 'theater', None)
        # booking may contain a single seat (booking.seat) or a selected_seats attribute
        seats_list = []
        if hasattr(booking, 'selected_seats') and booking.selected_seats:
            # assume comma-separated string
            if isinstance(booking.selected_seats, str):
                seats_list = [s.strip() for s in booking.selected_seats.split(',') if s.strip()]
            else:
                seats_list = list(booking.selected_seats)
        elif hasattr(booking, 'seat') and booking.seat:
            seats_list = [getattr(booking.seat, 'seat_number', str(booking.seat))]
    elif len(args) >= 4:
        user, movie, theater, seats_list = args[0], args[1], args[2], args[3]
    else:
        raise ValueError('Invalid arguments to send_booking_confirmation_email')

    if not getattr(user, 'email', None):
        return False

    context = {
        'user': user,
        'movie': movie,
        'theater': theater,
        'seats': seats_list,
    }

    subject = f"Your booking confirmation for {getattr(movie, 'name', '')}"

    # Try rendering simple templates first
    try:
        text_body = render_to_string('emails/booking_confirmation.txt', context)
        html_body = render_to_string('emails/booking_confirmation.html', context)
    except Exception:
        # fallback to older booking-style template
        booking_dict = {
            'user': user,
            'movie': movie,
            'theater': theater,
            'show_date': theater.time.date() if hasattr(theater.time, 'date') else theater.time,
            'show_time': theater.time.time() if hasattr(theater.time, 'time') else theater.time,
            'selected_seats': ', '.join(seats_list),
            'total_price': 0,
        }
        text_body = render_to_string('emails/booking_confirmation.txt', {'booking': booking_dict})
        html_body = render_to_string('emails/booking_confirmation.html', {'booking': booking_dict})

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or settings.EMAIL_HOST_USER
    # If html_body is present but we want plain text too
    plain_body = strip_tags(html_body) if html_body else text_body
    msg = EmailMultiAlternatives(subject, plain_body, from_email, [user.email])
    if html_body:
        msg.attach_alternative(html_body, 'text/html')

    # Attempt to send via Django's configured email backend first
    try:
        msg.send()
        return True
    except Exception as e:
        # Try direct SMTP using settings as a fallback
        try:
            smtp_host = getattr(settings, 'EMAIL_HOST', None)
            smtp_port = getattr(settings, 'EMAIL_PORT', None)
            smtp_user = getattr(settings, 'EMAIL_HOST_USER', None)
            smtp_pass = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            use_tls = getattr(settings, 'EMAIL_USE_TLS', False)
            use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)

            email_msg = EmailMessage()
            email_msg['Subject'] = subject
            email_msg['From'] = from_email
            email_msg['To'] = user.email
            email_msg.set_content(plain_body)
            if html_body:
                email_msg.add_alternative(html_body, subtype='html')

            if smtp_host and smtp_port:
                if use_ssl:
                    smtp = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
                else:
                    smtp = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                try:
                    if use_tls:
                        smtp.ehlo()
                        smtp.starttls()
                        smtp.ehlo()
                    if smtp_user and smtp_pass:
                        smtp.login(smtp_user, smtp_pass)
                    smtp.send_message(email_msg)
                    smtp.quit()
                    return True
                except Exception:
                    try:
                        smtp.quit()
                    except Exception:
                        pass
                    raise
            else:
                raise RuntimeError('SMTP host/port not configured')
        except Exception as send_exc:
            # As a last resort, persist the email to disk and print to console
            try:
                base = getattr(settings, 'BASE_DIR', None) or Path(__file__).resolve().parent.parent
                out_dir = Path(base) / 'sent_emails'
                out_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                safe_to = user.email.replace('@', '_at_')
                txt_path = out_dir / f'booking_{safe_to}_{timestamp}.txt'
                html_path = out_dir / f'booking_{safe_to}_{timestamp}.html'
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(plain_body)
                if html_body:
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(html_body)
                # Print to console so developer sees it immediately
                print('Failed to send email via backend and SMTP. Email saved to:', txt_path)
                if html_path.exists():
                    print('HTML copy saved to:', html_path)
            except Exception as persist_exc:
                print('Failed to persist unsent email:', persist_exc)
            # Still return False to indicate send failed
            return False
