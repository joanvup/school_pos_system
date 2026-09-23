import sys
import time
import ctypes
from datetime import datetime
from typing import List, Optional

try:
    from smartcard.System import readers
    from smartcard.CardConnection import CardConnection
    from smartcard.CardRequest import CardRequest
    from smartcard.CardType import AnyCardType
    from smartcard.Exceptions import (
        NoCardException,
        CardConnectionException,
        CardRequestTimeoutException,
    )
    SMARTCARD_AVAILABLE = True
except ImportError:
    SMARTCARD_AVAILABLE = False

# Comando estándar APDU para obtener el UID de la tarjeta NFC (ISO 14443 Type A/B)
APDU_GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]

# Estado del módulo
_CONNECTION_ERRORS = 0          # Fallos consecutivos de comunicación
_READERS_CACHE = None           # Caché de objetos Reader() para no enumerar a cada rato
_READERS_CACHE_TIME = 0.0
_READERS_CACHE_TTL = 5.0        # Re-enumerar lectores cada TTL seg
_MAX_ERRORS = 3                 # Umbral de fallos antes de activar backoff
_BACKOFF_MAX = 2.0              # Tope del backoff exponencial en segundos


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_reader_list() -> List:
    """Devuelve la lista de objetos Reader() con caché (TTL)."""
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


def get_nfc_readers() -> List[str]:
    """Obtiene la lista de nombres de lectores PC/SC conectados (con caché)."""
    return [str(r) for r in _get_reader_list()]


def _backoff():
    """Backoff exponencial (0.1s -> 0.2s -> 0.4s ... hasta 2s) ante errores repetidos."""
    global _CONNECTION_ERRORS
    if _CONNECTION_ERRORS >= _MAX_ERRORS:
        delay = min(0.1 * (2 ** (min(_CONNECTION_ERRORS, 5) - 1)), _BACKOFF_MAX)
        print(f"{_now()} [NFC] {_CONNECTION_ERRORS} fallos consecutivos. Reintentando en {delay:.1f}s...")
        time.sleep(delay)
    return None


def _transmit_uid_with_retry(connection, retries: int = 3) -> Optional[str]:
    """Transmite GetUID sobre una conexión ya abierta.

    Solo se usa justo después de que una tarjeta llega (un tope por tarjeta),
    nunca sobre un lector vacío ni sobre una tarjeta ya leída/re-apoyada.
    """
    global _CONNECTION_ERRORS
    for attempt in range(retries):
        try:
            response, sw1, sw2 = connection.transmit(APDU_GET_UID)
        except NoCardException:
            # La retiraron justo entre el evento y la lectura
            return None
        except CardConnectionException as e:
            _CONNECTION_ERRORS += 1
            print(f"{_now()} [NFC] Error de comunicación (intento {attempt + 1}/{retries}): {e}")
            time.sleep(0.05 * (attempt + 1))
            continue
        except Exception as e:
            print(f"{_now()} [NFC] Error inesperado al leer UID: {e}")
            break

        # 0x90 0x00 indica éxito en APDU
        if sw1 == 0x90 and sw2 == 0x00:
            _CONNECTION_ERRORS = 0
            return "".join(f"{b:02X}" for b in response)

        # Error APDU no crítico (tarjeta incompatible o en transición)
        print(f"{_now()} [NFC] GetUID devolvió SW={sw1:02X}{sw2:02X}")
        return None
    return None


def read_next_card_uid(reader_index: int = 0, timeout: float = 1.5) -> Optional[str]:
    """Espera a que LLEGUE una tarjeta nueva y devuelve su UID.

    Diseñado para no bloquear el ACR122U:
    - La espera se hace por estado PC/SC (SCardGetStatusChange), SIN enviar
      APDUs contra un lector vacío.
    - newcardonly=True: mientras la misma tarjeta siga apoyada, NO se re-lee
      (nada de GetUID repetido sobre una tarjeta activa, causa del bloqueo).

    Devuelve el UID hex (ej: '04A1B2C3') o None si timeout/sin tarjeta.
    """
    global _CONNECTION_ERRORS
    if not SMARTCARD_AVAILABLE:
        return None

    reader_list = _get_reader_list()
    if not reader_list or reader_index >= len(reader_list):
        return None

    try:
        with CardRequest(
            newcardonly=True,
            readers=[reader_list[reader_index]],
            cardType=AnyCardType(),
            timeout=timeout,
        ) as request:
            try:
                service = request.waitforcard()
            except CardRequestTimeoutException:
                # Sin tarjeta nueva en el tiempo esperado: vuelve a intentar sin ruido
                return None

            connection = service.connection
            try:
                connection.connect()
                return _transmit_uid_with_retry(connection)
            finally:
                try:
                    connection.disconnect()
                except Exception:
                    pass
    except CardRequestTimeoutException:
        return None
    except Exception as e:
        _CONNECTION_ERRORS += 1
        print(f"{_now()} [NFC] Error en espera de tarjeta (intento {_CONNECTION_ERRORS}): {e}")
        return _backoff()


def read_card_uid_once(reader_index: int = 0) -> Optional[str]:
    """Una lectura inmediata (sin espera). Útil para diagnóstico.

    Devuelve el UID de la tarjeta si hay una sobre el lector, o None.
    """
    global _CONNECTION_ERRORS
    if not SMARTCARD_AVAILABLE:
        return None

    reader_list = _get_reader_list()
    if not reader_list or reader_index >= len(reader_list):
        return None

    try:
        connection = reader_list[reader_index].createConnection()
        connection.connect()
        try:
            return _transmit_uid_with_retry(connection)
        finally:
            try:
                connection.disconnect()
            except Exception:
                pass
    except NoCardException:
        return None
    except CardConnectionException as e:
        _CONNECTION_ERRORS += 1
        print(f"{_now()} [NFC] Error de comunicación en lectura directa: {e}")
        return _backoff()
    except Exception as e:
        _CONNECTION_ERRORS += 1
        print(f"{_now()} [NFC] Error inesperado en lectura directa: {e}")
        return _backoff()


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