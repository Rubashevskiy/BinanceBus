#DATA
from collections import OrderedDict
from collections import namedtuple
#SIGN
import hmac
import hashlib
import time
#HTTPS
import requests
from urllib.parse import urlencode
from requests.exceptions import ConnectionError
#EXCEPTION
import traceback


DEF_HEADER       = {'ContentType' : 'application/x-www-form-urlencoded',
                    'Accept'      : 'application/json',
                    'User-Agent'  : 'binance/python/api'
                   }

#             COMMAND              TYPE                    URL                              AUTH
DEF_HTTPS = {'ping'             : ['GET',    'https://api.binance.com/api/v3/ping',         False],
             'get_server_time'  : ['GET',    'https://api.binance.com/api/v3/time',         False],
             'get_symbol_data'  : ['GET',    'https://api.binance.com/api/v3/exchangeInfo', False],
             'get_symbol_price' : ['GET',    'https://api.binance.com/api/v3/ticker/price', False],
             'get_user_data'    : ['GET',    'https://api.binance.com/api/v3/account',      True],
             'get_open_orders'  : ['GET',    'https://api.binance.com/api/v3/openOrders',   True],
             'get_order_info'   : ['GET',    'https://api.binance.com/api/v3/order',        True],
             'create_order'     : ['POST',   'https://api.binance.com/api/v3/order',        True],
             'cancel_order'     : ['DELETE', 'https://api.binance.com/api/v3/order',        True]
            }

DEF_RECV_WINDOW  = 5000

TraceNode = namedtuple('TraceNode', 'file_name, code_line, func_name, text')

class BinanceBusException(Exception):
  def __init__(self, msg, trace = []):
    self.what = msg
    self.traceback = trace
    if 0 == len(self.traceback):
      stack = traceback.extract_stack()
      for i in range(len(stack) - 1):
        (file_name, code_line, func_name, text) = stack[i]
        self.traceback.append(TraceNode(file_name, code_line, func_name, text))

class BinanceBus(object):
  def __init__(self, api_secret, api_key):
    self.API_SECRET = api_secret
    self.API_KEY = api_key

  def ping(self):
    self.binance_response('ping')
    return True

  def getServerTime(self):
    return self.binance_response('get_server_time')

  def getSymbolData(self):
    return self.binance_response('get_symbol_data')
  
  def getSymbolPrice(self, symbol):
    data = OrderedDict({'symbol' : symbol})
    return self.binance_response('get_symbol_price', data)

  def getUserData(self):
    return self.binance_response('get_user_data')

  def getOpenOrders(self, symbol):
    data = OrderedDict({'symbol' : symbol})
    return self.binance_response('get_open_orders', data)
  
  def getOrderInfo(self, symbol, order_id):
    data = OrderedDict({'symbol' : symbol, 'orderId' : order_id})
    return self.binance_response('get_order_info', data)

  def createOrder(self, symbol, side, quantity, price):
    data = OrderedDict({'symbol' : symbol,
                        'side' : side,
                        'type' : 'LIMIT',
                        'timeInForce' : 'GTC',
                        'quantity' : quantity,
                        'price' : price,
                        'newOrderRespType' : 'RESULT'
                       })
    return self.binance_response('create_order', data)

  def cancelOrder(self, symbol, orderId):
    data = OrderedDict({'symbol' : symbol,
                        'orderId' : orderId
                       })
    return self.binance_response('cancel_order', data)

  def binance_response(self, response_name, resp_data = None):
    resp_type   = DEF_HTTPS[response_name][0]
    resp_url    = DEF_HTTPS[response_name][1]
    resp_header = DEF_HEADER
    if resp_data is None: resp_data = OrderedDict()
    if DEF_HTTPS[response_name][2]:
      resp_header['X-MBX-APIKEY'] = self.API_KEY
      resp_data['timestamp'] = self.timestampNow()
      resp_data['recvWindow'] = DEF_RECV_WINDOW
      resp_data['signature'] = self.getURLDataHash(resp_data, self.API_SECRET)
    result = self.https_response(resp_type, resp_url, resp_header, resp_data)
    return result

  def https_response(self, resp_type, resp_url, resp_header, resp_data):
    try:
      if 'GET' == resp_type: 
        response_data = requests.get(url = resp_url, headers = resp_header, params = resp_data)
      elif 'POST' == resp_type:
        response_data = requests.post(url = resp_url, headers = resp_header,  params = resp_data)
      elif 'DELETE' == resp_type:
        response_data = requests.delete(url = resp_url, headers = resp_header,  params = resp_data)

      if response_data.ok:
        return response_data.json()
      else:
        js_error = response_data.json()
        if ('code' in js_error) and ('msg' in js_error):
          raise BinanceBusException('ERROR: <Binance API>: Code %s MSG %s' % (js_error['code'], js_error['msg']))
        else:
          raise BinanceBusException('ERROR: <HTTPS_P >: Code %s' % (response_data.status_code))
    except ConnectionError:
      raise BinanceBusException('ERROR: <HTTP_T>: MSG %s' % ('Connection error'))

  def timestampNow(self):
    return int(time.time() * 1000)

  def getURLDataHash(self, data, key):
    data_encode = urlencode(data)
    m = hmac.new(key.encode('utf-8'), data_encode.encode('utf-8'), hashlib.sha256)
    return m.hexdigest()