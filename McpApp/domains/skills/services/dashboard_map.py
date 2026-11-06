"""
Mapa estático del dashboard de DAVENT para asistentes (bot in-app y tools
MCP). No toca la base de datos: es texto de orientación generado desde la
estructura real del menú.

Fuente de verdad del front: frontend/src/views/DashboardView.vue
(navItems + tabGroups). Si el menú cambia, actualizar este texto.
"""

DASHBOARD_MAP   =   (
    'Mapa del panel (menú lateral → qué hay adentro):\n'
    '- Inicio: resumen del negocio hoy.\n'
    '- Mis productos: catálogo — productos con foto, precio, categorías, '
    'marcas y descuentos.\n'
    '- Mis servicios: servicios que ofrecés, con duración, precio y '
    'consulta por WhatsApp.\n'
    '- Mi página (tu web), con pestañas internas:\n'
    '  · Mi dirección web: link público de tu tienda y dominio propio.\n'
    '  · Mis fotos: logo, foto de portada y galería.\n'
    '  · Diseño: elegir plantilla y estilo/tema, vista previa en vivo, '
    '"Qué mostrar" (páginas y secciones de la web) y acceso al Studio '
    '(editor avanzado, según plan).\n'
    '  · Sobre mi negocio: descripción, horarios, dirección, redes '
    'sociales y WhatsApp de la portada.\n'
    '- Opiniones: reseñas y comentarios de clientes.\n'
    '- Promocionar: QR y folletos para imprimir, y Mis visitas '
    '(estadísticas de tráfico).\n'
    '- Ayuda: el asistente de la cuenta (Tu Asistente), dudas sobre tu '
    'plan, tienda, productos, visitas, pagos y facturas.\n'
    '- Asistente virtual: chatbot que responde a tus clientes dentro de '
    'tu web.\n'
    '- Plan y pagos: Mi plan (cambio y renovación), Pagos y Facturas.\n'
    '- Mi cuenta: datos personales y contraseña.\n'
    '- Novedades: últimas actualizaciones de DAVENT.\n'
    'Deep link: /dashboard?s=<id> abre la sección directo (ids: overview, '
    'catalogs, services, store, photos, design, company, reviews, tools, '
    'stats, support, bot, plans, payments, invoices, settings, changelog).'
)
