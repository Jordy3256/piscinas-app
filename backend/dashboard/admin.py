from django.contrib import admin
from .models import PushSubscription, Notificacion


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "updated_at")
    search_fields = ("user__username", "endpoint")
    list_filter = ("created_at", "updated_at")


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("user", "titulo", "leida", "creada_en", "leida_en")
    search_fields = ("user__username", "titulo", "mensaje", "url")
    list_filter = ("leida", "creada_en", "leida_en")