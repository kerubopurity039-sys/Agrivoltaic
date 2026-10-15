# Agrivoltaic Smart Farming System

## Project Overview

An IoT-based agrivoltaic prototype integrating smart irrigation, movable solar-panel shading and environmental monitoring for Irish potato cultivation.

The system uses an ESP32 microcontroller, a DHT11 temperature and humidity sensor, a resistive analog soil moisture sensor, a 5 V water pump and a servo motor. The ESP32 monitors field conditions, controls irrigation and adjusts a miniature solar-panel model to demonstrate adaptive crop shading.

Oracle Cloud Infrastructure (OCI) is planned for remote monitoring, telemetry storage and data analytics.

## Hardware Components

- ESP32 development board
- DHT11 temperature and humidity sensor
- Resistive analog soil moisture sensor
- 5 V submersible water pump
- Servo motor
- Pump driver and external power supply
- Cardboard prototype structure
- Jumper wires and breadboard

## Repository Structure

- `Firmware.ino` — main ESP32 control program
- `README.md` — project overview and setup instructions

## Software Requirements

- Arduino IDE
- ESP32 board support package
- Adafruit DHT sensor library
- Adafruit Unified Sensor library
- ESP32Servo library

## Getting Started

1. Install Arduino IDE and the ESP32 board support package.
2. Install the required libraries.
3. Open `Firmware.ino`.
4. Select the appropriate ESP32 board and serial port.
5. Verify the sensor pin connections and calibrate the soil moisture sensor.
6. Upload the firmware and inspect readings in Serial Monitor at 115200 baud.
7. Test the servo and pump safely before running the complete system.

## Development Status

The current prototype focuses on local sensor monitoring, automatic irrigation and servo-controlled shading. Oracle Cloud telemetry integration and crop-specific control optimization are planned development stages.

## Team Collaboration

Team members should test changes before merging them into the main branch. Do not commit passwords, private keys, OCI credentials or other secrets to this repository.

## Project Goal

To demonstrate how agrivoltaic technology can combine renewable energy, adaptive crop shading, smart irrigation and cloud-based monitoring to support more efficient and data-driven farming.
