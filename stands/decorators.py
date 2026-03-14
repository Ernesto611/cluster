from django.shortcuts import redirect
from functools import wraps

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request.user, 'tipo_usuario') or request.user.tipo_usuario not in allowed_roles:
                return redirect('acceso_restringido')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
