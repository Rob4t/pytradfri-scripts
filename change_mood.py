#!/usr/bin/env python3
"""
You can set moods via this script.

Example usage via cron:

    # sets a "cold" mood for group "bathroom". determines group state via bulb "light"
    # when state is "True" the mood "FOCUS" will be set. when state is "False"
    # the mood "FOCUS OFF" is set (which does not turn on the light)
    0 6 * * 1-5 /root/change_mood.py 192.168.178.45 bathroom light FOCUS "FOCUS OFF"

"""

# Hack to allow relative import above top level package
import sys
import os
folder = os.path.dirname(os.path.abspath(__file__))  # noqa
sys.path.insert(0, os.path.normpath("%s/.." % folder))  # noqa

from pytradfri import Gateway
from pytradfri.api.libcoap_api import APIFactory
from pytradfri.error import PytradfriError
from pytradfri.util import load_json, save_json
import json
import uuid
import argparse

CONFIG_FILE = 'tradfri_standalone_psk.conf'


parser = argparse.ArgumentParser()
parser.add_argument('host', metavar='IP', type=str,
                    help='IP Address of your Tradfri gateway')
parser.add_argument('group', type=str,
                    help='Name of the Tadfri group')
# unfortunately a groups state is always "True"... as a workaround we determine a groups
# state by this passed member
parser.add_argument('object_determining_state', type=str,
                    help='This member of group determines group state')
parser.add_argument('mood_on', type=str,
                    help='Mood to set if group is on')
parser.add_argument('mood_off', type=str,
                    help='Mood to set if group is off')
parser.add_argument('-K', '--key', dest='key', required=False,
                    help='Security code found on your Tradfri gateway')
args = parser.parse_args()


if args.host not in load_json(CONFIG_FILE) and args.key is None:
    print("Please provide the 'Security Code' on the back of your "
          "Tradfri gateway:", end=" ")
    key = input().strip()
    if len(key) != 16:
        raise PytradfriError("Invalid 'Security Code' provided.")
    else:
        args.key = key


conf = load_json(CONFIG_FILE)

try:
    identity = conf[args.host].get('identity')
    psk = conf[args.host].get('key')
    api_factory = APIFactory(host=args.host, psk_id=identity, psk=psk)
except KeyError:
    identity = uuid.uuid4().hex
    api_factory = APIFactory(host=args.host, psk_id=identity)

    try:
        psk = api_factory.generate_psk(args.key)
        print('Generated PSK: ', psk)

        conf[args.host] = {'identity': identity,
                           'key': psk}
        save_json(CONFIG_FILE, conf)
    except AttributeError:
        raise PytradfriError("Please provide the 'Security Code' on the "
                             "back of your Tradfri gateway using the "
                             "-K flag.")

api = api_factory.request

gateway = Gateway()

available_groups = api(gateway.get_groups())

target_group = None

# search for our group via name
for group in available_groups:
    data = api(group)
    if data.name == args.group:
        target_group = data
        break

state_object = None

# search group member to check state for
for member in target_group.members():
    data = api(member)
    if data.name == args.object_determining_state:
        state_object = data
        break

# get object state
bulb_state = state_object.light_control.lights[0].state

target_mood = None

target_mood_name = None
if bulb_state:
    target_mood_name = args.mood_on
else:
    target_mood_name = args.mood_off

available_moods = api(target_group.moods())

for mood in available_moods:
    data = api(mood)
    if data.name == target_mood_name:
        target_mood = data
        break

api(target_group.activate_mood(target_mood.id))
