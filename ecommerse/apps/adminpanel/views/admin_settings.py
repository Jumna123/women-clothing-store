from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from apps.adminpanel.models import StoreSettings, PromoCode


def admin_settings(request):
    settings = StoreSettings.get_settings()
    promo_codes = PromoCode.objects.all().order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'save_general':
            settings.marquee_text = request.POST.get('marquee_text', settings.marquee_text)
            settings.cod_enabled = 'cod_enabled' in request.POST
            settings.discounts_enabled = 'discounts_enabled' in request.POST
            settings.free_shipping_threshold = request.POST.get('free_shipping_threshold', settings.free_shipping_threshold)
            settings.standard_shipping_cost = request.POST.get('standard_shipping_cost', settings.standard_shipping_cost)
            settings.express_shipping_cost = request.POST.get('express_shipping_cost', settings.express_shipping_cost)
            settings.return_window_days = int(request.POST.get('return_window_days', 10))  # ← add this
            settings.save()
            messages.success(request, "Settings saved successfully.")
            return redirect('adminpanel:settings')

        elif action == 'add_promo':
            code = request.POST.get('code', '').strip().upper()
            discount = request.POST.get('discount_percent', 0)
            usage_limit = request.POST.get('usage_limit', 0)
            expires_at = request.POST.get('expires_at') or None
            show_on_homepage = 'show_on_homepage' in request.POST  # ← add
            promo_image = request.FILES.get('promo_image')          # ← add

            if not code:
                messages.error(request, "Promo code cannot be empty.")
            elif PromoCode.objects.filter(code=code).exists():
                messages.error(request, f"Code '{code}' already exists.")
            else:
                promo = PromoCode.objects.create(
                    code=code,
                    discount_percent=discount,
                    usage_limit=usage_limit,
                    expires_at=expires_at,
                    show_on_homepage=show_on_homepage,  # ← add
                )
                if promo_image:                          # ← add
                    promo.image = promo_image
                    promo.save()
                messages.success(request, f"Promo code '{code}' created.")
            return redirect('adminpanel:settings')

    return render(request, "adminpanel/adminsettings.html", {
        "settings": settings,
        "promo_codes": promo_codes,
    })


@require_POST
def toggle_promo(request, pk):
    promo = get_object_or_404(PromoCode, pk=pk)
    promo.is_active = not promo.is_active
    promo.save()
    messages.success(request, f"'{promo.code}' {'activated' if promo.is_active else 'deactivated'}.")
    return redirect('adminpanel:settings')


@require_POST
def delete_promo(request, pk):
    promo = get_object_or_404(PromoCode, pk=pk)
    promo.delete()
    messages.success(request, "Promo code deleted.")
    return redirect('adminpanel:settings')