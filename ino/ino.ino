#include <DHT.h>

#define DHTPIN 2
#define DHTTYPE DHT11

const int PIN_ROJO = 9;
const int PIN_VERDE = 10;
const int PIN_AZUL = 11;

DHT dht(DHTPIN, DHTTYPE);

float temperaturaObjetivo = 25.0;

float Kp = 25.0;
float Ki = 0.5;
float Kd = 0.0;

float integral = 0.0;
float errorAnterior = 0.0;

unsigned long tiempoAnterior = 0;
const unsigned long INTERVALO_MS = 2000;

void escribirColor(int rojo, int verde, int azul) {
  analogWrite(PIN_ROJO, constrain(rojo, 0, 255));
  analogWrite(PIN_VERDE, constrain(verde, 0, 255));
  analogWrite(PIN_AZUL, constrain(azul, 0, 255));
}

void procesarComando(String linea) {
  linea.trim();

  if (linea.startsWith("SET,")) {
    float nuevoObjetivo = linea.substring(4).toFloat();

    if (nuevoObjetivo >= 0 && nuevoObjetivo <= 50) {
      temperaturaObjetivo = nuevoObjetivo;
      integral = 0;
      errorAnterior = 0;

      Serial.print("OK,SET,");
      Serial.println(temperaturaObjetivo, 1);
    }
  }
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(100);

  dht.begin();

  pinMode(PIN_ROJO, OUTPUT);
  pinMode(PIN_VERDE, OUTPUT);
  pinMode(PIN_AZUL, OUTPUT);

  escribirColor(0, 0, 255);

  tiempoAnterior = millis();

  Serial.println("READY");
}

void loop() {
  while (Serial.available() > 0) {
    String linea = Serial.readStringUntil('\n');
    procesarComando(linea);
  }

  unsigned long ahora = millis();

  if (ahora - tiempoAnterior < INTERVALO_MS) {
    return;
  }

  float dt = (ahora - tiempoAnterior) / 1000.0;
  tiempoAnterior = ahora;

  float temperatura = dht.readTemperature();
  float humedad = dht.readHumidity();

  if (isnan(temperatura) || isnan(humedad)) {
    Serial.println("ERR,DHT");
    return;
  }

  // Calcular PID
  float error = temperatura - temperaturaObjetivo;

  integral += error * dt;
  integral = constrain(integral, -100.0, 100.0);

  float derivada = 0;

  if (dt > 0) {
    derivada = (error - errorAnterior) / dt;
  }

  errorAnterior = error;

  float salidaPID =
      Kp * error +
      Ki * integral +
      Kd * derivada;

  // Temperatura baja: azul.
  // Temperatura alta: rojo.
  int rojo = constrain((int)(127.5 + salidaPID), 0, 255);
  int azul = 255 - rojo;

  escribirColor(rojo, 0, azul);

  // Enviar información a Ubuntu.
  Serial.print("DATA,");
  Serial.print(temperatura, 1);
  Serial.print(",");
  Serial.print(humedad, 1);
  Serial.print(",");
  Serial.print(temperaturaObjetivo, 1);
  Serial.print(",");
  Serial.print(rojo);
  Serial.print(",0,");
  Serial.println(azul);
}
