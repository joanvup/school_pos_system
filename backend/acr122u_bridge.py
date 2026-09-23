import sys
import os
import time
import threading
import argparse
import ctypes
import winsound

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.utils.acr122u_reader import (
    get_nfc_readers,
    read_card_uid_once,
    send_keystrokes_windows,
    play_beep,
    SMARTCARD_AVAILABLE
)

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

STATE = {
    "running": True,
    "connected": False,
    "last_uid": None,
    "reads": 0,
    "tray_icon": None,
}

COOLDOWN_SEC = 1.5

def create_tray_icon(color: str) -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=color, outline="white", width=3)
    return img

def update_tray(icon, connected: bool):
    if icon is None:
        return
    try:
        color = "#22c55e" if connected else "#ef4444"
        icon.icon = create_tray_icon(color)
        status = "Conectado" if connected else "Sin lector"
        icon.title = f"NFC ACR122U | {status}"
    except Exception:
        pass

def on_exit(icon, item):
    STATE["running"] = False
    icon.stop()

def build_tray_menu():
    return pystray.Menu(
        pystray.MenuItem("School POS - Lector NFC", lambda i, it: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            lambda item: f"Estado: {'Conectado' if STATE['connected'] else 'Sin lector'}",
            lambda i, it: None,
            enabled=False
        ),
        pystray.MenuItem(
            lambda item: f"Lecturas: {STATE['reads']}",
            lambda i, it: None,
            enabled=False
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Salir", on_exit),
    )

def run_tray():
    if not TRAY_AVAILABLE:
        return
    icon = pystray.Icon(
        name="acr122u_nfc",
        icon=create_tray_icon("#ef4444"),
        title="NFC ACR122U | Sin lector",
        menu=build_tray_menu()
    )
    STATE["tray_icon"] = icon
    icon.run()

def wedge_loop():
    card_present = False
    absent_count = 0
    ABSENT_CYCLES_THRESHOLD = 4  # Requiere ~400ms de ausencia continua para resetear

    print("[NFC-BRIDGE] Servicio iniciado. Esperando lector ACR122U...")

    while STATE["running"]:
        try:
            available = get_nfc_readers()
            reader_ok = bool(available)

            if reader_ok != STATE["connected"]:
                STATE["connected"] = reader_ok
                update_tray(STATE["tray_icon"], reader_ok)
                if reader_ok:
                    print(f"[NFC-BRIDGE] Lector detectado: {available[0]}")
                    play_beep(1800, 80)
                else:
                    print("[NFC-BRIDGE] Lector desconectado. Esperando reconexion...")
                    card_present = False
                    absent_count = 0

            if not reader_ok:
                time.sleep(2)
                continue

            uid = read_card_uid_once()

            if uid:
                absent_count = 0
                if not card_present:
                    # NUEVA LECTURA (DISPARAR SOLO UNA VEZ)
                    card_present = True
                    print(f"[NFC-BRIDGE] Tarjeta detectada -> UID: {uid}")
                    play_beep(2500, 100)
                    send_keystrokes_windows(uid, press_enter=True)
                    STATE["reads"] += 1
                    time.sleep(0.3)
                # Si la tarjeta sigue apoyada sobre el lector, no hacer nada
            else:
                if card_present:
                    absent_count += 1
                    if absent_count >= ABSENT_CYCLES_THRESHOLD:
                        # La tarjeta se ha retirado fisicamente del lector
                        card_present = False
                        absent_count = 0

            time.sleep(0.1)

        except KeyboardInterrupt:
            break
        except Exception as e:
            time.sleep(1)

    print("[NFC-BRIDGE] Servicio detenido.")

def run_test_mode():
    print("=" * 60)
    print("  MODO PRUEBA - LECTOR NFC ACR122U")
    print("=" * 60)

    if not SMARTCARD_AVAILABLE:
        print("ERROR: El paquete 'pyscard' no esta disponible.")
        return

    available = get_nfc_readers()
    if not available:
        print("AVISO: No se detectaron lectores PC/SC conectados.")
        print("Conecte el lector ACR122U via USB y vuelva a intentar.")
        return

    print(f"Lectores detectados ({len(available)}):")
    for i, r in enumerate(available):
        print(f"  [{i}] {r}")

    print("\nAcerque una tarjeta NFC (Ctrl+C para salir)...\n")
    card_present = False
    absent_count = 0
    try:
        while True:
            uid = read_card_uid_once()
            if uid:
                absent_count = 0
                if not card_present:
                    card_present = True
                    play_beep(2500, 100)
                    print(f"  [TAP] UID: {uid}  ({len(uid)//2} bytes)")
                    time.sleep(0.2)
            else:
                if card_present:
                    absent_count += 1
                    if absent_count >= 4:
                        card_present = False
                        absent_count = 0
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nPrueba finalizada.")

def run_wedge_mode():
    if TRAY_AVAILABLE:
        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()
        time.sleep(0.5)
    else:
        print("[AVISO] pystray/pillow no disponibles. Corriendo sin icono en bandeja.")

    wedge_loop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Puente de lectura NFC para ACR122U")
    parser.add_argument(
        "--mode",
        choices=["wedge", "test"],
        default="wedge",
        help="Modo: 'wedge' (emula teclado + bandeja sistema) | 'test' (diagnostico)"
    )
    args = parser.parse_args()

    if args.mode == "test":
        run_test_mode()
    else:
        run_wedge_mode()
