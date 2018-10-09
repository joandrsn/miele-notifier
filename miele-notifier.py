#!/usb/bin/env python3

import requests
import json
import sys
import signal
from datetime import datetime
from texttable import Texttable
from pprint import pprint
from time import sleep
from pushover import Client

watchids = []
config = {}

def sigint_handle(sig, frame):
  exit_with_msg('SIGINT received. Exiting..')

def printtime(msg):
  message = '[{}] {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg)
  print(message)

def list_machines():
  machines = get_machines()
  table = Texttable()
  for m in machines:
    table.add_row([m['id'], m['type'], m['in_use'], m['status'], m['unitName']])
  table.header(['ID', 'Type', 'In Use', 'Status', 'Unit Name'])
  table.set_deco(Texttable.BORDER | Texttable.HEADER)
  print(table.draw())

def readconfig():
  global config
  with open('config.json', 'r') as f:
    config = json.load(f)

def sendNotification(message, title = 'Miele Notifier'):
  global config

  client = Client(config['pushover']['user'], api_token = config['pushover']['key'])
  client.send_message(message, title=title)

def get_raw_machines():
  global config

  r = requests.get(config['miele']['url'], headers = {'Authorization': config['miele']['auth']})

  if r.status_code != 200:
    exit_with_msg("Wrong status", 1)

  return json.loads(r.text)

def get_machines():
  originalmachineobject = get_raw_machines()
  result = []
  for m in originalmachineobject['MachineStates']:
    machine = {}
    machine['type'] = 'Dryer' if m['machineSymbol'] else 'Washer'
    machine['in_use'] = not m['machineColor']
    machine['status'] = m['text1']
    machine['unitName'] = m['unitName']
    machine['id'] = m['unitName'].replace("Machine ", "")
    result.append(machine)
  return result

def watch():
  global watchids
  machines = get_machines()
  for m in machines:
    if m['id'] in watchids:
      if not m['in_use'] :
        msg = '{} {} is now finished!'.format(m['type'], m['id'])
        watchids.remove(m['id'])
        printtime(msg)
        sendNotification(msg)
      else:
        printtime('{} {} is still working. {}'.format(m['type'], m['id'], m['status']))

def mainloop():
  while True:
    watch()
    checkdone()
    sleep(60)

def checkdone():
  global watchids
  if len(watchids) != 0:
    return
  msg = 'All Done'
  sendNotification(msg)
  exit_with_msg(msg)

def exit_with_msg(msg, code = 0):
  if not msg is None:
    if code == 0:
      printtime(msg)
    else:
      print(msg)
  sys.exit(code)

def handle_args():
  if len(sys.argv) != 2:
    exit_with_msg('Usage: ./miele-notifier.py <action>\n\t<action> can be: list or ids of machine\nExample:\n\t./miele-notifier.pt list\n\t./miele-notifier.py 1,2,3', 2)
  elif sys.argv[1] == 'list':
    exit_with_msg(list_machines(), 0)
  else:
    global watchids
    watchids = sys.argv[1].split(',')

def main():
  readconfig()
  handle_args()
  signal.signal(signal.SIGINT, sigint_handle)
  list_machines()
  mainloop()

if __name__ == '__main__':
  main()