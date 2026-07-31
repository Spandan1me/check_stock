from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_admin_role:
            raise PermissionDenied("Admin access only.")
        return view_func(request, *args, **kwargs)
    return _wrapped


def vendor_or_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not (request.user.is_admin_role or request.user.is_vendor_role):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped
