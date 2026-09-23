import sys
import time
import ctypes
from datetime import datetime
from typing import List, Optional

try:
    from smartcard.System import readers
    from smartcard.CardConnection import CardConnection
    from smartcard.Exceptions import NoCardException, CardConnectionException
    SMARTCARD_AVAILABLE = True
except ImportError:
    SMARTCARD_AVAILABLE = False

# Comando estándar APDU para obtener el UID de la tarjeta NFC (ISO 14443 Type A/B)
APDU_GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
# Comando de control del ACR122U para apagar LEDs y buzzer (limpieza de estado)
APDU_ACR122U_LED_RESET = [0xFF, 0x00, 0x40, 0x00, 0x04, 0x00, 0x00, 0x00, 0x00]

# --- Estado persistente de la sesión PC/SC ---
# Reutilizamos UNA conexión y UNA caché de lectores para no abrir contextos
# PC/SC nuevos (y sin cerrar) en cada lectura, causa de lectores bloqueados.
_CONNECTION = None              # Conexión abierta reutilizada entre lecturas
_CONNECTION_INDEX = None        # Índice del lector al que pertenece la conexión
_CONNECTION_ERRORS = 0          # Fallos consecutivos de comunicación
_READERS_CACHE = None           # Objetos Reader() cacheados (contexto reutilizado)
_READERS_CACHE_TIME = 0.0
_READERS_CACHE_TTL = 5.0        # Re-enumerar lectores cada TTL seg
_MAX_ERRORS = 3                 # Umbral de fallos antes de active backoff
_BACKOFF_MAX = 2.0              # Tope del backoff exponencial en segundos


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_reader_list() -> List:
    """Devuelve la lista cacheadas de objetos Reader() (contexto PC/SC reutilizado)."""
    global _READERS_CACHE, _READERS_CACHE_TIME
    if not SMARTCARD_AVAILABLE:
        return []
    now = time.time()
    if _READERS_CACHE is not None and (now - _READERS_CACHE_TIME) < _READERS_CACHE_TTL:
        return _READERS_CACHE
    try:
        _READERS_CACHE = readers()
    except Exception as e:
        print(f"{_now()} [NFC] Error listando lectores: {e}")
        _READERS_CACHE = []
    _READERS_CACHE_TIME = now
    return _READERS_CACHE


def _close_connection(reset_card: bool = False):
    """Cierra la sesión PC/SC e invalida la caché de lectores.

    Si reset_card es True se hace un warm reset del PICC (SCARD_RESET_CARD),
    que reinicia el estado del lector/tarjeta y limpia el estado de error
    (LED parpadeando rápido) del ACR122U.
    """
    global _CONNECTION, _CONNECTION_INDEX, _READERS_CACHE, _READERS_CACHE_TIME
    if _CONNECTION is not None:
        try:
            if reset_card:
                _CONNECTION.disconnect(CardConnection.SCARD_RESET_CARD)
            else:
                _CONNECTION.disconnect()
        except Exception:
            pass
        _CONNECTION = None
    _CONNECTION_INDEX = None
    _READERS_CACHE = None
    _READERS_CACHE_TIME = 0.0


def _connect(reader_index: int = 0):
    """Conecta al lector reutilizando la sesión abierta, o crea una si no existe."""
    global _CONNECTION, _CONNECTION_INDEX
    reader_list = _get_reader_list()
    if not reader_list or reader_index >= len(reader_list):
        _close_connection()
        return None

    if _CONNECTION is not None and _CONNECTION_INDEX == reader_index:
        return _CONNECTION

    _close_connection()
    try:
        connection = reader_list[reader_index].createConnection()
        connection.connect()
    except Exception as e:
        print(f"{_now()} [NFC] No se pudo conectar al lector {reader_index}: {e}")
        return None

    _CONNECTION = connection
    _CONNECTION_INDEX = reader_index

    # Devuelve el lector a un estado conocido: LEDs y buzzer apagados (best effort)
    try:
        connection.transmit(APDU_ACR122U_LED_RESET)
    except Exception:
        pass

    return connection


def get_nfc_readers() -> List[str]:
    """Obtiene la lista de nombres de lectores PC/SC conectados (con caché)."""
    return [str(r) for r in _get_reader_list()]


def _handle_read_error(error: Exception, message: str):
    """Registra el error, cierra la sesión con warm reset y aplica backoff."""
    global _CONNECTION_ERRORS
    _CONNECTION_ERRORS += 1
    print(f"{_now()} [NFC] {message} (intento {_CONNECTION_ERRORS}): {error}")

    # Warm reset del PICC: limpia el estado de error del lector y la tarjeta
    _close_connection(reset_card=True)

    # Backoff exponencial (0.1s -> 0.2s -> 0.4s ... hasta 2s) para no martillar
    # al lector cuando sigue en estado de error.
    if _CONNECTION_ERRORS >= _MAX_ERRORS:
        delay = min(0.1 * (2 ** (min(_CONNECTION_ERRORS, 5) - 1)), _BACKOFF_MAX)
        print(f"{_now()} [NFC] {_CONNECTION_ERRORS} fallos consecutivos. Reintentando en {delay:.1f}s...")
        time.sleep(delay)
    return None


def read_card_uid_once(reader_index: int = 0) -> Optional[str]:
    """
    Lee el UID de una tarjeta NFC colocada sobre el lector especificado.
    Retorna el UID en formato hexadecimal en mayúsculas (ej: '04A1B2C3') o None.

    Reutiliza la misma sesión PC/SC entre lecturas para evitar fugas de
    recursos. Ante errores de comunicación cierra la sesión con warm reset
    del PICC y aplica backoff exponencial para no dejar el lector bloqueado.
    """
    global _CONNECTION_ERRORS
    if not SMARTCARD_AVAILABLE:
        return None

    connection = _connect(reader_index)
    if connection is None:
        return None

    try:
        response, sw1, sw2 = connection.transmit(APDU_GET_UID)
    except NoCardException:
        # Sin tarjeta en el campo: situación normal, no es un error del lector.
        _CONNECTION_ERRORS = 0
        return None
    except CardConnectionException as e:
        return _handle_read_error(e, "Error de comunicación con el lector")
    except Exception as e:
        return _handle_read_error(e, "Error inesperado al leer tarjeta")

    # 0x90 0x00 indica éxito en APDU
    if sw1 == 0x90 and sw2 == 0x00:
        _CONNECTION_ERRORS = 0
        return "".join(f"{b:02X}" for b in response)

    # Respuesta sin error pero sin tarjeta válida reconocida
    _CONNECTION_ERRORS = 0
    return None


def play_beep(freq: int = 2500, duration_ms: int = 100):
    """Emite un pitido de confirmación en el altavoz de la placa/sistema."""
    try:
        if sys.platform == "win32":
            import winsound
            winsound.Beep(freq, duration_ms)
    except Exception:
        pass


def send_keystrokes_windows(text: str, press_enter: bool = True):
    """
    Simula la escritura de texto por teclado en Windows usando la API nativa de Windows (SendInput/keybd_event).
    No requiere librerías externas.
    """
    if sys.platform != "win32":
        return

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    VK_RETURN = 0x0D

    for char in text:
        vk = user32.VkKeyScanW(ord(char))
        if vk != -1:
            shift = (vk >> 8) & 1
            code = vk & 0xFF

            # Si requiere shift (ej. mayúsculas)
            if shift:
                user32.keybd_event(0x10, 0, 0, 0) # Shift down

            user32.keybd_event(code, 0, 0, 0)
            time.sleep(0.01)
            user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)

            if shift:
                user32.keybd_event(0x10, 0, KEYEVENTF_KEYUP, 0) # Shift up

            time.sleep(0.01)

    if press_enter:
        time.sleep(0.02)
        user32.keybd_event(VK_RETURN, 0, 0, 0)
        time.sleep(0.01)
        user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)