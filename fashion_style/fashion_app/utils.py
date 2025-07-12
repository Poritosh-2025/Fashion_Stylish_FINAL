from django.core.mail import send_mail
from django.conf import settings
from .tasks import send_otp_email_task
import logging

logger = logging.getLogger(__name__)

def send_otp_email(email, otp_code, otp_type='registration'):
    """
    Send OTP email using Celery task (asynchronous)
    """
    try:
        # Send email asynchronously using Celery
        send_otp_email_task.delay(email, otp_code, otp_type)
        logger.info(f"OTP email task queued for {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to queue OTP email task for {email}: {str(e)}")
        # Fallback to synchronous email sending if Celery fails
        return send_otp_email_sync(email, otp_code, otp_type)

def send_otp_email_sync(email, otp_code, otp_type='registration'):
    """
    Send OTP email synchronously (fallback)
    """
    try:
        if otp_type == 'registration':
            subject = 'Welcome! Verify Your Email - OTP Code'
            message = f'''
            Welcome to Fashion Style App!
            
            Your OTP code is: {otp_code}
            
            This code will expire in 10 minutes.
            Please enter this code to verify your email and complete your registration.
            
            If you didn't request this, please ignore this email.
            '''
        elif otp_type == 'password_reset':
            subject = 'Password Reset - OTP Code'
            message = f'''
            Password Reset Request
            
            Your OTP code is: {otp_code}
            
            This code will expire in 10 minutes.
            Please enter this code to reset your password.
            
            If you didn't request this, please ignore this email.
            '''
        else:
            subject = 'Your OTP Code'
            message = f'Your OTP code is: {otp_code}. This code will expire in 10 minutes.'
        
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]
        
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False
        )
        
        logger.info(f"OTP email sent synchronously to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send OTP email synchronously to {email}: {str(e)}")
        return False
# from django.core.mail import send_mail
# from django.conf import settings

# def send_otp_email(email, otp_code):
#     subject = 'Your OTP Code'
#     message = f'Your OTP code is: {otp_code}. This code will expire in 10 minutes.'
#     from_email = settings.DEFAULT_FROM_EMAIL
#     recipient_list = [email]
    
#     send_mail(subject, message, from_email, recipient_list)