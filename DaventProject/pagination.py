from rest_framework.pagination import PageNumberPagination


# Paginación por defecto del proyecto: acepta ?page_size= hasta un tope.
# Los catálogos (provincias/ciudades, productos, pagos, facturas) viajan en una
# sola página en vez de encadenar requests de a 10 — el fetchAllPages del
# frontend era una cascada serial por cada lista.
class DaventPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 200
