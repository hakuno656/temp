import json
import os
import socket
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify
)

from werkzeug.security import check_password_hash


app = Flask(__name__)


# =====================================
# CONFIGURACION MANUAL DEL USUARIO
# =====================================

USUARIO = "brayan"

# Pega aquí el hash completo de tu contraseña.
PASSWORD_HASH = "scrypt:32768:8:1$7BO9lVDeaEXsJ86o$e30eab9a109343c009ffa6fd4325bfc5b444bbc885363f3d56240f2649680149eb3156e91f1f7cf7efb43f869504d48b6215b760dfbcba84c73ecf183b5dee77"

# Cambia esta clave por una cadena larga y aleatoria.
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "CAMBIA_ESTA_CLAVE_SECRETA_POR_UNA_ALEATORIA"
)


# =====================================
# CONFIGURACION DEL SERVIDOR TCP
# =====================================

HOST_TCP = "127.0.0.1"
PUERTO_TCP = 65432


def consultar_arduino(comando="GET"):

    with socket.create_connection(
        (HOST_TCP, PUERTO_TCP),
        timeout=3
    ) as conexion:

        conexion.sendall((comando + "\n").encode())

        respuesta = conexion.recv(4096).decode().strip()

    return json.loads(respuesta)


# =====================================
# PROTECCION DE PAGINAS
# =====================================

def requiere_login(funcion):

    @wraps(funcion)
    def verificar(*args, **kwargs):

        if not session.get("autenticado"):

            if request.path.startswith("/api/"):
                return jsonify({
                    "error": "No autorizado"
                }), 401

            return redirect(url_for("login"))

        return funcion(*args, **kwargs)

    return verificar


# =====================================
# PAGINA PRINCIPAL
# =====================================

@app.route("/")
def inicio():

    if session.get("autenticado"):
        return redirect(url_for("panel"))

    return redirect(url_for("login"))


# =====================================
# INICIO DE SESION
# =====================================

@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        usuario = request.form.get("usuario", "")
        password = request.form.get("password", "")

        hash_configurado = (
            PASSWORD_HASH != "PEGUE_AQUI_EL_HASH_COMPLETO"
            and bool(PASSWORD_HASH)
        )

        if (
            hash_configurado
            and usuario == USUARIO
            and check_password_hash(PASSWORD_HASH, password)
        ):

            session.clear()

            session["autenticado"] = True
            session["usuario"] = usuario

            return redirect(url_for("panel"))

        error = (
            "Usuario o contraseña incorrectos. "
            "Revisa la configuración de app.py."
        )

    return render_template(
        "login.html",
        error=error
    )


# =====================================
# PANEL DE TEMPERATURA
# =====================================

@app.route("/panel")
@requiere_login
def panel():

    return render_template(
        "index.html",
        usuario=session.get("usuario", "admin")
    )


# =====================================
# OBTENER TEMPERATURA Y HUMEDAD
# =====================================

@app.route("/api/data")
@requiere_login
def obtener_datos():

    try:

        datos = consultar_arduino("GET")

        return jsonify(datos)

    except (
        OSError,
        ValueError,
        json.JSONDecodeError
    ) as error:

        return jsonify({
            "connected": False,
            "status": str(error)
        }), 503


# =====================================
# MODIFICAR TEMPERATURA OBJETIVO
# =====================================

@app.route("/api/setpoint", methods=["POST"])
@requiere_login
def modificar_objetivo():

    datos = request.get_json(silent=True) or {}

    try:

        objetivo = float(datos.get("setpoint"))

        if not 0 <= objetivo <= 50:
            raise ValueError

    except (TypeError, ValueError):

        return jsonify({
            "ok": False,
            "error": "Usa una temperatura entre 0 y 50"
        }), 400

    try:

        resultado = consultar_arduino(
            f"SET,{objetivo:.1f}"
        )

        return jsonify(resultado)

    except (
        OSError,
        ValueError,
        json.JSONDecodeError
    ) as error:

        return jsonify({
            "ok": False,
            "error": str(error)
        }), 503


# =====================================
# CERRAR SESION
# =====================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =====================================
# EJECUTAR SERVIDOR WEB
# =====================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
