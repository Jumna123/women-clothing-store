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

            "stock_quantity": forms.NumberInput(attrs={
                "class": "w-full h-12 bg-[#f8fcfa] border border-border-green rounded-xl px-4 focus:border-primary focus:ring-0 transition-colors",
            }),

            # 🔥 CLEAN CATEGORY DROPDOWN
            "category": forms.Select(attrs={
                "class": "w-full h-12 bg-white border border-border-green rounded-xl px-4 focus:border-primary focus:ring-0 transition-colors cursor-pointer",
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
