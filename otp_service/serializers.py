from rest_framework import serializers

class OTPRequestSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    purpose = serializers.ChoiceField(choices=['REGISTER', 'PASSWORD_RESET', 'DELIVERY', 'LOGIN'])

class OTPVerifySerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp_code = serializers.CharField(max_length=6)
    purpose = serializers.ChoiceField(choices=['REGISTER', 'PASSWORD_RESET', 'DELIVERY', 'LOGIN'])
