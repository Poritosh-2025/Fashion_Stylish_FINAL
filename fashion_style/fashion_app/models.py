# models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
import random
import string

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, phone_number, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'superadmin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, phone_number, password, **extra_fields)
class User(AbstractUser):
    username = None 
    USER_ROLES = [
        ('user', 'User'),
        ('Stap_admin', 'Stap_admin'),
        ('superadmin', 'Super Admin'),
    ]
    
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_verified = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    role = models.CharField(max_length=20, choices=USER_ROLES, default='user')
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    conversation = models.TextField(blank=True)
    outfits = models.TextField(blank=True)
    is_disabled = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number']
    
    
    objects = UserManager()  # Use the custom manager

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or "Anonymous" 
    
    def __str__(self):
        return self.email
    
    # AI
    def get_conversation_history(self):
        """Get user's conversation history from AI stylist"""
        from ai_stylist_app.models import SessionHistory
        return SessionHistory.objects.filter(user_id=str(self.id)).order_by('timestamp')

    def get_outfit_analyses(self):
            """Get user's outfit analysis history"""
            from ai_stylist_app.models import SessionHistory
            return SessionHistory.objects.filter(
                user_id=str(self.id), 
                image__isnull=False
            ).order_by('timestamp')

class OTP(models.Model):
    OTP_TYPES = [
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
    ]
    
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    otp_type = models.CharField(max_length=20, choices=OTP_TYPES)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = ''.join(random.choices(string.digits, k=6))
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"{self.email} - {self.otp_code}"
    

# def get_conversation_history(self):
#     """Get user's conversation history from AI stylist"""
#     from ai_stylist_app.models import SessionHistory
#     return SessionHistory.objects.filter(user_id=str(self.id)).order_by('timestamp')

# def get_outfit_analyses(self):
#     """Get user's outfit analysis history"""
#     from ai_stylist_app.models import SessionHistory
#     return SessionHistory.objects.filter(
#         user_id=str(self.id), 
#         image__isnull=False
#     ).order_by('timestamp')