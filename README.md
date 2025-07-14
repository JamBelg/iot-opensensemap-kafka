# iot-opensensemap-kafka

iot-opensensemap-kafka is a Python-based IoT project designed to collect, process, and visualize environmental sensor data. It integrates with openSenseMap, Kafka, and other IoT platforms to provide real-time monitoring and analytics.

## Features

- Collects data from various environmental sensors
- Sends data to openSenseMap, Kafka, and other endpoints
- Real-time data visualization
- Modular and extensible architecture

## Installation

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) for container management.
2. Clone the repository:
    ```bash
    git clone https://github.com/JamBelg/iot-opensensemap-kafka.git
    cd iot-opensensemap-kafka
    ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Configure your sensors, Kafka, and ports in `docker-compose.yml`.
2. Run the application using Docker Compose:
    ```bash
    docker-compose up -d --build
    ```

## Contributing

Contributions are welcome! Please submit issues or pull requests via GitHub.

## License

This project is licensed under the MIT License.
