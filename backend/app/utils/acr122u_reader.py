import time
import sys
import ctypes
from typing import Optional, List, Callable
try:
    from smartcard.System import readers
    from smartcard.util import toHexString
    from smartcard.Exceptions import NoCardException, CardConnectionException
    SMARTCARD_AVAILABLE = True
except ImportError:
    SMARTCARD_AVAILABLE = False

# Comando estándar APDU para obtener el UID de la tarjeta NFC (ISO 14443 Type A/B)
APDU_GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
# Comando para activar el Buzzer/LED integrado del ACR122U
APDU_ACR122U_BUZZER = [0xFF, 0x00, 0x40, 0x40, 0x04, 0x01, 0x00, 0x01, 0x01]

def play_beep(freq: int = 2500, duration_ms: int = 100):
    """Emite un pitido de confirmación en el altavoz de la placa/sistema."""
    try:
        if sys.platform == "win32":
            import winsound
            winsound.Beep(freq, duration_ms)
    except Exception:
        pass

def get_nfc_readers() -> List[str]:
    """Obtiene la lista de lectores de tarjetas inteligentes / NFC conectados."""
    if not SMARTCARD_AVAILABLE:
        return []
    try:
        r_list = readers()
        return [str(r) for r in r_list]
    except Exception as e:
        print(f"Error listando lectores: {e}")
        return []

def read_card_uid_once(reader_index: int = 0) -> Optional[str]:
    """
    Intenta leer una tarjeta NFC colocada sobre el lector especificado.
    Retorna el UID en formato hexadecimal en mayúsculas (ej: '04A1B2C3') o None.
    """
    if not SMARTCARD_AVAILABLE:
        return None

    try:
        available_readers = readers()
        if not available_readers or reader_index >= len(available_readers):
            return None

        reader = available_readers[reader_index]
        connection = reader.createConnection()
        connection.connect()

        response, sw1, sw2 = connection.transmit(APDU_GET_UID)

        # 0x90 0x00 indica éxito en APDU
        if sw1 == 0x90 and sw2 == 0x00:
            uid_hex = "".join([f"{b:02X}" for b in response])
            return uid_hex
        return None
    except (NoCardException, CardConnectionException):
        return None
    except Exception as e:
        print(f"Error al leer tarjeta: {e}")
        return None

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
