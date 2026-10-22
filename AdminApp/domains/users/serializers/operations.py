"""

En este modulo se desarrollaran las operaciones logicas que ensucian el clean code en los modulos mixins.py

"""

#=========================
# USER PROFILE 
#=========================

# TAX CONDITION AND TYPE DOCUMENT SELECT
def TypeDocumentSelect(tax, type_dc):
    if tax == 'CF':
        type_dc     =   'DNI'
    else:
        type_dc     =   'CUIT'
    return type_dc

# BUSINESS NAME REQUIRED
def BusinessNameRequired(tax, business):
    if tax != 'CF' and not business:
        return False
    return True

# DOCUMENT FORMAT
def DocumentFormat(type_doc, document):
    errors          =   {}
    if type_doc == 'DNI':
        if len(document) < 7 or len(document) > 8:
            errors['document'] = 'El DNI debe tener entre 7 y 8 dígitos'
        return errors

    if type_doc == 'CUIT':
        if len(document) != 11:
            errors['document'] = 'El CUIT/CUIL debe tener exactamente 11 dígitos'
            return errors

        valid_prefixes  =   ('20', '23', '24', '27', '30', '33', '34')
        if not document.startswith(valid_prefixes):
            errors['document'] = (
                'El CUIT/CUIL debe comenzar con: '
                '20, 23, 24, 27 (personas físicas) o 30, 33, 34 (personas jurídicas)'
            )
            return errors

        coefficients    =   [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        digits          =   [int(d) for d in document]
        total           =   sum(digits[i] * coefficients[i] for i in range(10))
        remainder       =   total % 11
        if remainder == 0:
            expected_digit  =   0
        elif remainder == 1:
            errors['document'] = 'El CUIT/CUIL ingresado no es válido'
            return errors
        else:
            expected_digit  =   11 - remainder

        if digits[10] != expected_digit:
            errors['document'] = 'El CUIT/CUIL ingresado no es válido'

    return errors
#PROVINCE AND CITY COMPARATION
def ProvinceAndCityComparation(prov, city):
    if not prov.cities.filter(pk=city.pk).exists():
        return False
    return True