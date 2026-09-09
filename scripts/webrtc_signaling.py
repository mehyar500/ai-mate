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


async def resolve_local_offer(payload, local_addresses, resolve):
    """Resolve only bounded mDNS host candidates, then pin validated local IPs."""
    import asyncio
    import re
    # Preflight the entire offer before any network lookup.
    if not isinstance(payload, dict) or not isinstance(payload.get('sdp'), str):
        return validate_offer(payload, local_addresses)
    names = set()
    probe = []
    for line in payload['sdp'].splitlines():
        if line.startswith('a=candidate:'):
            fields = line.split()
            if len(fields) >= 8 and re.fullmatch(r'[a-zA-Z0-9-]{1,63}\.local', fields[4]):
                names.add(fields[4])
                fields[4] = '127.0.0.1'
                line = ' '.join(fields)
        probe.append(line)
    validate_offer({**payload, 'sdp': '\r\n'.join(probe)+'\r\n'}, local_addresses)
    if not names:
        return payload
    async def lookup(name):
        address = await resolve(name)
        if not address:
            raise ValueError('Local ICE hostname did not resolve.')
        return name, str(ipaddress.ip_address(address))
    resolved = dict(await asyncio.wait_for(asyncio.gather(*(lookup(name) for name in names)), 3))
    lines = []
    for line in payload['sdp'].splitlines():
        if line.startswith('a=candidate:'):
            fields = line.split()
            if fields[4] in resolved:
                fields[4] = resolved[fields[4]]
                line = ' '.join(fields)
        lines.append(line)
    # Never pass the hostname to ICE again: resolution cannot change after validation.
    return validate_offer({**payload, 'sdp': '\r\n'.join(lines)+'\r\n'}, local_addresses)
