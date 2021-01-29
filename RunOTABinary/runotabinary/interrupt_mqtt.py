import time
import paho.mqtt.client as mqtt
from runotabinary.configs.config_project import OtaProject
from runotabinary.logger import logger
from pathlib import Path


class InterruptMQTTConnection:

    def __init__(self, otaProject):
        self.project = otaProject
        self.connected_to_iot = False

    def get_thing_certificate(self):
        cert = open(self.project.client_cert_path, 'r')
        return cert.read() 

    def get_thing_private_key(self):
        cert = open(self.project.client_private_key_path, 'r')
        return cert.read()

    def interrupt_mqtt_connection(self):
        """
        Create a dummy device copy to connect to IoT which will disconnect the
        actual device. Used for interrupting device connection to cloud.
        :return: If the operation is successful it returns PASS else FAIL
        """
        def on_connect(client, userdata, flags, rc):
            """ Callback function to notify that the connection is successful
            """
            logger.info("Connected to IoT core. Device should now disconnect then reconnect.")
            self.connected_to_iot = True
            mqtt_client.disconnect()
            mqtt_client.loop_stop()

        # Create temporary files to store the certificates. This is a limitation of the
        # python ssl module since we cannot pass the certificates directly.

        certfile = Path("tmp_cert.pem")
        keyfile = Path("tmp_key.pem")
        certfile.write_text(self.get_thing_certificate())
        keyfile.write_text(self.get_thing_private_key())

        # Initialize the paho mqtt client
        mqtt_client = mqtt.Client(client_id=self.project.thing_name)
        mqtt_client.tls_set(certfile=certfile, keyfile=keyfile)
        mqtt_client.on_connect = on_connect
        mqtt_client.connect(self.project.aws_iot_endpoint, 8883, 60)
        mqtt_client.loop_start()

        # Wait up to 10 second until we connect to the IoT core
        timeout = time.perf_counter() + 10
        while self.connected_to_iot != True and time.perf_counter() < timeout:
            time.sleep(1)

        # Delete the temporary credential files.
        certfile.unlink()
        keyfile.unlink()

        # Notify the connection status
        if self.connected_to_iot:
            self.connected_to_iot = False
            return 1
        else:
            return 2

def main():
    task = InterruptMQTTConnection(OtaProject())
    task.interrupt_mqtt_connection() 
    

if __name__ == "__main__":
    main()