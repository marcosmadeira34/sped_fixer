from django.conf import settings
from django.conf.urls.static import static
from core.views import FixSped
from django.urls import path

urlpatterns = [
    # ... suas outras URLs ...
    path('fix-sped/', FixSped.as_view(), name='fix_sped'),
]

# Adicionar serving de arquivos de mídia (apenas para desenvolvimento)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)