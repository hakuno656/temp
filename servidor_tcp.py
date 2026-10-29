import json
import socket
import threading
import time

import serial

PUERTO_ARDUINO = "/dev/ttyACM0"
VELOCIDAD = 9600

HOST = "127.0.0.1"
PUERTO_TCP = 65432

estado = {
    "connected": False,
    "temperature": None,
    "humidity": None,
    "setpoint": 25.0,
    "red": 0,
    "green": 0,
    "blue": 255,
    "status": "Esperando Arduino"
}

lock = threading.Lock()
arduino = None


def conectar_arduino():
    global arduino

    try:
        arduino = serial.Serial(
            PUERTO_ARDUINO,
            VELOCIDAD,
            timeout=1
        )

        time.sleep(2)

        with lock:
            estado["connected"] = True
            estado["status"] = "Arduino conectado"

        print("Arduino conectado correctamente")

        return True

    except (serial.SerialException, OSError) as error:
        print("Error al conectar:", error)

        with lock:
            estado["connected"] = False
            estado["status"] = str(error)

        return False


def leer_arduino():
    global arduino

    while True:

        if arduino is None or not arduino.is_open:
            if not conectar_arduino():
                time.sleep(3)
                continue

        try:
            linea = arduino.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if not linea:
                continue

            print("Arduino:", linea)

            partes = linea.split(",")

            if len(partes) == 7 and partes[0] == "DATA":

                with lock:
                    estado.update({
                        "connected": True,
                        "temperature": float(partes[1]),
                        "humidity": float(partes[2]),
                        "setpoint": float(partes[3]),
                        "red": int(partes[4]),
                        "green": int(partes[5]),
                        "blue": int(partes[6]),
                        "status": "Datos actualizados"
                    })

            elif linea == "ERR,DHT":

                with lock:
                    estado["status"] = "Error del sensor DHT11"

        except (
            serial.SerialException,
            OSError,
            ValueError
        ) as error:

            print("Error serial:", error)

            with lock:
                estado["connected"] = False
                estado["status"] = str(error)

            try:
                arduino.close()
            except Exception:
                pass

            arduino = None
            time.sleep(2)


def atender_cliente(conexion):

    try:
        conexion.settimeout(3)

        solicitud = conexion.recv(1024).decode().strip()

        if solicitud == "GET":

            with lock:
                respuesta = dict(estado)

            conexion.sendall(
                (json.dumps(respuesta) + "\n").encode()
            )

        elif solicitud.startswith("SET,"):

            valor = float(solicitud.split(",", 1)[1])

            if not 0 <= valor <= 50:
                raise ValueError(
                    "La temperatura debe estar entre 0 y 50"
                )

            if arduino is None or not arduino.is_open:
                raise ConnectionError("Arduino desconectado")

            arduino.write(
                f"SET,{valor:.1f}\n".encode()
            )

            with lock:
                estado["setpoint"] = valor

            respuesta = {
                "ok": True,
                "setpoint": valor
            }

            conexion.sendall(
                (json.dumps(respuesta) + "\n").encode()
            )

        else:
            conexion.sendall(
                b'{"ok":false,"error":"Comando desconocido"}\n'
            )

    except Exception as error:

        try:
            conexion.sendall(
                (json.dumps({
                    "ok": False,
                    "error": str(error)
                }) + "\n").encode()
            )
        except OSError:
            pass

    finally:
        conexion.close()


def iniciar_servidor():

    servidor = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    servidor.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    servidor.bind((HOST, PUERTO_TCP))
    servidor.listen(10)

    print("Servidor TCP iniciado en el puerto 65432")

    while True:

        conexion, direccion = servidor.accept()

        threading.Thread(
            target=atender_cliente,
            args=(conexion,),
            daemon=True
        ).start()


if __name__ == "__main__":

    threading.Thread(
        target=leer_arduino,
        daemon=True
    ).start()

    iniciar_servidor()
