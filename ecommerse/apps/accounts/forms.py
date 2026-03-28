from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, EmailVerificationRequest,Address
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required



class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)


    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()

        if User.objects.filter(email=email).exists():
            raise ValidationError("User already exists")

        if EmailVerificationRequest.objects.filter(email=email).exists():
            raise ValidationError("Verification already pending")

        return email
    
    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password and confirm and password != confirm:
            raise ValidationError("Passwords do not match")

        return cleaned_data
    

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        exclude = ['user']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
                'placeholder': 'e.g. Jane Doe'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
                'placeholder': '+91 00000 00000'
            }),
            'house_name': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
                'placeholder': 'House / Flat No.'
            }),
            'street': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
                'placeholder': 'Street name'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
            }),
            'state': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
                'placeholder': '000000'
            }),
            # ✅ hide is_default — handled via checkbox in template manually
            'is_default': forms.HiddenInput(),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) < 10:
            raise forms.ValidationError("Enter a valid phone number with at least 10 digits.")
        return phone

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode', '').strip()
        if not pincode.isdigit() or len(pincode) != 6:
            raise forms.ValidationError("Enter a valid 6-digit pincode.")
        return pincode
    
@login_required
def add_address(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user

            # ✅ handle set_default checkbox from template
            if request.POST.get('set_default') or not Address.objects.filter(user=request.user).exists():
                Address.objects.filter(user=request.user).update(is_default=False)
                address.is_default = True

            address.save()
            messages.success(request, "Address added successfully.")
        else:
            messages.error(request, "Please fix the errors below.")
    return redirect("accounts:address_list")
    






