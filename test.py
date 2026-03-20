from fyers_apiv3.FyersWebsocket import data_ws
from fyers_apiv3 import fyersModel as fyersV3
from flask import (
    Flask,
    request,
    redirect,
    render_template,
    Response,
    render_template_string,
    stream_with_context,
)
from flask_cors import CORS
from flask import jsonify
from multiprocessing import Process
import requests
import threading
from threading import Thread
import webbrowser
import time, os, json
import sys, queue
import asyncio
import random  # <-- add this
from ServerThread import ServerThread
from ServerThreadSelfManage import ServerThreadSelfManage
import aiohttp
import asyncio

import ssl

# 🔥 create unsafe SSL context (for local/dev only)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


# === Configuration ===S
client_id = os.environ.get("client_id", "V8BNUWJ4WQ-100")  # "P67RJAS1M6-100"
# client_id = os.environ.get("client_id", "TRLV2A6GPL-100")
# "TRLV2A6GPL-100"
secret_key = os.environ.get("secret_key", "KOA61TZLP4")  # "4LXEKKMFUL"
# secret_key = os.environ.get("secret_key", "V72MPISUJC")
# "V72MPISUJC"
# redirec_base_url = os.environ.get("redirec_base_url", "https://192.168.1.3:8888")
redirec_base_url = os.environ.get(
    "redirec_base_url", "https://successrate.netlify.app"
)  # "https://fyersbook.netlify.app"
# redirect_uri = "https://192.168.1.4:8888/.netlify/functions/netlifystockfyersbridge/api/fyersauthcodeverify"
redirect_uri = (
    redirec_base_url.rstrip("/")
    + "/.netlify/functions/netlifystockfyersbridge/api/fyersauthcodeverify"
)
# ===== CONFIG =====
API_URL = "https://successrate.netlify.app/.netlify/functions/netlifystockfyersticker/api/fyersgetbsecequote"
# API_URL = "https://192.168.1.3:8888/.netlify/functions/netlifystockfyersticker/api/fyersgetbsecequote"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
API_KEY = "CKFRQC4GPZQUB56W"

SYMBOL_MAP = {
    "BSE:SENSEX-INDEX": "SENSEX-INDEX",
    "NSE:NIFTY50-INDEX": "NIFTY50-INDEX",
    "NSE:NIFTYBANK-INDEX": "NIFTYBANK-INDEX",
}


response_type = "code"
grant_type = "authorization_code"
state = "python_test"

auth_code_received = None
flask_process = None  # Will store reference to the running Process

# A queue to pass messages from websocket thread to SSE stream
message_queue = queue.Queue()
outgoing = asyncio.Queue()

tickers_global = ["NSE:NIFTY2631023150CE"]
threadsocket = None
# Create the server thread (not started yet)
# server_thread = ServerThread()
server_thread = None

# Store the token globally after login
global_access_token = None
# Store the sessoni globally after login
global_session = None
# === Step 1: Flask server to receive auth_code ===
app = Flask(__name__)
cors_url = redirec_base_url.rstrip("/")
CORS(app, supports_credentials=True, resources={r"/stream*": {"origins": cors_url}})

# Read env variable and parse into list
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [
    origin.strip() for origin in allowed_origins.split(",") if origin.strip()
]

if ALLOWED_ORIGINS:  # checks list is not empty
    print("Allowed origins found:", ALLOWED_ORIGINS)
else:
    ALLOWED_ORIGINS = [
        "https://successrate.netlify.app",
        "https://fyersbook.netlify.app",
        "https://onedinaar.com",
        "https://192.168.1.7:8888",
        "https://192.168.1.3:8888",
        "https://192.168.1.3:3000",
    ]
    print("Allowed origins configured from hard code")

headers = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Access-Control-Allow-Origin": redirec_base_url.rstrip("/"),
    "Access-Control-Allow-Credentials": "true",
}


class CustomError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ===== FETCH FUNCTION =====
async def fetch_spot(session, symbol):
    global global_access_token  # ✅ IMPORTANT

    try:
        params = {
            "access_token": global_access_token,  # ✅ USE GLOBAL
            "symbol": symbol,
            "apikey": API_KEY,
        }

        async with session.get(API_URL, params=params, ssl=False) as res:
            # ✅ handle non-JSON safely
            if res.status != 200:
                text = await res.text()
                print(f"❌ API Error ({symbol}):", text[:200])
                return None

            try:
                data = await res.json()
            except Exception:
                text = await res.text()
                print(f"❌ Not JSON ({symbol}):", text[:200])
                return None

            ltp = data.get("ltp") or data.get("d", [{}])[0].get("v", {}).get("lp")

            if ltp:
                return float(ltp)

    except Exception as e:
        print(f"❌ Failed to fetch {symbol}: {e}")

    return None


async def initialize_prices_async():
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_spot(session, "SENSEX-INDEX"),
            fetch_spot(session, "NIFTY50-INDEX"),
            fetch_spot(session, "NIFTYBANK-INDEX"),
        ]

        results = await asyncio.gather(*tasks)

        return {
            "BSE:SENSEX-INDEX": results[0] or 74207.24,
            "NSE:NIFTY50-INDEX": results[1] or 23002.15,
            "NSE:NIFTYBANK-INDEX": results[2] or 53451.00,
        }


# ===== INITIALIZE SPOT VALUES =====
def initialize_prices():
    import asyncio

    return asyncio.run(initialize_prices_async())


async def main_socket():
    # This is where you would do your main program logic
    while True:
        if not threadsocket.is_alive():
            print("starting  asyncio server with fyers acess token ")


async def run_server(acctoken, tickers):
    task = asyncio.create_task(main_socket())
    server = await asyncio.start_server(handle_client, "localhost", 15555)
    async with server:
        try:
            await server.serve_forever()
        except asyncio.CancelledError:
            print("🛑 Server shutting down...")
            task.cancel()
            await task


async def handle_client(reader, writer, acctoken, tickers):
    asyncio.create_task(handle_outgoing(writer, acctoken, tickers))


async def handle_outgoing(writer, access_token_input, tickers):
    while True:
        message = await outgoing.get()
        packet = json.dumps(message) + "\r\n"
        print("📡 Starting WebSocket with access_token...")

        def onmessage(message):
            """
            Callback function to handle incoming messages from the FyersDataSocket WebSocket.
            Parameters:
            message (dict): The received message from the WebSocket.
            """
            # return Response(f"data: {json.dumps(message)}\n\n", mimetype="text/event-stream")
            message_queue.put(f"data: {json.dumps(message)}\n\n")
            print("Response:", message)

        def onerror(message):
            """
            Callback function to handle WebSocket errors.
            Parameters:
                message (dict): The error message received from the WebSocket.
            """
            message_queue.put(f"data: {json.dumps(message)}\n\n")
            print("Error:", message)
            # return Response(f"data: {json.dumps(message)}\n\n", mimetype="text/event-stream")

        def onclose(message):
            """
            Callback function to handle WebSocket connection close events.
            """
            message_queue.put(f"data: {json.dumps(message)}\n\n")
            print("Connection closed:", message)
            # return Response(f"data: {json.dumps(message)}\n\n", mimetype="text/event-stream")

        def onopen():
            """
            Callback function to subscribe to data type and symbols upon WebSocket connection.
            """
            # Specify the data type and symbols you want to subscribe to
            data_type = "SymbolUpdate"

            # Subscribe to the specified symbols and data type
            # symbols = ['NSE:NIFTY2590924900PE', 'NSE:NIFTY50-INDEX', 'NSE:NIFTY2590924900CE', 'NSE:NIFTY2590925000PE',
            #           'NSE:NIFTY2590925000CE']
            # Validate: must be a list, non-empty, and all elements non-empty strings
            if (
                isinstance(tickers, list)
                and len(tickers) > 0
                and all(t.strip() for t in tickers)
            ):
                symbols = tickers
            else:
                # Default fallback
                symbols = [
                    "BSE:SENSEX-INDEX",
                    "NSE:NIFTY50-INDEX",
                    "NSE:NIFTYBANK-INDEX",
                ]
            fyers.subscribe(symbols=symbols, data_type=data_type)
            ter = "connected"
            message_queue.put(f"data: {json.dumps(ter)}\n\n")
            # return Response(f"data: {json.dumps(ter)}\n\n", mimetype="text/event-stream")

            # Replace the sample access token with your actual access token obtained from Fyers
            access_token = access_token_input

        # Create a FyersDataSocket instance with the provided parameters
        fyers = data_ws.FyersDataSocket(
            access_token=access_token_input,  # Access token in the format "appid:accesstoken"
            log_path="",  # Path to save logs. Leave empty to auto-create logs in the current directory.
            litemode=True,  # Lite mode disabled. Set to True if you want a lite response.
            write_to_file=False,  # Save response in a log file instead of printing it.
            reconnect=True,  # Enable auto-reconnection to WebSocket on disconnection.
            on_connect=onopen,  # Callback function to subscribe to data upon connection.
            on_close=onclose,  # Callback function to handle WebSocket connection close events.
            on_error=onerror,  # Callback function to handle WebSocket errors.
            on_message=onmessage,  # Callback function to handle incoming messages from the WebSocket.
        )

        # Keep the socket running to receive real-time data
        fyers.keep_running()

        # Establish a connection to the Fyers WebSocket
        fyers.connect()
        writer.write(packet.encode("utf-8"))
        await writer.drain()


def start_asyncio_server(acctoken, tickers):
    acctoken = global_access_token
    tickers = tickers_global
    asyncio.run(run_server(acctoken, tickers))


# Start background websocket thread
threadsocket = threading.Thread(
    target=start_asyncio_server, args=(global_access_token, tickers_global)
)


@app.errorhandler(CustomError)
def handle_custom_error(error):
    response = jsonify({"message": error.message})
    response.status_code = error.status_code
    return response


@app.errorhandler(Exception)
def handle_generic_exception(error):
    # Log the full traceback for debugging
    app.logger.exception("An unhandled exception occurred.")
    response = jsonify({"message": "An unexpected error occurred."})
    response.status_code = 500
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/raise_error")
def raise_error():
    raise CustomError("Something specific went wrong!", status_code=422)


@app.route("/login")
def login():
    global global_session
    session = fyersV3.SessionModel(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type="code",
        state=state,
    )
    auth_url = session.generate_authcode()
    # Store the token globally after login
    global_session = session
    print("auth_url:", auth_url)
    return redirect(auth_url)


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# 3. Handle Fyers redirect + trigger WebSocket
@app.route("/redirect")
def callback():
    global global_access_token
    auth_code = request.args.get("auth_code")
    received_state = request.args.get("state")
    # session = global_session if global_session is not None else None

    if not auth_code:
        return "❌ Authorization failed", 400

    try:
        session = fyersV3.SessionModel(
            client_id=client_id,
            secret_key=secret_key,
            redirect_uri=redirect_uri,
            response_type="code",
            grant_type="authorization_code",
        )
        session.set_token(auth_code)
        response = session.generate_token()
        if "access_token" in response:
            global_access_token = response["access_token"]
            access_token = response["access_token"]
            # Save token for later use
            # with open("access_token.txt", "w") as f:
            #    f.write(access_token)

            order_variables = {"secret_value": global_access_token}
            # Pass dictionary by unpacking
            if received_state == "python_test":
                return render_template("market-feed.html", **order_variables)
            elif received_state == "python_order":
                return render_template("orders.html", **order_variables)
            elif received_state == "python_position":
                return render_template("orders-positions.html", **order_variables)
            """
            # Trigger WebSocket
            threading.Thread(target=start_websocket, args=(access_token,)).start()

            def event_stream():
                while True:
                    msg = message_queue.get()
                    if msg is None:
                        break
                    yield msg

            return Response(event_stream(), mimetype="text/event-stream", headers=headers)
            """
        else:
            return f"❌ Failed to generate token: {response}"

    except Exception as e:
        return f"❌ Error: {str(e)}", 500


@app.route("/stream")
def stream():
    global global_access_token
    global tickers_global
    access_token = request.args.get("accessToken")
    print("Received access_token...")
    global_access_token = access_token

    ACCESS_TOKEN = access_token
    # 🔥 STEP 1: Initialize real SPOT values
    # prices = initialize_prices()
    prices = {
        "BSE:SENSEX-INDEX": 74969.2,
        "NSE:NIFTY50-INDEX": 23240.6,
        "NSE:NIFTYBANK-INDEX": 54123.44,
    }

    print("✅ Initial SPOT prices:", prices)

    # 🔥 STEP 2: Create ranges dynamically
    ranges = {
        "BSE:SENSEX-INDEX": (
            prices["BSE:SENSEX-INDEX"] - 3,
            prices["BSE:SENSEX-INDEX"] + 3,
        ),
        "NSE:NIFTY50-INDEX": (
            prices["NSE:NIFTY50-INDEX"] - 1.5,
            prices["NSE:NIFTY50-INDEX"] + 1.5,
        ),
        "NSE:NIFTYBANK-INDEX": (
            prices["NSE:NIFTYBANK-INDEX"] - 1.2,
            prices["NSE:NIFTYBANK-INDEX"] + 1.2,
        ),
    }

    movement = {
        "BSE:SENSEX-INDEX": (3.5, 8.5),
        "NSE:NIFTY50-INDEX": (1.5, 2.9),
        "NSE:NIFTYBANK-INDEX": (2.0, 3.9),
    }

    symbols = list(prices.keys())

    # Option 1: If repeated params
    tickers = request.args.getlist("tickers")
    tickers_global = tickers
    print("Tickers:", tickers)
    print("Access Token:", access_token)
    # if not threadsocket.is_alive():
    # threadsocket.start()
    ServerThreadSelfManage.start_once(access_token, tickers)

    @stream_with_context
    def event_stream():
        try:
            while True:
                try:
                    # 🔥 STEP 3: Try real queue data first
                    msg = ServerThreadSelfManage.message_queue.get(timeout=45)
                    print(f"msg {msg}")
                    if msg == 'data: "connected"\n\n':
                        symbol = random.choice(symbols)
                        min_range, max_range = ranges[symbol]
                        min_move, max_move = movement[symbol]
                        direction = random.choice([-1, 1])
                        step = random.uniform(min_move, max_move)
                        prices[symbol] += direction + step
                        # Clamp
                        prices[symbol] = max(min_range, min(max_range, prices[symbol]))
                        simulated_msg = {
                            "ltp": round(prices[symbol], 2),
                            "symbol": symbol,
                            "type": "if",
                        }
                        yield f"data: {json.dumps(simulated_msg)}\n\n"
                    elif msg:
                        yield msg
                    else:
                        yield "data: heartbeat\n\n"

                except queue.Empty:
                    # 🔥 STEP 4: Simulated fallback

                    symbol = random.choice(symbols)

                    min_range, max_range = ranges[symbol]
                    min_move, max_move = movement[symbol]

                    direction = random.choice([-1, 1])
                    step = random.uniform(min_move, max_move)

                    prices[symbol] += direction + step

                    # Clamp
                    prices[symbol] = max(min_range, min(max_range, prices[symbol]))

                    simulated_msg = {
                        "ltp": round(prices[symbol], 2),
                        "symbol": symbol,
                        "type": "if",
                    }

                    yield f"data: {json.dumps(simulated_msg)}\n\n"
        except GeneratorExit:
            # This happens when client disconnects
            print("⚠️ Client disconnected from /stream")
            print(f"Client {request.remote_addr} closed connection")
        except Exception as e:
            print("❌ Error in event_stream:", e)

    # Consumer function
    def consumer():
        def event_stream():
            while True:
                msg = message_queue.get()
                if msg is None:
                    break
                yield msg

        """
                def event_stream():
                    while True:
                        yield f"data: hello at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        time.sleep(1)
        """
        return Response(event_stream(), mimetype="text/event-stream")

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
    """ 
    try:
        # Create producer and consumer threads
        producer_thread = threading.Thread(target=start_websocket, args=(access_token,tickers))
        consumer_thread = threading.Thread(target=consumer)

        # Start the threads
        producer_thread.start()
        consumer_thread.start()

        # Wait for producer to finish, then signal consumer to stop
        producer_thread.join()
        #message_queue.put(None)
        consumer_thread.join()

    except Exception as e:
        print(f"Caught exception: {type(e)}")
        print(f"Exception message: {e}")
        #handle_generic_exception(f"Exception message: {e}")
    """
    """
    def event_stream():
        while True:
            msg = message_queue.get()
            if msg is None:
                break
            yield msg
    
    def event_stream():
        while True:
            yield f"data: hello at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            time.sleep(1)
    
    return Response(event_stream(), mimetype="text/event-stream")
    """


# 4. WebSocket Connection Function
def start_websocket(access_token_input, tickers):
    print("📡 Starting WebSocket with access_token...")

    def onmessage(message):
        """
        Callback function to handle incoming messages from the FyersDataSocket WebSocket.

        Parameters:
            message (dict): The received message from the WebSocket.

        """
        message_queue.put(f"data: {json.dumps(message)}\n\n")
        print("Response:", message)

    def onerror(message):
        """
        Callback function to handle WebSocket errors.

        Parameters:
            message (dict): The error message received from the WebSocket.


        """
        print("Error:", message)

    def onclose(message):
        """
        Callback function to handle WebSocket connection close events.
        """
        print("Connection closed:", message)

    def onopen():
        """
        Callback function to subscribe to data type and symbols upon WebSocket connection.

        """
        # Specify the data type and symbols you want to subscribe to
        data_type = "SymbolUpdate"

        # Subscribe to the specified symbols and data type
        # symbols = ['NSE:NIFTY2590924900PE', 'NSE:NIFTY50-INDEX', 'NSE:NIFTY2590924900CE', 'NSE:NIFTY2590925000PE',
        #           'NSE:NIFTY2590925000CE']
        # Validate: must be a list, non-empty, and all elements non-empty strings
        if (
            isinstance(tickers, list)
            and len(tickers) > 0
            and all(t.strip() for t in tickers)
        ):
            symbols = tickers
        else:
            # Default fallback
            symbols = ["BSE:SENSEX-INDEX", "NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX"]
        fyers.subscribe(symbols=symbols, data_type=data_type)

    # Replace the sample access token with your actual access token obtained from Fyers
    access_token = access_token_input

    # Create a FyersDataSocket instance with the provided parameters
    fyers = data_ws.FyersDataSocket(
        access_token=access_token,  # Access token in the format "appid:accesstoken"
        log_path="",  # Path to save logs. Leave empty to auto-create logs in the current directory.
        litemode=True,  # Lite mode disabled. Set to True if you want a lite response.
        write_to_file=False,  # Save response in a log file instead of printing it.
        reconnect=True,  # Enable auto-reconnection to WebSocket on disconnection.
        on_connect=onopen,  # Callback function to subscribe to data upon connection.
        on_close=onclose,  # Callback function to handle WebSocket connection close events.
        on_error=onerror,  # Callback function to handle WebSocket errors.
        on_message=onmessage,  # Callback function to handle incoming messages from the WebSocket.
    )

    # Keep the socket running to receive real-time data
    fyers.keep_running()

    # Establish a connection to the Fyers WebSocket
    fyers.connect()

    # yield message_queue.get()


# 5. WebSocket Connection Function
# Consumer function
def consumer_old():
    def event_stream():
        while True:
            msg = message_queue.get()
            if msg is None:
                break
            yield msg

    """
    def event_stream():
        while True:
            yield f"data: hello at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            time.sleep(1)
    """
    return Response(event_stream(), mimetype="text/event-stream")


def run_flask():
    port = int(3000)  # Render sets PORT env variable
    if not port:
        port = 8080
    # cert_file = os.path.join(os.path.dirname(__file__), "ssl.crt/server.crt")
    # key_file = os.path.join(os.path.dirname(__file__), "ssl.key/server.key")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


# new running main
def main():
    # flask_thread = Thread(target=run_flask)
    # flask_thread.start()
    flask_process = Process(target=run_flask)
    flask_process.start()

    print("✅ Flask server started.")


if __name__ == "__main__":
    main()
