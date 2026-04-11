from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Order
from django.utils import timezone
from datetime import timedelta


@shared_task
def send_order_confirmation_email(order_id):
    try:
        order = Order.objects.get(id=order_id)
        send_mail(
            subject=f'Order Confirmed — #ORD-{order.id}',
            message=f'''
Hi {order.user.first_name},

Your order #ORD-{order.id} has been confirmed!

Total: ₹{order.total_amount}
Payment: {order.get_payment_method_display()}

We'll notify you when it ships.

Thank you for shopping with us!
            ''',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
    except Order.DoesNotExist:
        pass


@shared_task
def send_payment_failed_email(order_id):
    try:
        order = Order.objects.get(id=order_id)
        send_mail(
            subject=f'Payment Failed — #ORD-{order.id}',
            message=f'''
Hi {order.user.first_name},

Unfortunately your payment for order #ORD-{order.id} of ₹{order.total_amount} could not be completed.

Please try again or contact support.
            ''',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
    except Order.DoesNotExist:
        pass


@shared_task
def cancel_unpaid_orders():
    """Runs periodically — cancels Razorpay orders unpaid after 30 minutes."""
    cutoff = timezone.now() - timedelta(minutes=30)
    unpaid_orders = Order.objects.filter(
        payment_method='razorpay',
        status='pending',
        created_at__lt=cutoff
    )
    count = unpaid_orders.update(status='cancelled')
    return f'{count} unpaid orders cancelled'