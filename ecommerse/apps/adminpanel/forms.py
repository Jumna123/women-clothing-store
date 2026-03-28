from django import forms
from .models import Category, Product, Collection
import re


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['category_image', 'category_name', 'is_active']


class ProductForm(forms.ModelForm):

    fabric = forms.CharField(required=False)
    image = forms.ImageField(required=False)

    stock_quantity = forms.IntegerField(
        required=False,
        initial=0,
        min_value=0,  
        widget=forms.NumberInput(attrs={
            "min": "0",   
            "step": "1",  
            "class": "w-full h-12 bg-[#f8fcfa] border border-border-green rounded-xl px-4 focus:border-primary focus:ring-0 transition-colors",
        })
    )

    class Meta:
        model = Product
        exclude = ['slug', 'collections']
        widgets = {
            "product_name": forms.TextInput(attrs={
                "class": "w-full h-14 bg-[#f8fcfa] border border-border-green rounded-xl px-4 focus:border-primary focus:ring-0 transition-colors",
                "placeholder": "e.g. Floral Summer Maxi Dress",
            }),
            "price": forms.NumberInput(attrs={
                "class": "w-full h-14 bg-[#f8fcfa] border border-border-green rounded-xl pl-8 pr-4 focus:border-primary focus:ring-0 transition-colors",
            }),
            "discount_price": forms.NumberInput(attrs={
                "class": "w-full h-14 bg-[#f8fcfa] border border-border-green rounded-xl pl-8 pr-4 focus:border-primary focus:ring-0 transition-colors",
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full h-32 bg-transparent border-none p-4 resize-none",
                "placeholder": "Describe the product material, fit, and style details...",
            }),
            "category": forms.Select(attrs={
                "class": "w-full h-12 bg-white border border-border-green rounded-xl px-4 focus:border-primary focus:ring-0 transition-colors cursor-pointer",
            }),
            "is_available": forms.CheckboxInput(attrs={
                "class": "peer hidden",
            }),
            "color_hex": forms.HiddenInput(),
            "color_name": forms.TextInput(attrs={
                "class": "sr-only",
            }),
        }

    def clean_product_name(self):
        name = self.cleaned_data.get("product_name", "").strip()
        if len(name) < 3:
            raise forms.ValidationError("Product name must be at least 3 characters.")
        if name.isdigit():
            raise forms.ValidationError("Product name cannot be only numbers.")
        if not re.match(r"^[a-zA-Z0-9\s\-'&.,()]+$", name):
            raise forms.ValidationError("Product name contains invalid characters.")
        if not re.search(r"[a-zA-Z]", name):
            raise forms.ValidationError("Product name must contain at least one letter.")
        return name.title()

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price <= 0:
            raise forms.ValidationError("Price must be greater than 0.")
        return price

    def clean_discount_price(self):
        discount_price = self.cleaned_data.get("discount_price")
        if discount_price is not None and discount_price <= 0:
            raise forms.ValidationError("Discount price must be greater than 0.")
        return discount_price

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get("price")
        discount_price = cleaned_data.get("discount_price")
        if price and discount_price and discount_price >= price:
            raise forms.ValidationError({
                "discount_price": "Discount price must be less than the original price."
            })
        return cleaned_data

    def clean_stock_quantity(self):
        value = self.cleaned_data.get("stock_quantity")
        if value is not None and value < 0:
            raise forms.ValidationError("Stock quantity cannot be negative.")
        return value if value is not None else 0


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["name", "description", "image", "is_active", "publish_at"]