const $ = (id) => document.getElementById(id);

const slider = $("setpoint");
const output = $("setpoint-output");
const label = $("setpoint-label");
const message = $("message");

slider.addEventListener("input", () => {

    const valor = Number(slider.value).toFixed(1);

    output.textContent = `${valor} °C`;
    label.textContent = valor;

});


async function actualizar() {

    try {

        const respuesta = await fetch(
            "/api/data",
            { cache: "no-store" }
        );

        const datos = await respuesta.json();

        if (!respuesta.ok) {
            throw new Error(
                datos.status || "Error de comunicación"
            );
        }

        $("connection").textContent =
            datos.connected
                ? "Arduino conectado"
                : "Arduino desconectado";

        $("connection").className =
            "status-pill " +
            (datos.connected ? "ok" : "bad");

        message.textContent = datos.status || "";

        if (datos.temperature !== null &&
            datos.temperature !== undefined) {

            $("temperature").textContent =
                Number(datos.temperature).toFixed(1);

            $("humidity").textContent =
                Number(datos.humidity).toFixed(0);

            $("red").textContent = datos.red;
            $("green").textContent = datos.green;
            $("blue").textContent = datos.blue;

            const color =
                `rgb(${datos.red},${datos.green},${datos.blue})`;

            $("led-preview").style.backgroundColor = color;

            $("led-preview").style.boxShadow =
                `0 0 28px rgba(${datos.red},${datos.green},${datos.blue},0.35)`;

            slider.value = datos.setpoint;

            output.textContent =
                `${Number(datos.setpoint).toFixed(1)} °C`;

            label.textContent =
                Number(datos.setpoint).toFixed(1);
        }

    } catch (error) {

        $("connection").textContent = "Sin comunicación";

        $("connection").className = "status-pill bad";

        message.textContent = error.message;
    }
}


$("setpoint-form").addEventListener(
    "submit",
    async (evento) => {

        evento.preventDefault();

        message.textContent = "Enviando objetivo...";

        try {

            const respuesta = await fetch(
                "/api/setpoint",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        setpoint: Number(slider.value)
                    })
                }
            );

            const resultado = await respuesta.json();

            if (!respuesta.ok || !resultado.ok) {
                throw new Error(
                    resultado.error || "No se pudo aplicar"
                );
            }

            message.textContent =
                `Objetivo actualizado a ${Number(resultado.setpoint).toFixed(1)} °C`;

            await actualizar();

        } catch (error) {

            message.textContent = error.message;
        }
    }
);


actualizar();

setInterval(actualizar, 2000);
