import requests

from kraken_wsclient_py import kraken_wsclient_py as client
from flask import Flask, render_template, request
from flask_socketio import SocketIO
from binance import ThreadedWebsocketManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

symbol = None
platform = None
kraken_ticker = {}


def binance_price_calculate(ticker):
    if type(ticker) == list:
        pairs = {}

        for pair in ticker:
            pairs[pair['s']] = (float(pair['b'])+float(pair['a']))/2

        return pairs
    elif type(ticker) == dict:
        return {ticker['s']: (float(ticker['b'])+float(ticker['a']))/2}
    return None


def kraken_price_calculate(ticker):
    return {'symbol': ticker.pop().replace('/', ''), 'price': (float(ticker[1]['b'][0])+float(ticker[1]['a'][0]))/2}


def kraken_get_pairs():
    resp = requests.get('https://api.kraken.com/0/public/AssetPairs')
    pairs = resp.json()['result']

    return [pairs[pair]['wsname'] for pair in pairs.keys()]


def binance_handler(param):
    twm = ThreadedWebsocketManager()

    twm.start()

    def handle_socket_message(msg):
        socketio.emit('binance', binance_price_calculate(msg), to=param['user_id'])

    if not param.get('symbol'):
        twm.start_ticker_socket(callback=handle_socket_message)
    else:
        twm.start_symbol_ticker_socket(callback=handle_socket_message, symbol=param['symbol'].replace('_', ''))


def kraken_handler(param):
    my_client = client.WssClient()
    my_client.start()

    asset_pairs = kraken_get_pairs()

    def handle_socket_message(msg):
        global kraken_ticker

        if type(msg) == list:
            if len(kraken_ticker) == len(asset_pairs):
                socketio.emit('kraken', kraken_ticker, to=param['user_id'])

            price_calculate = kraken_price_calculate(msg)

            kraken_ticker[price_calculate['symbol']] = price_calculate['price']

    def handle_pair_socket_message(msg):
        if type(msg) == list:
            kraken_data = kraken_price_calculate(msg)
            socketio.emit('kraken', {kraken_data['symbol']: kraken_data['price']}, to=param['user_id'])


    if not param.get('symbol'):
        my_client.subscribe_public(
            subscription={
                'name': 'ticker'
            },
            pair=kraken_get_pairs(),
            callback=handle_socket_message
        )
    else:
        my_client.subscribe_public(
            subscription={
                'name': 'ticker'
            },
            pair=[param['symbol'].replace('_', '/')],
            callback=handle_pair_socket_message
        )


@app.route('/')
def home():
    global symbol
    global platform

    platform = request.args.get('platform')
    symbol = request.args.get('symbol')
    return render_template('index.html', data=[])


@socketio.on('connect')
def connect():
    if platform == 'kraken':
        socketio.start_background_task(
            kraken_handler,
            {
                'user_id': request.sid,
                'symbol': symbol,
                'platform': platform,
            }
        )
    elif platform == 'binance':
        socketio.start_background_task(
            binance_handler,
            {
                'user_id': request.sid,
                'symbol': symbol,
                'platform': platform,
            }
        )
    else:
        socketio.start_background_task(
            kraken_handler,
            {
                'user_id': request.sid,
                'symbol': symbol,
                'platform': platform,
            }
        )
        socketio.start_background_task(
            binance_handler,
            {
                'user_id': request.sid,
                'symbol': symbol,
                'platform': platform,
            }
        )



if __name__ == '__main__':
    socketio.run(app)