"""
Programa de control para matriz LED MAX7219 usando ESP32 y MicroPython
=================================================================

Este programa implementa un servidor web que permite controlar una matriz LED MAX7219
a través de una interfaz web. Sus principales características son:

1. Conectividad WiFi:
   - Se conecta a una red WiFi existente
   - Crea un servidor web en el puerto 80

2. Control de Matriz LED:
   - Utiliza el chip MAX7219 para controlar la matriz LED
   - Muestra texto en scroll horizontal
   - Permite actualizar el mensaje en tiempo real

3. Interfaz Web:
   - Presenta un formulario HTML simple
   - Permite ingresar nuevo texto para mostrar
   - Actualiza el mensaje sin necesidad de reiniciar

4. Características técnicas:
   - Implementa multithreading para el scroll de texto
   - Maneja codificación URL para caracteres especiales
   - Uso eficiente de memoria y recursos

Uso:
1. Conectar el ESP32 con la matriz LED MAX7219
2. Cargar el programa y configurar la conexión WiFi
3. Acceder a la IP del ESP32 desde un navegador
4. Ingresar el texto deseado en el formulario
"""

# Importaciones necesarias para el funcionamiento
try:
    import usocket as socket
except:
    import socket

import max7219_rotate
from machine import Pin, SPI
from time import sleep
from utime import sleep_ms
import wificonnect    
import _thread
thread_lock = _thread.allocate_lock()

# Función principal que muestra el texto en scroll en la matriz LED
def scrolltext(mensaje, n):
    """
    Muestra un mensaje en scroll horizontal en la matriz LED
    mensaje: texto a mostrar
    n: longitud del mensaje
    """
    global new_message_received
    start = 33
    extend = 0 - (n * 8)
    while not new_message_received:
        for i in range(start, extend, -1):
            if new_message_received:
                break
            display.fill(0)
            display.text(mensaje, i, 0, 1)
            display.show()
            sleep(0.1)
        
# Configuración inicial del hardware
# SPI para comunicación con MAX7219 y configuración de pines
texto = 'Inicializando...'
num = len(texto) + 1
ample, alt = 32, 8
spi = SPI(1, baudrate=10000000, polarity=1, phase=0, sck=Pin(4), mosi=Pin(2))  
ss = Pin(15, Pin.OUT)
display = max7219_rotate.Max7219(ample, alt, spi, ss)
display.text(texto, 0, 0, 1)
display.show()

wificonnect.connect()

def form(last_message=""):
    """
    Genera la página web HTML con el formulario
    last_message: último mensaje mostrado para mantenerlo en el campo de texto
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>ESP32 AND MAX7219</title>
        <meta charset="UTF-8">
        <style>
            html, body {{
                font-family: Helvetica;
                display: block;
                margin: 0px auto;
                text-align: center;
                background-color: #cad9c5;
            }}
            #container {{
                width: 100%;
                height: 100%;
                margin-left: 5px;
                margin-top: 20px;
                border: solid 2px;
                padding: 10px;
                background-color: #2dfa53;
            }}
        </style>
    </head>
    <body>
        <h1>Control WiFi de una matriu de LEDs amb ESP32</h1>
        <div id="container">
            <form id="txt_form" name="frmText" method="post">
                <label>Missatge:<input type="text" name="msg" maxlength="255" value="{0}"></label><br>
                <input type="submit" value="Envia Text">
            </form>
        </div>
    </body>
    </html>
    """.format(last_message)
    return html

def url_decode(string):
    """
    Decodifica caracteres especiales de URLs
    Convierte %XX en caracteres y + en espacios
    """
    string = string.replace('+', ' ')
    result = ''
    i = 0
    while i < len(string):
        if string[i] == '%':
            try:
                char_code = int(string[i+1:i+3], 16)
                result += chr(char_code)
                i += 3
            except:
                result += string[i]
                i += 1
        else:
            result += string[i]
            i += 1
    return result

def extract_message(request):
    """
    Extrae el mensaje del request HTTP POST
    Busca el parámetro 'msg=' y obtiene su valor
    """
    msg_start = request.find('msg=') + 4
    msg_end = request.find(' ', msg_start)
    if msg_end == -1:
        msg_end = len(request)
    msg = request[msg_start:msg_end]
    msg = url_decode(msg)
    return msg

# Configuración del servidor web
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)

new_message_received = False
scrolltext_thread = None

# Start displaying the initial message in a loop
scrolltext_thread = _thread.start_new_thread(scrolltext, (texto, num))

# Bucle principal del programa
while True:
    """
    Loop principal que:
    1. Acepta conexiones web
    2. Procesa requests HTTP
    3. Actualiza el mensaje en la matriz LED
    4. Envía la respuesta HTML
    """
    conn, addr = s.accept()
    print('Got a connection from %s' % str(addr))
    request = conn.recv(1024).decode()
    print('Content = %s' % request)
    
    if 'msg=' in request:
        new_texto = extract_message(request)
        if new_texto != texto:
            texto = new_texto
            num = len(texto) + 1
            with thread_lock:
                new_message_received = True
                sleep(0.2)  # Give time for the previous thread to exit
                new_message_received = False
                scrolltext_thread = _thread.start_new_thread(scrolltext, (texto, num))
    
    response = form(texto)
    conn.send('HTTP/1.1 200 OK\n')
    conn.send('Content-Type: text/html\n')
    conn.send('Connection: close\n\n')
    conn.sendall(response)
    conn.close()