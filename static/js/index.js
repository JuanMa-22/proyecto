// Configurar DataTables para desactivar alertas molestas
if (typeof $.fn.dataTable !== 'undefined') {
    $.fn.dataTable.ext.errMode = 'none';
}

// ── Funciones para el dropdown de Navegación Lateral ──
function toggleNavDropdown(menuId) {
    const menu = document.getElementById(menuId);
    const chevron = document.getElementById('chevronReportes');
    const btn = document.getElementById('btnReportes');
    if (!menu) return;
    const isOpen = menu.classList.contains('open');
    menu.classList.toggle('open', !isOpen);
    if (chevron) chevron.classList.toggle('rotated', !isOpen);
    if (btn) btn.classList.toggle('open', !isOpen);
}

function abrirNavDropdown(menuId) {
    const menu = document.getElementById(menuId);
    const chevron = document.getElementById('chevronReportes');
    const btn = document.getElementById('btnReportes');
    if (menu) menu.classList.add('open');
    if (chevron) chevron.classList.add('rotated');
    if (btn) btn.classList.add('open');
}


function abrirModal(id) {
    document.getElementById(id).classList.add('active');
}

function cerrarModal(id) {
    document.getElementById(id).classList.remove('active');

    // Si se actualizaron coordenadas automáticamente, recargar página para refrescar el mapa general
    if (id === 'modalEditarEmpresa' && window.coordenadasActualizadas) {
        window.location.reload();
        return;
    }

    // Resetear formulario dentro del modal
    const form = document.querySelector(`#${id} form`);
    if (form) {
        form.reset();
        // Eliminar alertas de error activas
        const activeAlert = form.querySelector('.form-error-alert');
        if (activeAlert) activeAlert.remove();
        
        // Resetear Select2
        if (typeof $ !== 'undefined') {
            $(form).find('select').val('').trigger('change');
        }
    }

    // Resetear detalles y totales de Venta/Compra
    if (id === 'modalCrearVenta') {
        const tbody = document.querySelector('#tablaDetallesVenta tbody');
        if (tbody) {
            tbody.innerHTML = `
                <tr class="placeholder-row">
                    <td colspan="6" class="empty-placeholder">
                        <i class='bx bx-basket'></i>
                        Ningún producto agregado a esta transacción todavía.
                    </td>
                </tr>
            `;
        }
        if (typeof totalVenta !== 'undefined') {
            totalVenta = 0;
            if (typeof actualizarTotalVenta === 'function') actualizarTotalVenta();
        }
    } else if (id === 'modalCrearCompra') {
        const tbody = document.querySelector('#tablaDetallesCompra tbody');
        if (tbody) {
            tbody.innerHTML = `
                <tr class="placeholder-row">
                    <td colspan="6" class="empty-placeholder">
                        <i class='bx bx-basket'></i>
                        Ningún producto agregado a esta transacción todavía.
                    </td>
                </tr>
            `;
        }
        if (typeof totalCompra !== 'undefined') {
            totalCompra = 0;
            if (typeof actualizarTotalCompra === 'function') actualizarTotalCompra();
        }
    }
}

// Función global para mostrar alertas estilizadas en el formulario de un modal
function mostrarErrorFormulario(modalId, mensaje) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    
    const form = modal.querySelector('form');
    if (!form) return;
    
    // Buscar si ya existe una alerta activa para este formulario
    let alertDiv = form.querySelector('.form-error-alert');
    if (!alertDiv) {
        alertDiv = document.createElement('div');
        alertDiv.className = 'form-error-alert';
        // Insertarla justo antes del último elemento del formulario (los botones del footer)
        const lastChild = form.lastElementChild;
        form.insertBefore(alertDiv, lastChild);
    }
    
    // Setear contenido e icono
    alertDiv.innerHTML = `
        <div class="alert-content">
            <i class='bx bx-error-circle'></i>
            <span>${mensaje}</span>
        </div>
        <button type="button" class="alert-close" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // Desplazar el scroll del modal suavemente para que la alerta sea visible
    alertDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    // Eliminar temporizadores previos si existen
    if (alertDiv.dataset.timeoutId) {
        clearTimeout(parseInt(alertDiv.dataset.timeoutId));
    }
    
    // Desvanecer y remover la alerta automáticamente tras 5 segundos
    const timeoutId = setTimeout(() => {
        if (alertDiv && alertDiv.parentElement) {
            alertDiv.style.opacity = '0';
            alertDiv.style.transform = 'translateY(-10px)';
            setTimeout(() => alertDiv.remove(), 300);
        }
    }, 5000);
    
    alertDiv.dataset.timeoutId = timeoutId;
}


document.addEventListener('DOMContentLoaded', function () {
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');

    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', function (e) {
            e.stopPropagation(); // Evita que el evento se propague al document
            sidebar.classList.toggle('active');
        });

        // Cerrar el sidebar al hacer clic en cualquier lugar fuera de él
        document.addEventListener('click', function (e) {
            if (sidebar.classList.contains('active') && 
                !sidebar.contains(e.target) && 
                !menuToggle.contains(e.target)) {
                sidebar.classList.remove('active');
            }
        });
    }

    // Interceptar formularios dentro de modales para envío mediante AJAX
    $(document).on('submit', '.modal form', function (e) {
        const form = this;
        const $form = $(form);

        // Si el formulario explícitamente pide no usar AJAX o ya maneja su propio AJAX
        if ($form.hasClass('no-ajax') || 
            $form.attr('data-ajax') === 'false' || 
            $form.hasClass('ajax-form') || 
            form.id === 'formProveedorRapido' || 
            form.id === 'formProductoRapido' || 
            form.id === 'formClienteRapido') {
            return;
        }

        e.preventDefault();

        const formData = new FormData(form);
        const $submitBtn = $form.find('button[type="submit"]');
        const originalBtnHtml = $submitBtn.html();
        
        $submitBtn.prop('disabled', true).html("<i class='bx bx-loader-alt bx-spin'></i> Guardando...");

        $.ajax({
            url: $form.attr('action') || window.location.href,
            type: $form.attr('method') || 'POST',
            data: formData,
            processData: false,
            contentType: false,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            success: function (response) {
                Swal.fire({
                    position: "top-end",
                    icon: "success",
                    title: response.message || "Guardado exitosamente",
                    showConfirmButton: false,
                    timer: 1500
                }).then(() => {
                    window.location.reload();
                });
            },
            error: function (xhr) {
                $submitBtn.prop('disabled', false).html(originalBtnHtml);
                
                let errorMsg = "Ocurrió un error al procesar la solicitud.";
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMsg = xhr.responseJSON.message;
                } else if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMsg = xhr.responseJSON.error;
                }
                
                Swal.fire({
                    icon: "error",
                    title: "Error",
                    text: errorMsg,
                    confirmButtonColor: "#3085d6"
                });
            }
        });
    });

    // ── Auto-abrir el dropdown de Reportes si la ruta actual es de reportes ──
    const rutasReportes = ['/venta/reportes', '/compra/reportes'];
    const pathActual = window.location.pathname;
    const esRutaReporte = rutasReportes.some(r => pathActual.startsWith(r));
    if (esRutaReporte) {
        abrirNavDropdown('reportesMenu');
    }

    // ── Dropdown de Administración en el Header ──
    const adminDropdownDetails = document.querySelector('.admin-dropdown-container');
    if (adminDropdownDetails) {
        document.addEventListener('click', function (e) {
            if (!adminDropdownDetails.contains(e.target)) {
                adminDropdownDetails.removeAttribute('open');
            }
        });
    }

    // ── Preservar la posición de scroll de la barra lateral ──
    const sidebarElement = document.getElementById('sidebar');
    if (sidebarElement) {
        const scrollPos = sessionStorage.getItem('sidebarScrollPosition');
        if (scrollPos) {
            sidebarElement.scrollTop = parseInt(scrollPos, 10);
        }
        sidebarElement.addEventListener('scroll', function () {
            sessionStorage.setItem('sidebarScrollPosition', sidebarElement.scrollTop);
        });
    }
});
