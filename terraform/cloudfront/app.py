def lambda_handler(event, context):
    event = event['Records'][0]['cf']
    request = event['request']
    uri = request['uri']
    if uri.endswith('.gz') or uri.endswith('.zip'):
        pass
    else:
        accept_encoding = request['headers'].get('accept-encoding', [])
        if any('gzip' == entry['value'] for entry in accept_encoding):
            request['uri'] += '.gz'
    return request
