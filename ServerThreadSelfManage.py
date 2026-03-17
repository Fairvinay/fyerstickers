# ServerThread.py
import threading
import asyncio
import queue
import json
from fyers_apiv3.FyersWebsocket import data_ws


class ServerThreadSelfManage(threading.Thread):
    _instance = None
    message_queue = queue.Queue(
        maxsize=1000
    )  # <-- class-level queue accessible outside

    def __init__(self):
        super().__init__(daemon=True)
        self.accessToken = None
        self.tickers = []
        self._ready_event = threading.Event()

    def set_args(self, accessToken, tickers):
        self.accessToken = accessToken
        self.tickers = tickers
        self._ready_event.set()

    def run(self):
        asyncio.run(self._async_main())

    async def _async_main(self):
        self._ready_event.wait()
        print(f"🚀 Server starting with token={self.accessToken}")
        print(f"📊 Subscribed tickers: {self.tickers}")

        while True:
            print("📡 Starting WebSocket with access_token...")

            def onmessage(message):
                try:
                    ServerThreadSelfManage.message_queue.put(
                        f"data: {json.dumps(message)}\n\n"
                    )
                    print("Response:", message)
                except queue.Full:
                    ServerThreadSelfManage.message_queue.get_nowait()
                    ServerThreadSelfManage.message_queue.put(msg)

            def onerror(message):
                # ServerThreadSelfManage.message_queue.put(f"data: {json.dumps(message)}\n\n")
                try:
                    ServerThreadSelfManage.message_queue.put(
                        f"data: {json.dumps(message)}\n\n"
                    )
                    print("Error:", message)
                except queue.Full:
                    ServerThreadSelfManage.message_queue.get_nowait()
                    ServerThreadSelfManage.message_queue.put(msg)

            def onclose(message):
                # ServerThreadSelfManage.message_queue.put(f"data: {json.dumps(message)}\n\n")
                try:
                    ServerThreadSelfManage.message_queue.put(
                        f"data: {json.dumps(message)}\n\n"
                    )
                    print("Connection closed:", message)
                except queue.Full:
                    ServerThreadSelfManage.message_queue.get_nowait()
                    ServerThreadSelfManage.message_queue.put(msg)

            def onopen():
                data_type = "SymbolUpdate"
                if (
                    isinstance(self.tickers, list)
                    and self.tickers
                    and all(t.strip() for t in self.tickers)
                ):
                    symbols = self.tickers
                else:
                    symbols = [
                        "BSE:SENSEX-INDEX",
                        "NSE:NIFTY50-INDEX",
                        "NSE:NIFTYBANK-INDEX",
                    ]
                    self.tickers = symbols

                fyers.subscribe(symbols=symbols, data_type=data_type)
                ServerThreadSelfManage.message_queue.put(
                    f"data: {json.dumps('connected')}\n\n"
                )

            fyers = data_ws.FyersDataSocket(
                access_token=self.accessToken,
                log_path="",
                litemode=True,
                write_to_file=False,
                reconnect=True,
                on_connect=onopen,
                on_close=onclose,
                on_error=onerror,
                on_message=onmessage
            )

            # fyers.keep_running()
            fyers.connect()

            await asyncio.sleep(5)
            print("Still running with:", self.tickers)

    @classmethod
    def start_once(cls, accessToken, tickers):
        """Start only one ServerThread at a time"""
        if cls._instance is None or not cls._instance.is_alive():
            cls._instance = cls()
            cls._instance.set_args(accessToken, tickers)
            cls._instance.start()
            print("🚀 New ServerThread started")
        else:
            print("⚡ ServerThread already running")
        return cls._instance
