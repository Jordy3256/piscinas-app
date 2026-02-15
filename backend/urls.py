from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

from dashboard.views import login_view, logout_view

urlpatterns = [
    # Página raíz → Home del dashboard
    path('', lambda request: redirect('/dashboard/home/')),

    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    path('dashboard/', include('dashboard.urls')),
]

# ✅ Servir archivos MEDIA en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
