from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import OTPRequestSerializer, OTPVerifySerializer
from .utils import OTPManager
from django.contrib.auth import get_user_model

User = get_user_model()

class RequestOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            purpose = serializer.validated_data['purpose']
            
            # Logic restrictions
            if purpose == 'PASSWORD_RESET':
                if not User.objects.filter(phone_number=phone_number).exists():
                    return Response({"error": "No account found with this phone number."}, status=status.HTTP_404_NOT_FOUND)

            record = OTPManager.generate_dummy_otp(phone_number, purpose)
            
            return Response({
                "message": f"OTP sent successfully for {purpose}.",
                "dummy_otp": record.otp_code
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            otp_code = serializer.validated_data['otp_code']
            purpose = serializer.validated_data['purpose']
            
            is_valid, msg = OTPManager.verify_otp(phone_number, otp_code, purpose)
            
            if is_valid:
                return Response({
                    "message": "OTP verified successfully."
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": msg
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
