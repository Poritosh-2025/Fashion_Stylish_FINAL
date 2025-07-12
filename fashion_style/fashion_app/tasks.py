from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_otp_email_task(email, otp_code, otp_type='registration'):
    """
    Celery task to send OTP email asynchronously
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
        
        logger.info(f"OTP email sent successfully to {email}")
        return f"Email sent successfully to {email}"
        
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        raise e

@shared_task
def send_welcome_email_task(email, full_name):
    """
    Celery task to send welcome email after successful registration
    """
    try:
        subject = 'Welcome to Fashion Style App!'
        message = f'''
        Dear {full_name},
        
        Welcome to Fashion Style App! 
        
        Your account has been successfully created and verified.
        You can now enjoy all our features including:
        - AI-powered style recommendations
        - Outfit analysis
        - Personalized fashion advice
        
        Thank you for joining us!
        
        Best regards,
        Fashion Style Team
        '''
        
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]
        
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False
        )
        
        logger.info(f"Welcome email sent successfully to {email}")
        return f"Welcome email sent successfully to {email}"
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {str(e)}")
        raise e

@shared_task
def send_password_reset_confirmation_task(email, full_name):
    """
    Celery task to send password reset confirmation email
    """
    try:
        subject = 'Password Reset Successful'
        message = f'''
        Dear {full_name},
        
        Your password has been successfully reset.
        
        If you didn't make this change, please contact our support team immediately.
        
        Best regards,
        Fashion Style Team
        '''
        
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [email]
        
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False
        )
        
        logger.info(f"Password reset confirmation email sent successfully to {email}")
        return f"Password reset confirmation email sent successfully to {email}"
        
    except Exception as e:
        logger.error(f"Failed to send password reset confirmation email to {email}: {str(e)}")
        raise e

@shared_task
def example_task():
    """
    Example task for testing Celery functionality
    """
    print("This is an example task running in the background.")
    return "Example task completed successfully"