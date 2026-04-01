from .models import User

def associate_by_email(backend, details, user=None, *args, **kwargs):
    """
    If a user already exists with this email, return them
    instead of creating a duplicate.
    """
    if user:
        return {'user': user}

    email = details.get('email')
    if not email:
        return

    try:
        existing_user = User.objects.get(email=email)
        return {'user': existing_user}
    except User.DoesNotExist:
        return