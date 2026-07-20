from apps.web.views import is_profile_complete

def profile_status(request):
    if not request.user or not request.user.is_authenticated:
        return {}
    return {
        'profile_complete': is_profile_complete(request.user)
    }
