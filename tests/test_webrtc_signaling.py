import unittest

from scripts.webrtc_signaling import validate_offer


def offer(address='127.0.0.1', direction='recvonly'):
    candidate=f'a=candidate:1 1 udp 100 {address} 50000 typ host\r\n'
    return {'type':'offer','sdp':'v=0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\na='+direction+'\r\n'+candidate+
            'm=audio 9 UDP/TLS/RTP/SAVPF 111\r\na='+direction+'\r\n'+candidate}


class LocalRTCSignalingTests(unittest.TestCase):
    def test_only_this_pc_and_receiving_media_are_accepted(self):
        for address in ['127.0.0.1','192.168.1.5','::1']:
            packet=offer(address)
            self.assertEqual(validate_offer(packet,{address}),packet)
        for address in ['8.8.8.8','192.168.1.6','example.com','random.local']:
            with self.assertRaises(ValueError):
                validate_offer(offer(address),{'127.0.0.1','192.168.1.5'})
        for direction in ['sendrecv','sendonly','inactive']:
            with self.assertRaises(ValueError):
                validate_offer(offer(direction=direction),{'127.0.0.1'})

    def test_shape_relay_capture_and_size_fail_before_creating_peer(self):
        packets=[[],{}, {'type':'answer','sdp':offer()['sdp']},offer()|{'extra':1},
                 {'type':'offer','sdp':'x'*30001}, {'type':'offer','sdp':'v=0\nm=\nm=audio'},
                 {'type':'offer','sdp':offer()['sdp'].replace('typ host','typ relay')},
                 {'type':'offer','sdp':offer()['sdp'].replace('a=recvonly','a=recvonly\r\na=sendrecv')},
                 {'type':'offer','sdp':offer()['sdp']+'m=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\n'}]
        for packet in packets:
            with self.subTest(packet=str(packet)[:50]),self.assertRaises(ValueError):
                validate_offer(packet,{'127.0.0.1'})


if __name__=='__main__':unittest.main()
