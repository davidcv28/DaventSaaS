from django.db import models

"""

Creación de modelos para el dominio locations


"""

#=======================================
# ZIPCODE
#=======================================
class ZipCode(models.Model):
    zipcode                     =   models.CharField(max_length = 4, verbose_name = 'Codigo postal')
    class Meta:
        app_label               =   'locations'
        verbose_name_plural     =   'Codigos postales'
    def __str__(self):
        return self.zipcode

#=======================================
# PROVINCE
#=======================================
class Province(models.Model):
    name_province               =   models.CharField(max_length = 150, unique = True, null = False, blank = False)
    class Meta:
        app_label               =   'locations'
        verbose_name            =   'Provincia'
        verbose_name_plural     =   'Provincias'
    def __str__(self):
        return self.name_province
    
#=======================================
# CITY
#=======================================
class City(models.Model):
    name_city                   =   models.CharField(max_length = 150, null = False, blank = False)
    province                    =   models.ForeignKey(Province, on_delete = models.CASCADE, related_name = 'cities', verbose_name = 'provincia', db_index = False)
    zipcode                     =   models.ForeignKey(ZipCode, on_delete = models.RESTRICT, verbose_name = 'Codigo postal', db_index = False )
    class Meta:
        app_label               =   'locations'
        verbose_name            =   'Ciudad'
        verbose_name_plural     =   'Ciudades'
        indexes                 =   [
            models.Index(fields = ['province'], name = 'idx_city_province'),
            models.Index(fields = ['zipcode'], name = 'idx_city_zipcode'),
        ]
    def __str__(self):
        return self.name_city