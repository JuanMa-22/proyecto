from apps.empresa.models import Empresa

def canonical(request):
    """
    Returns a clean absolute canonical URL without query parameters.
    And the global Empresa configuration object.
    """
    return {
        'canonical_url': request.build_absolute_uri(request.path),
        'empresa': Empresa.objects.first()
    }
