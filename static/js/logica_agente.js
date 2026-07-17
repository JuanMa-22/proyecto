let agenteSocket = null;
let activeBotDiv = null;
let acumuladoBotText = "";

// ── TTS (Text-to-Speech con edge-tts) ──
let vozActivada = true;          // Por defecto ACTIVADO
let audioTtsActual = null;       // Referencia al Audio actual para poder detenerlo

// Intentar abrir la conexión WebSocket al cargar la página
window.addEventListener('DOMContentLoaded', (event) => {
    conectarWebsocket();
});

function conectarWebsocket() {
    if (agenteSocket && (agenteSocket.readyState === WebSocket.OPEN || agenteSocket.readyState === WebSocket.CONNECTING)) {
        return;
    }

    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    
    // Si estamos en la página de inicio, nosotros, servicios o contacto, forzamos modo cliente
    const esPaginaPublicaCliente = window.location.pathname === '/' || 
                                   window.location.pathname.startsWith('/nosotros') || 
                                   window.location.pathname.startsWith('/servicios') || 
                                   window.location.pathname.startsWith('/contacto');
    
    const wsUrl = `${wsScheme}://${window.location.host}/ws/agente-conversacional/?client_mode=${esPaginaPublicaCliente}`;

    console.log("Conectando al canal WebSocket del Agente Conversacional... Modo Cliente Forzado: " + esPaginaPublicaCliente);
    agenteSocket = new WebSocket(wsUrl);

    agenteSocket.onopen = function() {
        console.log("Conexión WebSocket establecida.");
    };

    agenteSocket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        const indicadorEscribiendo = document.getElementById('agenteTypingIndicator');
        const contenedorMensajes = document.getElementById('agenteMessages');

        if (data.type === 'typing') {
            if (data.is_typing) {
                indicadorEscribiendo.style.display = 'flex';
                contenedorMensajes.appendChild(indicadorEscribiendo); // Asegurar que queda al final
                desplazarAbajo();
            } else {
                indicadorEscribiendo.style.display = 'none';
            }
        } else if (data.type === 'token') {
            if (!activeBotDiv) {
                activeBotDiv = agregarMensajeVacio('bot');
            }
            acumuladoBotText += data.token;
            actualizarMensaje(activeBotDiv, acumuladoBotText);
        } else if (data.type === 'done') {
            if (activeBotDiv) {
                actualizarMensaje(activeBotDiv, data.full_text);
            }
            activeBotDiv = null;
            acumuladoBotText = "";
            indicadorEscribiendo.style.display = 'none';
            // Reproducir voz si está activada
            if (vozActivada && data.full_text) {
                reproducirVozAgente(data.full_text);
            }
        } else if (data.type === 'error') {
            indicadorEscribiendo.style.display = 'none';
            agregarMensaje('bot', '⚠️ Error: ' + data.message);
            activeBotDiv = null;
            acumuladoBotText = "";
        }
    };

    agenteSocket.onclose = function(e) {
        console.warn("Canal WebSocket del agente cerrado. Reintentando en 3 segundos...", e);
        setTimeout(conectarWebsocket, 3000);
    };

    agenteSocket.onerror = function(err) {
        console.error("Error detectado en el WebSocket: ", err);
        agenteSocket.close();
    };
}

function alternarAgente() {
    const ventanaChat = document.getElementById('agenteWindow');
    if (ventanaChat.style.display === 'none' || ventanaChat.style.display === '') {
        ventanaChat.style.display = 'flex';
        document.getElementById('agenteInput').focus();
        conectarWebsocket();
        desplazarAbajo();
    } else {
        ventanaChat.style.display = 'none';
    }
}

function manejarEnterAgente(evento) {
    if (evento.key === 'Enter') {
        enviarMensajeAgente();
    }
}

function enviarMensajeAgente() {
    const input = document.getElementById('agenteInput');
    const mensaje = input.value.trim();

    if (!mensaje) return;

    // Agregar mensaje del usuario a la vista
    agregarMensaje('user', mensaje);
    input.value = '';

    // Asegurar que el socket esté conectado y enviar
    if (agenteSocket && agenteSocket.readyState === WebSocket.OPEN) {
        agenteSocket.send(JSON.stringify({ 'message': mensaje }));
        
        // Mostrar indicador de escritura inmediatamente
        const indicadorEscribiendo = document.getElementById('agenteTypingIndicator');
        const contenedorMensajes = document.getElementById('agenteMessages');
        indicadorEscribiendo.style.display = 'flex';
        contenedorMensajes.appendChild(indicadorEscribiendo);
        desplazarAbajo();
    } else {
        agregarMensaje('bot', '⚠️ Error: No hay conexión con el servidor. Intentando reconectar...');
        conectarWebsocket();
    }
}

function agregarMensaje(remitente, texto) {
    const contenedor = document.getElementById('agenteMessages');
    const indicadorEscribiendo = document.getElementById('agenteTypingIndicator');

    const divMsg = document.createElement('div');
    divMsg.className = `chat-msg ${remitente}`;

    const divContent = document.createElement('div');
    divContent.className = 'msg-content';
    divContent.innerHTML = parsearMarkdown(texto);

    const spanTime = document.createElement('span');
    spanTime.className = 'msg-time';
    spanTime.textContent = obtenerHoraActual();

    divMsg.appendChild(divContent);
    divMsg.appendChild(spanTime);

    // Insertar antes del indicador de escritura
    contenedor.insertBefore(divMsg, indicadorEscribiendo);
    desplazarAbajo();
    return divMsg;
}

function agregarMensajeVacio(remitente) {
    const contenedor = document.getElementById('agenteMessages');
    const indicadorEscribiendo = document.getElementById('agenteTypingIndicator');

    const divMsg = document.createElement('div');
    divMsg.className = `chat-msg ${remitente}`;

    const divContent = document.createElement('div');
    divContent.className = 'msg-content';

    const spanTime = document.createElement('span');
    spanTime.className = 'msg-time';
    spanTime.textContent = obtenerHoraActual();

    divMsg.appendChild(divContent);
    divMsg.appendChild(spanTime);

    contenedor.insertBefore(divMsg, indicadorEscribiendo);
    desplazarAbajo();
    return divMsg;
}

function actualizarMensaje(divMsg, texto) {
    const divContent = divMsg.querySelector('.msg-content');
    divContent.innerHTML = parsearMarkdown(texto);
    desplazarAbajo();
}

function desplazarAbajo() {
    const contenedor = document.getElementById('agenteMessages');
    contenedor.scrollTop = contenedor.scrollHeight;
}

function obtenerHoraActual() {
    const ahora = new Date();
    return ahora.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/* --- Parseador de Markdown Ultra-Liviano con Soporte de Tablas --- */
function parsearMarkdown(texto) {
    if (!texto) return "";
    let html = texto;

    // Escapar caracteres HTML básicos para prevenir inyecciones
    html = html
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Reconstruir los tags de salto de línea
    html = html.replace(/\n/g, "<br>");

    // 0. Eliminar imágenes de markdown (![alt](url)) para no mostrarlas en el chat
    html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '');

    // 0.1. Parsear enlaces de markdown ([texto](url))
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" style="color: #ff5722; text-decoration: underline; font-weight: bold;">$1</a>');

    // 1. Detectar y estructurar tablas de markdown (| col 1 | col 2 |)
    const lineas = html.split('<br>');
    let procesandoTabla = false;
    let tablaHTML = "";
    let lineasProcesadas = [];

    for (let i = 0; i < lineas.length; i++) {
        let linea = lineas[i].trim();
        
        if (linea.startsWith('|') && linea.endsWith('|')) {
            const celdas = linea.split('|').map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
            
            // Ignorar la línea separadora de th/td (ej: |---|---|)
            if (linea.includes('---') || linea.includes('===') || linea.match(/^\|[\s\-\|:]+\|$/)) {
                continue;
            }

            if (!procesandoTabla) {
                // Iniciar nueva tabla
                procesandoTabla = true;
                tablaHTML = "<table><thead><tr>";
                celdas.forEach(c => {
                    tablaHTML += `<th>${c}</th>`;
                });
                tablaHTML += "</tr></thead><tbody>";
            } else {
                // Fila de cuerpo de tabla
                tablaHTML += "<tr>";
                celdas.forEach(c => {
                    tablaHTML += `<td>${c}</td>`;
                });
                tablaHTML += "</tr>";
            }
        } else {
            if (procesandoTabla) {
                // Cerrar tabla anterior
                tablaHTML += "</tbody></table>";
                lineasProcesadas.push(tablaHTML);
                procesandoTabla = false;
                tablaHTML = "";
            }
            lineasProcesadas.push(lineas[i]);
        }
    }
    // Si la tabla quedó abierta al final
    if (procesandoTabla) {
        tablaHTML += "</tbody></table>";
        lineasProcesadas.push(tablaHTML);
    }
    
    html = lineasProcesadas.join('<br>');

    // 2. Bold (**texto**)
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 3. Viñetas de lista (- item o * item)
    // Se procesa línea por línea
    const lineasLista = html.split('<br>');
    let enLista = false;
    let lineasListaProcesadas = [];

    for (let i = 0; i < lineasLista.length; i++) {
        let linea = lineasLista[i].trim();
        if (linea.startsWith('- ') || linea.startsWith('* ')) {
            let contenido = linea.substring(2);
            if (!enLista) {
                enLista = true;
                lineasListaProcesadas.push('<ul><li>' + contenido + '</li>');
            } else {
                lineasListaProcesadas.push('<li>' + contenido + '</li>');
            }
        } else {
            if (enLista) {
                enLista = false;
                // Cerrar la lista en la línea anterior o insertar cierre
                if (lineasListaProcesadas.length > 0) {
                    lineasListaProcesadas[lineasListaProcesadas.length - 1] += '</ul>';
                }
            }
            lineasListaProcesadas.push(lineasLista[i]);
        }
    }
    if (enLista && lineasListaProcesadas.length > 0) {
        lineasListaProcesadas[lineasListaProcesadas.length - 1] += '</ul>';
    }

    html = lineasListaProcesadas.join('<br>');

    // Corregir br sobrantes antes/después de tablas y listas
    html = html.replace(/<br><table>/g, '<table>');
    html = html.replace(/<\/table><br>/g, '</table>');
    html = html.replace(/<br><ul>/g, '<ul>');
    html = html.replace(/<\/ul><br>/g, '</ul>');
    html = html.replace(/<\/li><br><li>/g, '</li><li>');

    return html;
}

/* --- Text-to-Speech (TTS con edge-tts en servidor) --- */

/**
 * Alterna la voz del agente entre activada y desactivada.
 * Actualiza el ícono y el tooltip del botón de forma visual.
 */
function alternarVozAgente() {
    vozActivada = !vozActivada;
    const btn  = document.getElementById('agenteTtsBtn');
    const icon = document.getElementById('agenteTtsIcon');

    if (vozActivada) {
        btn.classList.add('active');
        btn.title = 'Voz activada — clic para silenciar';
        icon.className = 'fas fa-volume-up';
    } else {
        btn.classList.remove('active');
        btn.title = 'Voz desactivada — clic para activar';
        icon.className = 'fas fa-volume-mute';
        // Detener cualquier audio que esté reproduciéndose
        if (audioTtsActual) {
            audioTtsActual.pause();
            audioTtsActual.currentTime = 0;
            audioTtsActual = null;
        }
    }
}

/**
 * Llama al endpoint /agente-conversacional/tts/ para generar audio
 * con edge-tts y lo reproduce en el navegador.
 * @param {string} texto - Texto completo de la respuesta del agente.
 */
async function reproducirVozAgente(texto) {
    try {
        // Obtener la URL del endpoint TTS desde el data-attribute del DOM
        const agenteWindow = document.getElementById('agenteWindow');
        const ttsUrl = agenteWindow ? agenteWindow.dataset.ttsUrl : '/agente-conversacional/tts/';

        // Detener audio anterior si aún está sonando
        if (audioTtsActual) {
            audioTtsActual.pause();
            audioTtsActual.currentTime = 0;
            audioTtsActual = null;
        }

        // Mostrar indicador de voz en el botón mientras carga
        const icon = document.getElementById('agenteTtsIcon');
        if (icon) icon.className = 'fas fa-circle-notch fa-spin';

        // Enviar el texto al servidor para síntesis de voz
        const formData = new FormData();
        formData.append('text', texto);

        const respuesta = await fetch(ttsUrl, {
            method: 'POST',
            body: formData
        });

        if (!respuesta.ok) {
            console.warn('TTS: el servidor devolvió un error', respuesta.status);
            if (icon) icon.className = 'fas fa-volume-up';
            return;
        }

        // Convertir la respuesta en URL de audio y reproducir
        const blob = await respuesta.blob();
        const audioUrl = URL.createObjectURL(blob);
        audioTtsActual = new Audio(audioUrl);

        // Restaurar ícono cuando el audio termina
        audioTtsActual.onended = () => {
            if (icon) icon.className = 'fas fa-volume-up';
            URL.revokeObjectURL(audioUrl);
            audioTtsActual = null;
        };

        audioTtsActual.onerror = () => {
            if (icon) icon.className = 'fas fa-volume-up';
            audioTtsActual = null;
        };

        if (icon) icon.className = 'fas fa-volume-up';
        await audioTtsActual.play();

    } catch (err) {
        console.error('Error reproduciendo TTS:', err);
        const icon = document.getElementById('agenteTtsIcon');
        if (icon) icon.className = 'fas fa-volume-up';
        audioTtsActual = null;
    }
}

/* --- Reconocimiento de Voz (Speech to Text) --- */
let reconocimiento = null;
let estaEscuchando = false;

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    reconocimiento = new SpeechRecognition();
    reconocimiento.lang = 'es-BO'; // Español - Bolivia
    reconocimiento.continuous = false;
    reconocimiento.interimResults = false;

    reconocimiento.onstart = function() {
        estaEscuchando = true;
        document.getElementById('agenteMicBtn').classList.add('listening');
        document.getElementById('agenteMicIcon').className = 'fas fa-microphone-slash';
        console.log("Micrófono escuchando...");
    };

    reconocimiento.onresult = function(event) {
        const transcripcion = event.results[0][0].transcript;
        console.log("Texto escuchado:", transcripcion);
        const input = document.getElementById('agenteInput');
        input.value = (input.value + " " + transcripcion).trim();
        input.focus();
    };

    reconocimiento.onerror = function(event) {
        console.error("Error en reconocimiento de voz:", event.error);
        desactivarMicrofono();
    };

    reconocimiento.onend = function() {
        desactivarMicrofono();
    };
} else {
    // Si el navegador no soporta SpeechRecognition, ocultar el botón de micrófono
    document.getElementById('agenteMicBtn').style.display = 'none';
}

function alternarMicrofonoAgente() {
    if (!reconocimiento) return;

    if (estaEscuchando) {
        reconocimiento.stop();
    } else {
        reconocimiento.start();
    }
}

function desactivarMicrofono() {
    estaEscuchando = false;
    document.getElementById('agenteMicBtn').classList.remove('listening');
    document.getElementById('agenteMicIcon').className = 'fas fa-microphone';
    console.log("Micrófono apagado.");
}

/**
 * Abre la ventana del chatbot (si está oculta) y envía un mensaje predefinido inmediatamente
 */
function enviarMensajeChatDirecto(texto) {
    if (!texto) return;

    // 1. Abrir la ventana del chat si está oculta
    const ventanaChat = document.getElementById('agenteWindow');
    if (ventanaChat.style.display === 'none' || ventanaChat.style.display === '') {
        alternarAgente();
    }

    // 2. Esperar brevemente a que el socket se conecte (si no lo estaba) y enviar el mensaje
    let intentos = 0;
    function intentarEnviar() {
        if (agenteSocket && agenteSocket.readyState === WebSocket.OPEN) {
            // Agregar el mensaje visualmente en la conversación
            agregarMensaje('user', texto);

            // Enviar a través de websocket
            agenteSocket.send(JSON.stringify({ 'message': texto }));

            // Mostrar el indicador de carga/escribiendo
            const indicadorEscribiendo = document.getElementById('agenteTypingIndicator');
            const contenedorMensajes = document.getElementById('agenteMessages');
            indicadorEscribiendo.style.display = 'flex';
            contenedorMensajes.appendChild(indicadorEscribiendo);
            desplazarAbajo();
        } else if (intentos < 20) {
            // Si la conexión está en proceso, esperar 150ms y reintentar (hasta 3 segundos)
            intentos++;
            setTimeout(intentarEnviar, 150);
        } else {
            console.error("No se pudo establecer conexión WebSocket para enviar el mensaje directo.");
        }
    }

    intentarEnviar();
}
