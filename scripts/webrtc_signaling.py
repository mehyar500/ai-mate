"""Constraints for the single-PC transport benchmark, not public RTC signaling."""
import ipaddress


def validate_offer(payload, local_addresses):
    if not isinstance(payload, dict) or set(payload) != {'type', 'sdp'} or payload['type'] != 'offer':
        raise ValueError('Expected one SDP offer.')
    sdp = payload['sdp']
    if not isinstance(sdp, str) or not 1 <= len(sdp.encode('utf-8')) <= 30_000:
        raise ValueError('Invalid SDP length.')
    allowed = {str(ipaddress.ip_address(address)) for address in local_addresses}
    sections = sdp.replace('\r\n', '\n').split('\nm=')
    if len(sections) != 3 or {part.split(maxsplit=1)[0] if part.strip() else '' for part in sections[1:]} != {'audio', 'video'}:
        raise ValueError('The benchmark accepts exactly one audio and one video receiver.')
    for section in sections[1:]:
        directions = {line for line in section.splitlines() if line in {'a=recvonly', 'a=sendonly', 'a=sendrecv', 'a=inactive'}}
        if directions != {'a=recvonly'}:
            raise ValueError('The benchmark never accepts captured client media.')
    candidates = 0
    for line in sdp.splitlines():
        if line.startswith('a=candidate:'):
            fields = line.split()
            if len(fields) < 8 or fields[6:8] != ['typ', 'host']:
                raise ValueError('Use host candidates only; no relays or external STUN.')
            address = str(ipaddress.ip_address(fields[4]))
            if address not in allowed or fields[2].lower() not in {'udp', 'tcp'}:
                raise ValueError('ICE candidates must belong to this PC.')
            if not 1 <= int(fields[5]) <= 65535:
                raise ValueError('Invalid candidate port.')
            candidates += 1
    if not 1 <= candidates <= 32:
        raise ValueError('Invalid candidate count.')
    return payload
