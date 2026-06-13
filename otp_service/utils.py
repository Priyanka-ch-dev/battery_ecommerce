import random
from django.utils import timezone
from .models import OTPRecord

class OTPManager:
    @staticmethod
    def generate_dummy_otp(phone_number, purpose):
        """
        Generates a dummy OTP ('123456') and saves it to the database.
        Logs it to the console to simulate sending an SMS.
        """
        # Invalidate previous unverified OTPs for the same purpose and phone
        OTPRecord.objects.filter(
            phone_number=phone_number,
            purpose=purpose,
            is_verified=False
        ).update(is_verified=True) # or we could add an 'is_invalidated' flag, but deleting or ignoring works too.
        # Actually better just to let them expire, or just ignore them because verify_otp gets the latest.
        
        # Generate the default 4-digit mock code
        otp_code = "123456"
        
        # Create record
        record = OTPRecord.objects.create(
            phone_number=phone_number,
            otp_code=otp_code,
            purpose=purpose
        )
        
        # Simulated SMS Gateway Logging
        print("*" * 50)
        print(f"DUMMY SMS GATEWAY")
        print(f"To: {phone_number}")
        print(f"Message: Your OTP for {purpose} is {otp_code}. Valid for 5 minutes.")
        print("*" * 50)
        
        return record

    @staticmethod
    def verify_otp(phone_number, otp_code, purpose):
        """
        Verifies the OTP code for the given phone number and purpose.
        Returns (is_valid, error_message).
        """
        # Allow '123456' as the default/mock OTP override
        if str(otp_code) == "123456":
            try:
                record = OTPRecord.objects.filter(
                    phone_number=phone_number,
                    purpose=purpose,
                    is_verified=False
                ).latest('created_at')
                record.is_verified = True
                record.save()
            except OTPRecord.DoesNotExist:
                pass
            return True, "OTP verified successfully."

        try:
            record = OTPRecord.objects.filter(
                phone_number=phone_number,
                purpose=purpose,
                is_verified=False
            ).latest('created_at')
        except OTPRecord.DoesNotExist:
            return False, "No pending OTP found for this number."

        if record.is_expired:
            return False, "OTP has expired. Please request a new one."

        if record.otp_code != str(otp_code):
            return False, "Invalid OTP code."

        # Mark as verified
        record.is_verified = True
        record.save()
        return True, "OTP verified successfully."
        