#Rediseño generativo de plantillas (fase 2): el catálogo público pasa de 3
#a 6 diseños, dos por nivel de plan:
#   raiz / alimentos      (base,     generalista y gastronomía)
#   trama / boutique      (plus,     indumentaria y moda premium)
#   circuito / seguridad  (advanced, tecnología y seguridad industrial)
#'boutique' deja de ser un id retirado (ya no está en TEMPLATE_RETIRED_MAP)
#y 'alimentos'/'seguridad' son ids nuevos. También entran las fuentes jost,
#barlow y barlow-condensed al catálogo cerrado de name_font. Sin cambios de
#datos: solo choices (el default sigue siendo 'raiz').
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0053_redesign_template_catalog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='storecustomization',
            name='name_font',
            field=models.CharField(choices=[('inter', 'Inter'), ('roboto', 'Roboto'), ('open-sans', 'Open Sans'), ('lato', 'Lato'), ('montserrat', 'Montserrat'), ('poppins', 'Poppins'), ('raleway', 'Raleway'), ('nunito', 'Nunito'), ('work-sans', 'Work Sans'), ('dm-sans', 'DM Sans'), ('sora', 'Sora'), ('space-grotesk', 'Space Grotesk'), ('comfortaa', 'Comfortaa'), ('quicksand', 'Quicksand'), ('rubik', 'Rubik'), ('oswald', 'Oswald'), ('bebas-neue', 'Bebas Neue'), ('anton', 'Anton'), ('archivo-black', 'Archivo Black'), ('righteous', 'Righteous'), ('orbitron', 'Orbitron'), ('playfair-display', 'Playfair Display'), ('merriweather', 'Merriweather'), ('lora', 'Lora'), ('fraunces', 'Fraunces'), ('cinzel', 'Cinzel'), ('pacifico', 'Pacifico'), ('dancing-script', 'Dancing Script'), ('caveat', 'Caveat'), ('lobster', 'Lobster'), ('space-mono', 'Space Mono'), ('jetbrains-mono', 'JetBrains Mono'), ('manrope', 'Manrope'), ('archivo', 'Archivo'), ('bricolage-grotesque', 'Bricolage Grotesque'), ('figtree', 'Figtree'), ('cormorant-garamond', 'Cormorant Garamond'), ('dm-serif-display', 'DM Serif Display'), ('libre-baskerville', 'Libre Baskerville'), ('outfit', 'Outfit'), ('plus-jakarta-sans', 'Plus Jakarta Sans'), ('jost', 'Jost'), ('barlow', 'Barlow'), ('barlow-condensed', 'Barlow Condensed')], default='inter', max_length=40, verbose_name='Fuente del nombre'),
        ),
        migrations.AlterField(
            model_name='storecustomization',
            name='template',
            field=models.CharField(choices=[('raiz', 'Raíz'), ('alimentos', 'Alimentos'), ('trama', 'Trama'), ('boutique', 'Boutique'), ('circuito', 'Circuito'), ('seguridad', 'Seguridad')], default='raiz', max_length=12, verbose_name='Diseño de la web'),
        ),
        migrations.AlterField(
            model_name='storecustomization',
            name='template_draft',
            field=models.CharField(choices=[('raiz', 'Raíz'), ('alimentos', 'Alimentos'), ('trama', 'Trama'), ('boutique', 'Boutique'), ('circuito', 'Circuito'), ('seguridad', 'Seguridad')], default='raiz', max_length=12, verbose_name='Diseño de la web (borrador)'),
        ),
    ]
