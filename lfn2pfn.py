#!/usr/bin/env python

try:
    # py3
    import urllib.request as urllib2
except ImportError:
    # py2
    import urllib2
from datetime import datetime

metacat_base = None

def lfn2pfn_DUNE(scope, name, rse, rse_attrs, protocol_attrs):
    global metacat_base

    from rucio.common import config
    from rucio.common.types import InternalScope
    from rucio.rse import rsemanager
    from metacat.webapi import MetaCatClient

    # current URL: https://metacat.fnal.gov:9443/dune_meta_demo/app
    metacat_url = config.config_get('policy', 'metacat_base_url') or os.environ.get("METACAT_SERVER_URL")
    if metacat_url is None:
        raise ValueError("MetaCat client URL is not configured")

    metacat_client = MetaCatClient(metacat_url)

    def get_metadata_field(metadata, field):
        if field in metadata:
            return metadata[field]
        return 'None'

    # check to see if PFN is already cached in Rucio's metadata system
    didclient = None
    didmd = {}
    internal_scope = InternalScope(scope)
    if getattr(rsemanager, 'CLIENT_MODE', None):
        from rucio.client.didclient import DIDClient
        didclient = DIDClient()
        didmd = didclient.get_metadata(internal_scope, name)
    if getattr(rsemanager, 'SERVER_MODE', None):
        from rucio.core.did import get_metadata
        didmd = get_metadata(internal_scope, name)

    # if it is, just return it
    md_key = 'PFN_' + rse
    if md_key in didmd:
        return didmd[md_key]

    lfn = scope + ':' + name
    jsondata = metacat_client.get_file(name=lfn)
    metadata = jsondata["metadata"]

    # determine year from timestamps
    timestamp = None
    if 'core.start_time' in metadata:
        timestamp = metadata['core.start_time']
    elif 'core.end_time' in metadata:
        timestamp = metadata['core.end_time']
    elif 'created_timestamp' in jsondata:
        timestamp = jsondata['created_timestamp']
    if timestamp is None:
        year = 'None'
    else:
        dt = datetime.utcfromtimestamp(timestamp)
        year = str(dt.year)

    # determine hashes from run number
    run_number = 0
    if 'core.runs' in metadata:
        run_number = int(metadata['core.runs'][0])
        
    hash1 = "%02d" % ((run_number // 1000000) % 100)
    hash2 = "%02d" % ((run_number // 10000) % 100)
    hash3 = "%02d" % ((run_number // 100) % 100)
    hash4 = "%02d" % (run_number % 100)

    run_type = get_metadata_field(metadata, 'core.run_type')
    data_tier = get_metadata_field(metadata, 'core.data_tier')
    file_type = get_metadata_field(metadata, 'core.file_type')
    data_stream = get_metadata_field(metadata, 'core.data_stream')
    data_campaign = get_metadata_field(metadata, 'DUNE.campaign')
    filename = name
    
    pfn = 'pnfs/dune/tape_backed/dunepro/' + run_type + '/' + data_tier + '/' + year + '/' + file_type + '/' + data_stream + '/' + data_campaign + '/' + hash1 + '/' + hash2 + '/' + hash3 + '/' + hash4 + '/' + filename

    # store the PFN in Rucio metadata for next time
    if getattr(rsemanager, 'CLIENT_MODE', None):
        didclient.set_metadata(internal_scope, name, md_key, pfn)
    if getattr(rsemanager, 'SERVER_MODE', None):
        from rucio.core.did import set_metadata
        set_metadata(internal_scope, name, md_key, pfn)

    return pfn
