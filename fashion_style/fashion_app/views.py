from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .models import User, OTP
from .serializers import *
from .utils import send_otp_email
from rest_framework.permissions import AllowAny  # Change this based on your security needs
from django.contrib.auth import get_user_model
from .tasks import (
    example_task,
    send_otp_email_task,
    send_welcome_email_task,
    send_password_reset_confirmation_task
    ) # Import your Celery task
User = get_user_model()

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
       #send_otp_email_task.delay()
        otp = OTP.objects.create(email=user.email, otp_type='registration')
        send_otp_email(user.email, otp.otp_code, 'registration')
        return Response({
            'message': 'Registration successful. Please check your email for OTP verification.',
            'email': user.email
        }, status=status.HTTP_201_CREATED)

class OTPVerificationView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        otp_instance = serializer.validated_data['otp_instance']
        email = serializer.validated_data['email']
        otp_type = serializer.validated_data['otp_type']
        
        # Mark OTP as used
        otp_instance.is_used = True
        otp_instance.save()
        
        if otp_type == 'registration':
            # Activate user
            user = User.objects.get(email=email)
            user.is_active = True
            user.is_verified = True
            user.save()
            
            # Send welcome email asynchronously
            send_welcome_email_task.delay(user.email, user.full_name)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'message': 'Email verified successfully. Registration completed.',
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': UserProfileSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'message': 'OTP verified successfully.'
        }, status=status.HTTP_200_OK)

class ResendOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp_type = serializer.validated_data['otp_type']
        
        # Invalidate old OTPs
        OTP.objects.filter(email=email, otp_type=otp_type, is_used=False).update(is_used=True)
        
        # Create new OTP
        otp = OTP.objects.create(email=email, otp_type=otp_type)
        send_otp_email(email, otp.otp_code, otp_type)
        
        return Response({
            'message': 'New OTP sent to your email.'
        }, status=status.HTTP_200_OK)

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        user.last_active = timezone.now()
        user.save()
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Login successful.',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
        except KeyError:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        except TokenError:
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class UserProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({
            'message': 'Profile updated successfully.',
            'user': UserProfileSerializer(self.get_object()).data
        }, status=status.HTTP_200_OK)
    
# Update your existing PasswordResetRequestView
class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        # Store email in session for later steps
        request.session['reset_email'] = email
        
        # Invalidate old password reset OTPs
        OTP.objects.filter(email=email, otp_type='password_reset', is_used=False).update(is_used=True)
        
        # Create new OTP
        otp = OTP.objects.create(email=email, otp_type='password_reset')
        send_otp_email(email, otp.otp_code, 'password_reset')
        
        return Response({
            'message': 'Password reset OTP sent to your email.'
        }, status=status.HTTP_200_OK)

# Add this new view
class VerifyResetOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = VerifyResetOTPSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        otp_instance = serializer.validated_data['otp_instance']
        
        # Mark OTP as used
        otp_instance.is_used = True
        otp_instance.save()
        
        # Store verification status in session
        request.session['otp_verified'] = True
        
        return Response({
            'message': 'OTP verified successfully. You can now set new password.'
        }, status=status.HTTP_200_OK)

# Update your existing PasswordResetView
class PasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Check if OTP was verified
        if not request.session.get('otp_verified'):
            return Response({
                'error': 'Please verify OTP first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = PasswordResetSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        new_password = serializer.validated_data['new_password']
        
        # Update user password
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()
        # Send password reset confirmation email asynchronously
        send_password_reset_confirmation_task.delay(user.email, user.full_name)
        
        # Clear session data
        request.session.pop('reset_email', None)
        request.session.pop('otp_verified', None)
        
        return Response({
            'message': 'Password reset successful. You can now login with your new password.'
        }, status=status.HTTP_200_OK)
        

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        # Set new password
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully.'
        }, status=status.HTTP_200_OK)

# class PasswordResetRequestView(APIView):
#     permission_classes = [permissions.AllowAny]
    
#     def post(self, request):
#         serializer = PasswordResetRequestSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
        
#         email = serializer.validated_data['email']
        
#         # Invalidate old password reset OTPs
#         OTP.objects.filter(email=email, otp_type='password_reset', is_used=False).update(is_used=True)
        
#         # Create new OTP
#         otp = OTP.objects.create(email=email, otp_type='password_reset')
#         send_otp_email(email, otp.otp_code)
        
#         return Response({
#             'message': 'Password reset OTP sent to your email.'
#         }, status=status.HTTP_200_OK)

# class PasswordResetView(APIView):
#     permission_classes = [permissions.AllowAny]
    
#     def post(self, request):
#         serializer = PasswordResetSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
        
#         email = serializer.validated_data['email']
#         new_password = serializer.validated_data['new_password']
#         otp_instance = serializer.validated_data['otp_instance']
        
#         # Mark OTP as used
#         otp_instance.is_used = True
#         otp_instance.save()
        
#         # Update user password
#         user = User.objects.get(email=email)
#         user.set_password(new_password)
#         user.save()
        
#         return Response({
#             'message': 'Password reset successful. You can now login with your new password.'
#         }, status=status.HTTP_200_OK)

# Admin Views
# Replace your existing DashboardView with this
class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if request.user.role not in ['Stap_admin', 'superadmin']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # Today's data
        total_users = User.objects.filter(role='user').count()
        new_users_today = User.objects.filter(role='user', date_created__date=today).count()
        anonymous_users_today = User.objects.filter(is_anonymous=True, date_created__date=today).count()
        
        # Yesterday's data
        new_users_yesterday = User.objects.filter(role='user', date_created__date=yesterday).count()
        anonymous_users_yesterday = User.objects.filter(is_anonymous=True, date_created__date=yesterday).count()
        
        # Calculate percentages
        def calculate_percentage(today_count, yesterday_count):
            if yesterday_count == 0:
                return "+100%" if today_count > 0 else "0%"
            percentage = ((today_count - yesterday_count) / yesterday_count) * 100
            if percentage > 0:
                return f"+{percentage:.0f}%"
            elif percentage < 0:
                return f"{percentage:.0f}%"
            else:
                return "0%"
        
        new_users_percentage = calculate_percentage(new_users_today, new_users_yesterday)
        anonymous_users_percentage = calculate_percentage(anonymous_users_today, anonymous_users_yesterday)
        
        # Admin profile data
        admin_profile = {
            'id': request.user.id,
            'name': request.user.full_name,
            'email': request.user.email,
            'phone_number': request.user.phone_number,
            'role': request.user.role,
            'date_created': request.user.date_created,
            'last_active': request.user.last_active
        }
        
        data = {
            'total_users': total_users,
            'new_users': new_users_today,
            'anonymous_users': anonymous_users_today,
            'new_users_percentage': new_users_percentage,
            'anonymous_users_percentage': anonymous_users_percentage,
            'admin_profile': admin_profile
        }
        
        serializer = DashboardSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)

# class DashboardView(APIView):
#     permission_classes = [permissions.IsAuthenticated]
    
#     def get(self, request):
#         if request.user.role not in ['Stap_admin', 'superadmin']:
#             return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
#         today = timezone.now().date()
#         total_users = User.objects.filter(role='user').count()
#         new_users = User.objects.filter(role='user', date_created__date=today).count()
#         anonymous_users = User.objects.filter(is_anonymous=True).count()
        
#         data = {
#             'total_users': total_users,
#             'new_users': new_users,
#             'anonymous_users': anonymous_users
#         }
        
#         serializer = DashboardSerializer(data)
#         return Response(serializer.data, status=status.HTTP_200_OK)

class UserManagementView(generics.ListAPIView):
    serializer_class = UserManagementSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role not in ['Stap_admin', 'superadmin']:
            return User.objects.none()
        return User.objects.filter(role='user')

    from rest_framework.pagination import PageNumberPagination
    class UserPagination(PageNumberPagination):
        page_size = 10
        page_size_query_param = 'page_size'
        max_page_size = 100

    pagination_class = UserPagination
    

class UserActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        if request.user.role not in ['Stap_admin', 'superadmin']:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(id=user_id, role='user')
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        action = request.data.get('action')
        
        if action == 'disable':
            user.is_disabled = True
            user.save()
            return Response({'message': 'User access disabled.'}, status=status.HTTP_200_OK)
        elif action == 'enable':
            user.is_disabled = False
            user.save()
            return Response({'message': 'User access enabled.'}, status=status.HTTP_200_OK)
        elif action == 'delete':
            user.delete()
            return Response({'message': 'User account deleted.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid action. Use: disable, enable, or delete.'}, status=status.HTTP_400_BAD_REQUEST)

# class UserActionView(APIView):
#     permission_classes = [permissions.IsAuthenticated]
    
#     def post(self, request, user_id):
#         if request.user.role not in ['Stap_admin', 'superadmin']:
#             return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
#         try:
#             user = User.objects.get(id=user_id, role='user')
#         except User.DoesNotExist:
#             return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        
#         action = request.data.get('action')
        
#         if action == 'disable':
#             user.is_disabled = True
#             user.save()
#             return Response({'message': 'User access disabled.'}, status=status.HTTP_200_OK)
#         elif action == 'delete':
#             user.delete()
#             return Response({'message': 'User account deleted.'}, status=status.HTTP_200_OK)
#         else:
#             return Response({'error': 'Invalid action.'}, status=status.HTTP_400_BAD_REQUEST)

class AdministratorsView(generics.ListAPIView):
    serializer_class = AdminSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role not in ['Stap_admin', 'superadmin']:
            return User.objects.none()
        return User.objects.filter(role__in=['Stap_admin', 'superadmin'])

class AdminCreateView(generics.CreateAPIView):
    serializer_class = AdminCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        if request.user.role != 'superadmin':
            return Response({'error': 'Only Super Admin can create administrators.'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        response = super().create(request, *args, **kwargs)
        return Response({
            'message': 'Administrator created successfully.',
            'admin': response.data
        }, status=status.HTTP_201_CREATED)

class AdminUpdateView(generics.UpdateAPIView):
    serializer_class = AdminCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role not in ['Stap_admin', 'superadmin']:
            return User.objects.none()
        return User.objects.filter(role__in=['Stap_admin', 'superadmin'])
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({
            'message': 'Administrator updated successfully.',
            'admin': response.data
        }, status=status.HTTP_200_OK)

# Add this new view to your views.py
class AdminActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, admin_id):
        if request.user.role != 'superadmin':
            return Response({'error': 'Only Super Admin can perform this action.'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            admin = User.objects.get(id=admin_id, role='Stap_admin')
        except User.DoesNotExist:
            return Response({'error': 'Admin not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        action = request.data.get('action')
        
        if action == 'disable':
            admin.is_disabled = True
            admin.save()
            return Response({'message': 'Admin access disabled.'}, status=status.HTTP_200_OK)
        elif action == 'enable':
            admin.is_disabled = False
            admin.save()
            return Response({'message': 'Admin access enabled.'}, status=status.HTTP_200_OK)
        elif action == 'delete':
            admin.delete()
            return Response({'message': 'Admin account deleted.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid action. Use: disable, enable, or delete.'}, status=status.HTTP_400_BAD_REQUEST)

# class AdminDeleteView(generics.DestroyAPIView):
#     permission_classes = [permissions.IsAuthenticated]
    
#     def get_queryset(self):
#         if self.request.user.role not in ['Stap_admin', 'superadmin']:
#             return User.objects.none()
#         return User.objects.filter(role__in=['Stap_admin', 'superadmin'])
    
#     def destroy(self, request, *args, **kwargs):
#         instance = self.get_object()
#         self.perform_destroy(instance)
#         return Response({
#             'message': 'Administrator account deleted successfully.'
#         }, status=status.HTTP_200_OK)
    
class CreateSuperuserView(APIView):
    permission_classes = [AllowAny]  # Be careful with this in production
    
    def post(self, request):
        # Extract data from request
        email = request.data.get('email')
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        # Validation
        if not email or not phone_number or not password:
            return Response({
                'error': 'Email, phone_number, and password are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'User with this email already exists.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if User.objects.filter(phone_number=phone_number).exists():
            return Response({
                'error': 'User with this phone number already exists.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create superuser
            user = User.objects.create_user(
                email=email,
                phone_number=phone_number,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='superadmin',
                is_verified=True,
                is_active=True,
                is_staff=True,
                is_superuser=True
            )
            
            return Response({
                'message': 'Superuser created successfully!',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'phone_number': user.phone_number,
                    'full_name': user.full_name,
                    'role': user.role,
                    'is_verified': user.is_verified,
                    'is_active': user.is_active
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Error creating superuser: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)