import logging
import queue
import subprocess
import threading

log = logging.getLogger('web-scrcpy.uxplay')


class UxPlayManager:
    def __init__(self, name="WebScrcpy-iOS", port_base=7000):
        self.name = name
        self.port_base = port_base
        self.process = None
        self.video_queue = queue.Queue(maxsize=300)
        self._thread = None
        self.running = False

    def start(self):
        if self.process:
            return

        self.running = True
        cmd = [
            "uxplay",
            "-n",
            self.name,
            "-p",
            str(self.port_base),
            "-vs",
            "fdsink fd=1",  # output video to stdout
            "-as",
            "0",  # disable audio
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # hide verbose stderr
                bufsize=10**8,
            )
            log.info("Started uxplay with PID %s", self.process.pid)

            self._thread = threading.Thread(target=self._reader_thread, daemon=True)
            self._thread.start()
        except Exception as e:
            log.error("Failed to start uxplay: %s", e)
            self.running = False

    def _reader_thread(self):
        while self.running and self.process:
            try:
                # 4096 is typically optimal for pipes, adjust if needed
                data = self.process.stdout.read(4096)
                if not data:
                    break

                # If queue is full, drop old frames to avoid huge latency
                if self.video_queue.full():
                    try:
                        self.video_queue.get_nowait()
                    except queue.Empty:
                        pass

                self.video_queue.put(data)
            except Exception as e:
                log.error("Error reading uxplay output: %s", e)
                break

        log.info("uxplay reader thread stopped")
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
                log.error("Error stopping uxplay: %s", e)
            self.process = None
            log.info("uxplay stopped")

    def get_video_stream(self):
        while self.running:
            try:
                data = self.video_queue.get(timeout=1.0)
                yield data
            except queue.Empty:
                continue
