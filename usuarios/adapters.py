from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils import timezone

class GoogleSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):

        user = super().save_user(request, sociallogin, form=form)

        extra = sociallogin.account.extra_data or {}

        given_name = extra.get('given_name') or extra.get('name')
        family_name = extra.get('family_name')
        picture = extra.get('picture')
        google_uid = extra.get('sub')

        user.tipo_usuario = 'cliente'
        user.verificado = True
        user.email_verificado = timezone.now()

        if given_name and not getattr(user, 'aNombre', None):
            user.aNombre = given_name
        if family_name is not None and not getattr(user, 'aApellido', None):
            user.aApellido = family_name

        if google_uid and not getattr(user, 'aToken', None):
            user.aToken = str(google_uid)

        user.save()

        return user
