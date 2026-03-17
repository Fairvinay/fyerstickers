import threading
import asyncio

class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)  # daemon=True → dies when main program exits
        self.accessToken = None
        self.tickers = []
        self._ready_event = threading.Event()

    def set_args(self, accessToken, tickers):
        """Set arguments before starting the server"""
        self.accessToken = accessToken
        self.tickers = tickers
        self._ready_event.set()  # signal that args are ready

    def run(self):
        """Entry point for thread"""
        asyncio.run(self._async_main())

    async def _async_main(self):
        # Wait until args are set
        self._ready_event.wait()
        print(f"🚀 Starting asyncio server with token={self.accessToken}")
        print(f"📊 Tickers = {self.tickers}")

        # Here you put your asyncio server code
        while True:
            await asyncio.sleep(5)
            print("Still running with:", self.tickers)