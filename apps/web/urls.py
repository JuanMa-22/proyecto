# pyrefly: ignore [missing-import]
from django.urls import path
# pyrefly: ignore [missing-import]
from apps.web.views import (
    dashboard, inicio_pagina, nosotros_pagina, 
    servicios_pagina, ubicacion_pagina, detalle_producto,
    categoria_pagina
)

app_name='web'

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
    path('', inicio_pagina, name='inicio_pagina'),
    path('nosotros/', nosotros_pagina, name='nosotros_pagina'),
    path('servicios/', servicios_pagina, name='servicios_pagina'),
    path('ubicacion/', ubicacion_pagina, name='ubicacion_pagina'),
    path('productos/<slug:slug>/', detalle_producto, name='detalle_producto'),
    path('categorias/<slug:slug>/', categoria_pagina, name='categoria_pagina'),
]