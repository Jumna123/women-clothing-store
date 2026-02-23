from django import forms
from .models import Category
from .models import Product
from .models import Collection


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['category_image', 'category_name', 'is_active']

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"
        widgets = {
            "description": forms.Textarea(attrs={
                "class": "w-full h-32 bg-transparent border-none p-4 resize-none",
                "placeholder": "Describe the product material, fit, and style details...",
            }),
            "product_name": forms.TextInput(attrs={
                "class": "w-full h-14 bg-[#f8fcfa] border border-border-green rounded-xl px-4",
                "placeholder": "e.g. Floral Summer Maxi Dress",
            }),
            "price": forms.NumberInput(attrs={
                "class": "w-full h-14 bg-[#f8fcfa] border border-border-green rounded-xl pl-8 pr-4",
            }),
            "discount_price": forms.NumberInput(attrs={
                "class": "w-full h-14 bg-[#f8fcfa] border border-border-green rounded-xl pl-8 pr-4",
            }),
            "description": forms.Textarea(attrs={
                "class": "w-full h-32 bg-transparent border-none p-4 resize-none",
                "placeholder": "Describe the product material, fit, and style details...",
            }),
            "stock_quantity": forms.NumberInput(attrs={
                "class": "w-full h-12 bg-[#f8fcfa] border border-border-green rounded-xl px-4",
            }),
            "category": forms.Select(attrs={
                "class": "w-full h-12 bg-[#f8fcfa] border border-border-green rounded-xl px-4",
            }),

        }



class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = [
            "name",
            "description",
            "image",
            "is_active",
            "publish_at",
        ]
