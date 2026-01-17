from django.shortcuts import render,redirect
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import transaction
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from ..forms import SignupForm
from ..utils import generate_otp
from ..models import EmailVerificationRequest, User

def send_verification_email(email, otp):
    send_mail(
        subject="Verify your email",
        message=f"Your verification OTP is: {otp}\n\nThis OTP is valid for 5 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            try:
                verification = EmailVerificationRequest.objects.get(email=email)

                # If OTP expired → delete and create new
                if verification.is_expired():
                    verification.delete()
                else:
                    # Resend existing OTP
                    send_verification_email(email, verification.otp)
                    return render(request, "accounts/otp-verification.html", {
                        "message": "Verification email already sent. Please check your inbox."
                    })

            except EmailVerificationRequest.DoesNotExist:
                otp = generate_otp()

                EmailVerificationRequest.objects.create(
                    email=email,
                    password=make_password(password),
                    otp=otp,
                    expires_at=timezone.now() + timedelta(minutes=5)
                )

                send_verification_email(email, otp)

                request.session["otp_purpose"] = "signup"
                request.session["otp_email"] = email

                return render(request, "accounts/otp-verification.html", {
                    "purpose": "signup",
                    "message": "Verification email sent. Please verify to continue."
                })


        return render(request, "accounts/create_account.html", {
            "form": form
        })

    return render(request, "accounts/create_account.html", {
        "form": SignupForm()
    })

def verify_email_view(request):
    if request.method != "POST":
        return render(request, "accounts/otp-verification.html")

    otp = "".join([
        request.POST.get("otp1", ""),
        request.POST.get("otp2", ""),
        request.POST.get("otp3", ""),
        request.POST.get("otp4", ""),
        request.POST.get("otp5", ""),
        request.POST.get("otp6", ""),
    ])

    purpose = request.session.get("otp_purpose")
    email = request.session.get("otp_email")

    if not purpose or not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect("accounts:forgot_password")

    try:
        verification = EmailVerificationRequest.objects.get(
            email=email,
            otp=otp
        )
    except EmailVerificationRequest.DoesNotExist:
        messages.error(request, "Invalid OTP")
        return render(request, "accounts/otp-verification.html", {
            "purpose": purpose
        })

    if verification.is_expired():
        verification.delete()
        messages.error(request, "OTP expired")
        return redirect("accounts:forgot_password")

    # ✅ SIGNUP FLOW
    if purpose == "signup":
        with transaction.atomic():
            User.objects.create(
                email=verification.email,
                username=verification.email,
                password=verification.password
            )
            verification.delete()
            request.session.flush()

        return render(request, "accounts/verfy_successful.html")

    # ✅ FORGOT PASSWORD FLOW
    if purpose == "reset":
        verification.delete()

        request.session["otp_verified"] = True
        request.session["reset_email"] = email   

        return redirect("accounts:reset_password")


        # ---------------login--------------
def userlogin(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Authenticate user
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return render(request,"accounts/profile.html")  
        else:
            messages.error(request, "Invalid email or password")
            return render(request, "accounts/user_login.html")

    return render(request, "accounts/user_login.html")

@login_required(login_url='accounts:userlogin')  
def profile(request):
    return render(request, 'accounts/profile.html', {
        'user': request.user
    })

def user_logout(request):
    logout(request)
    return redirect("accounts:userlogin")  

# -----forget password-------
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if not User.objects.filter(email=email).exists():
            messages.error(request, "Email not registered")
            return redirect("accounts:forgot_password")

        # Remove old OTPs
        EmailVerificationRequest.objects.filter(email=email).delete()

        otp = generate_otp()

        EmailVerificationRequest.objects.create(
            email=email,
            otp=otp,
            expires_at=timezone.now() + timedelta(minutes=5)
        )

        send_verification_email(email, otp)

        request.session["otp_purpose"] = "reset"
        request.session["otp_email"] = email

        messages.success(request, "OTP sent to your email")
        return render(request, "accounts/otp-verification.html", {
            "purpose": "reset"
        })

    return render(request, "accounts/forgot_password.html")



def reset_password(request):
    if not request.session.get("otp_verified"):
        return redirect("accounts:forgot_password")

    email = request.session.get("reset_email")

    if not email:
        messages.error(request, "Session expired. Please try again.")
        return redirect("accounts:forgot_password")

    user = User.objects.filter(email=email).first()

    if not user:
        messages.error(request, "User does not exist.")
        return redirect("accounts:forgot_password")

    if request.method == "POST":
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("accounts:reset_password")

        user.set_password(password1)
        user.save()

        request.session.pop("otp_verified", None)
        request.session.pop("reset_email", None)
        request.session.pop("otp_purpose", None)
        request.session.pop("otp_email", None)
        login(
            request,
            user,
            backend='django.contrib.auth.backends.ModelBackend'
        )


        messages.success(request, "Password reset successful.")
        return redirect("accounts:profile")
        
    return render(request, "accounts/reset_password.html")



