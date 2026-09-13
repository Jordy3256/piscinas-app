from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
from datetime import date


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contratos", "0016_pago_semestral_adelantado"),
    ]

    operations = [
        migrations.AddField(
            model_name="contrato",
            name="vigencia_meses",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Duración contractual en meses. Vacío significa vigencia indefinida.",
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(120),
                ],
            ),
        ),
        migrations.AddField(
            model_name="contrato",
            name="fecha_fin_contrato",
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text="Último día vigente del ciclo contractual actual.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="contrato",
            name="aviso_vencimiento_dias",
            field=models.PositiveSmallIntegerField(
                default=30,
                help_text="Días de anticipación para advertir que el contrato está por vencer.",
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(365),
                ],
            ),
        ),
        migrations.CreateModel(
            name="RenovacionContrato",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha_renovacion", models.DateField(db_index=True, default=date.today)),
                ("inicio_anterior", models.DateField()),
                ("fin_anterior", models.DateField(blank=True, null=True)),
                ("nuevo_inicio", models.DateField()),
                ("nuevo_fin", models.DateField(blank=True, null=True)),
                ("vigencia_meses", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("observaciones", models.CharField(blank=True, default="", max_length=250)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("contrato", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="renovaciones", to="contratos.contrato")),
                ("registrada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="renovaciones_contrato_registradas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Renovación de contrato",
                "verbose_name_plural": "Renovaciones de contratos",
                "ordering": ["-fecha_renovacion", "-id"],
            },
        ),
    ]
