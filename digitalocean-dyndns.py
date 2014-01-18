#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Digital Ocean DynDNS

Dynamic DNS updater for Digital Ocean

Copyright (c) 2014 Frédéric Massart - FMCorz.net

Licensed under The MIT License
Redistributions of files must retain the above copyright notice.

http://github.com/FMCorz/digitalocean-dyndns
"""

import sys
import requests
import argparse
import logging

CLIENTID = 'XXXXXXXXXX'
APIKEY = 'YYYYYYYYYY'
API = 'https://api.digitalocean.com'

# Error codes
DOMAIN_NOT_FOUND = 1
RECORD_NOT_FOUND = 2
REQUEST_ERROR = 4


def getIp():
    """Return the external IPv4"""
    r = requests.get('http://api.externalip.net/ip')
    return r.text


def request(uri, params={}):
    """Perform a request on Digital Ocean API"""
    url = API + '/' + uri.strip('/')
    auth = {
        'client_id': CLIENTID,
        'api_key': APIKEY
    }

    if sys.version_info.major == 3:
        params = dict(list(auth.items()) + list(params.items()))
    else:
        params = dict(auth.items() + params.items())

    logging.debug('Requesting: %s' % (url))
    r = requests.get(url, params=params)
    jason = r.json()
    if jason.get('status', '') != 'OK':
        logging.error(u'Host replied with a non-OK status. Message: %s' % jason.get('error_message'))
        sys.exit(REQUEST_ERROR)
    return jason


# Define arguments
parser = argparse.ArgumentParser(description='Dynamic DNS updater for Digital Ocean')
parser.add_argument('--domain', '-d', help='Domain name', required=True)
parser.add_argument('--record', '-r', help='Record for domain', required=True)
parser.add_argument('--allownew', '-c', help='Allow creation of a new record', action='store_true')
parser.add_argument('--verbose', '-v', help='Increase verbosity', action='count', default=0)
args = parser.parse_args()

# Verbosity level
if args.verbose >= 2:
    debug = logging.DEBUG
elif args.verbose == 1:
    debug = logging.INFO
else:
    debug = logging.WARNING
logging.basicConfig(format='%(message)s', level=debug)

# Finding the domain ID
domainId = None
domains = request('/domains')
for domain in domains.get('domains'):
    if domain.get('name') == args.domain:
        domainId = domain.get('id')
        logging.info('Found domain %s, ID: %s' % (args.domain, domainId))
        break

if not domainId:
    logging.warning('Could not find domain %s' % (args.domain))
    sys.exit(DOMAIN_NOT_FOUND)

# Looking up the records
recordId = None
records = request('/domains/{0}/records'.format(domainId))
for record in records.get('records'):
    if record.get('record_type') == 'A' and record.get('name') == args.record:
        recordId = record.get('id')
        logging.info('Found record %s, ID: %s' % (args.record, recordId))
        break

# Create the record if it does not exist
if not recordId:
    if not args.allownew:
        logging.warning('Could not find the A record %s for domain %s' % (args.record, args.domain))
        sys.exit(RECORD_NOT_FOUND)

    ip = getIp()
    params = {
        'domain_id': domainId,
        'record_type': 'A',
        'name': args.record,
        'data': ip
    }
    result = request('/domains/{0}/records/new'.format(domainId), params=params)
    logging.info('Record created with ID %s using IP %s' % (result.get('record', {}).get('id', '<?>'), ip))

# Update the existing record
else:
    ip = getIp()
    if record.get('data') == ip:
        logging.info('No update required')

    else:
        params = {
            'record_id': recordId,
            'record_type': 'A',
            'data': ip
        }
        result = request('/domains/{0}/records/{1}'.format(domainId, recordId), params=params)
        logging.info('Updated record with IP %s' % (ip))