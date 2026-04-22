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
                'type': 'text',
                'autocomplete': 'name',
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
            }),
            'phone': forms.TextInput(attrs={
                'type': 'tel',
                'autocomplete': 'tel',
                'inputmode': 'numeric',
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
            }),
            'house_name': forms.TextInput(attrs={
                'type': 'text',
                'autocomplete': 'address-line1',
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
            }),
            'street': forms.TextInput(attrs={
                'type': 'text',
                'autocomplete': 'address-line2',
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
            }),
            'city': forms.TextInput(attrs={
                'type': 'text',
                'autocomplete': 'address-level2',
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
            }),
            'state': forms.TextInput(attrs={
                'type': 'text',
                'autocomplete': 'address-level1',
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
            }),
            'pincode': forms.TextInput(attrs={
                'type': 'text',
                'autocomplete': 'postal-code',
                'inputmode': 'numeric',
                'maxlength': '6',
                'class': 'w-full rounded-lg border border-border-light dark:border-border-dark bg-background-light dark:bg-background-dark text-text-main dark:text-white px-4 py-2.5 focus:ring-primary focus:border-primary',
            }),
            'is_default': forms.HiddenInput(),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        digits = ''.join(filter(str.isdigit, phone))
        if len(digits) != 10:
            raise forms.ValidationError("Enter a valid 10-digit phone number.")
        if digits[0] not in '6789':
            raise forms.ValidationError("Enter a valid Indian mobile number starting with 6, 7, 8, or 9.")
        return digits

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode', '').strip()
        if not pincode.isdigit() or len(pincode) != 6:
            raise forms.ValidationError("Enter a valid 6-digit pincode.")
        if pincode[0] == '0':
            raise forms.ValidationError("Pincode cannot start with 0.")
        return pincode

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if not all(c.isalpha() or c.isspace() for c in city):
            raise forms.ValidationError("City should contain only letters.")
        return city.title()

    def clean_state(self):
        state = self.cleaned_data.get('state', '').strip()
        if not all(c.isalpha() or c.isspace() for c in state):
            raise forms.ValidationError("State should contain only letters.")
        return state.title()
    
@login_required
def add_address(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user

            if request.POST.get('set_default') or not Address.objects.filter(user=request.user).exists():
                Address.objects.filter(user=request.user).update(is_default=False)
                address.is_default = True

            address.save()
            messages.success(request, "Address added successfully.")
        else:
            messages.error(request, "Please fix the errors below.")
    return redirect("accounts:address_list")
    






