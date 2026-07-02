import logging
import subprocess

import wda

log = logging.getLogger('web-scrcpy.wda_manager')


class WDAManager:
    def __init__(self, port=8100, mjpeg_port=9100):
        self.port = port
        self.mjpeg_port = mjpeg_port
        self.process = None
        self.relay_process = None
        self.running = False
        self.client = None
        self.device = None

    def _get_bundle_id(self):
        target_bundle = ''
        try:
            for info in self.device.installation.iter_installed():
                display_name = info.get('CFBundleDisplayName', '')
                if display_name == 'WebDriverAgentRunner-Runner':
                    target_bundle = info['CFBundleIdentifier']
                    return target_bundle
        except Exception as e:
            log.warning("Could not automatically determine bundle id: %s", e)
        # default fallback
        return "com.facebook.WebDriverAgentRunner.xctrunner"

    def start(self):
        if self.running:
            return

        self.running = True

        bundle_id = self._get_bundle_id()
        log.info(f"Using WDA bundle id: {bundle_id}")

        # Start wdaproxy
        cmd_wdaproxy = ["tidevice", "wdaproxy", "-B", bundle_id, "--port", str(self.port)]

        # Start relay for mjpeg (bind local mjpeg_port to device's 9100 where WDA MJPEG server runs)
        cmd_relay = ["tidevice", "relay", str(self.mjpeg_port), "9100"]

        try:
            self.process = subprocess.Popen(
                cmd_wdaproxy,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log.info("Started tidevice wdaproxy with PID %s", self.process.pid)

            self.relay_process = subprocess.Popen(
                cmd_relay,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            log.info("Started tidevice relay with PID %s", self.relay_process.pid)

            self.client = wda.Client(f"http://127.0.0.1:{self.port}")

        except Exception as e:
            log.error("Failed to start WDA: %s", e)
            self.running = False
            self.stop()

    def stop(self):
        self.running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                log.error("Error stopping tidevice wdaproxy: %s", e)
            self.process = None

        if self.relay_process:
            try:
                self.relay_process.terminate()
                self.relay_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.relay_process.kill()
            except Exception as e:
                log.error("Error stopping tidevice relay: %s", e)
            self.relay_process = None

        log.info("WDA stopped")

    def get_client(self):
        return self.client
