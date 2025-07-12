from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, OTP
from .utils import send_otp_email

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'phone_number', 'password', 'confirm_password', 'first_name', 'last_name']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already exists.")
        return value
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        user.is_active = False  # User will be activated after OTP verification
        user.save()
        
    
        # Send OTP using Celery (asynchronous)
        otp = OTP.objects.create(email=user.email, otp_type='registration')
        send_otp_email(user.email, otp.otp_code, 'registration')
        
        return user

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)
    otp_type = serializers.CharField(max_length=20)
    
    def validate(self, attrs):
        try:
            otp = OTP.objects.get(
                email=attrs['email'],
                otp_code=attrs['otp_code'],
                otp_type=attrs['otp_type'],
                is_used=False
            )
            if otp.is_expired():
                raise serializers.ValidationError("OTP has expired.")
            attrs['otp_instance'] = otp
        except OTP.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP.")
        return attrs

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_type = serializers.CharField(max_length=20)

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials.')
            if not user.is_verified:
                raise serializers.ValidationError('Please verify your email first.')
            if user.is_disabled:
                raise serializers.ValidationError('Your account has been disabled.')
            attrs['user'] = user
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    conversation_count = serializers.SerializerMethodField() # AI
    outfit_analysis_count = serializers.SerializerMethodField() # AI
    
    class Meta:
        model = User
        fields = ['id', 'email', 'phone_number', 'first_name', 'last_name', 
                 'full_name', 'profile_image', 'date_created', 'last_active', 
                 'is_anonymous', 'conversation', 'outfits','conversation_count', 
                 'outfit_analysis_count']
    # AI
    def get_conversation_count(self, obj):
        return obj.get_conversation_history().count()
    
    def get_outfit_analysis_count(self, obj):
        return obj.get_outfit_analyses().count()    
    
class UserProfileUpdateSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone_number', 'profile_image']
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exclude(id=self.instance.id).exists():
            raise serializers.ValidationError("Phone number already exists.")
        return value
    
    def update(self, instance, validated_data):
        if 'full_name' in validated_data:
            name_parts = validated_data.pop('full_name').split(' ', 1)
            instance.first_name = name_parts[0]
            instance.last_name = name_parts[1] if len(name_parts) > 1 else ''
        return super().update(instance, validated_data)
    
# Add this new serializer to your serializers.py

class VerifyResetOTPSerializer(serializers.Serializer):
    otp_code = serializers.CharField(max_length=6)
    
    def validate(self, attrs):
        # Get email from request context
        request = self.context.get('request')
        if not request or not hasattr(request, 'session') or 'reset_email' not in request.session:
            raise serializers.ValidationError("Invalid session. Please request OTP again.")
        
        email = request.session['reset_email']
        
        try:
            otp = OTP.objects.get(
                email=email,
                otp_code=attrs['otp_code'],
                otp_type='password_reset',
                is_used=False
            )
            if otp.is_expired():
                raise serializers.ValidationError("OTP has expired.")
            attrs['otp_instance'] = otp
            attrs['email'] = email
        except OTP.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP.")
        return attrs

# Update your existing PasswordResetSerializer
class PasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match.")
        
        # Get email from request context
        request = self.context.get('request')
        if not request or not hasattr(request, 'session') or 'reset_email' not in request.session:
            raise serializers.ValidationError("Invalid session. Please verify OTP first.")
        
        attrs['email'] = request.session['reset_email']
        return attrs

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    retype_new_password = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['retype_new_password']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
# class PasswordResetSerializer(serializers.Serializer):
#     email = serializers.EmailField()
#     otp_code = serializers.CharField(max_length=6)
#     new_password = serializers.CharField(validators=[validate_password])
#     confirm_password = serializers.CharField()
    
#     def validate(self, attrs):
#         if attrs['new_password'] != attrs['confirm_password']:
#             raise serializers.ValidationError("Passwords don't match.")
        
#         try:
#             otp = OTP.objects.get(
#                 email=attrs['email'],
#                 otp_code=attrs['otp_code'],
#                 #otp_type=attrs['otp_type'],
#                 otp_type='password_reset',
#                 is_used=False
#             )
#             if otp.is_expired():
#                 raise serializers.ValidationError("OTP has expired.")
#             attrs['otp_instance'] = otp
#         except OTP.DoesNotExist:
#             raise serializers.ValidationError("Invalid OTP.")
#         return attrs
# Replace your existing DashboardSerializer with this
class DashboardSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    new_users = serializers.IntegerField()
    anonymous_users = serializers.IntegerField()
    new_users_percentage = serializers.CharField()
    anonymous_users_percentage = serializers.CharField()
    admin_profile = serializers.DictField()

# class DashboardSerializer(serializers.Serializer):
#     total_users = serializers.IntegerField()
#     new_users = serializers.IntegerField()
#     anonymous_users = serializers.IntegerField()

class UserManagementSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'phone_number', 'is_anonymous', 
                 'date_created', 'last_active', 'conversation', 'outfits', 'is_disabled']

class AdminSerializer(serializers.ModelSerializer):
    has_access_to = serializers.CharField(source='role')
    contract = serializers.CharField(source='phone_number')
    name = serializers.CharField(source='full_name')
    
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'contract', 'has_access_to']

class AdminCreateUpdateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    phone = serializers.CharField(source='phone_number')
   # password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        #fields = ['email', 'phone_number', 'first_name', 'last_name', 'password'] # update
        fields = ['name', 'email', 'phone', 'role']
    
    def validate_role(self, value):
        if value not in ['Stap_admin', 'superadmin']:
            raise serializers.ValidationError("Role must be Stap_admin or superadmin.")
        return value
    
    def validate_email(self, value):
        if self.instance:
            if User.objects.filter(email=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("Email already exists.")
        else:
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("Email already exists.")
        return value
    
    def validate_phone_number(self, value):
        if self.instance:
            if User.objects.filter(phone_number=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("Phone number already exists.")
        else:
            if User.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError("Phone number already exists.")
        return value
    #Update
    def create(self, validated_data):
        name_parts = validated_data.pop('name').split(' ', 1)
        validated_data['first_name'] = name_parts[0]
        validated_data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
        #password = validated_data.pop('password')
        user = User(**validated_data)
       # user.set_password(password)
        user.role = validated_data.get('role', 'Stap_admin')
        user.is_verified = True
        user.is_active = True
        user.save()
        return user
    # def create(self, validated_data):
    #     name_parts = validated_data.pop('name').split(' ', 1)
    #     validated_data['first_name'] = name_parts[0]
    #     validated_data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
    #     validated_data['is_verified'] = True
    #     validated_data['is_active'] = True
    #     user = User.objects.create_user(**validated_data)
    #     return user
    
    def update(self, instance, validated_data):
        if 'name' in validated_data:
            name_parts = validated_data.pop('name').split(' ', 1)
            instance.first_name = name_parts[0]
            instance.last_name = name_parts[1] if len(name_parts) > 1 else ''
        return super().update(instance, validated_data)