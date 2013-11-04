import socket
import struct

def maskof(prefixlen):
    allones = (1 << 32) - 1
    return int((allones << (32 - prefixlen)) & allones)

def iptoint(ip):
    return struct.unpack("!I", socket.inet_aton(ip))[0]

def inttoip(int_):
    return socket.inet_ntoa(struct.pack("!I", int_))

def iptosubnet(ip):
    assert isinstance(ip, str)
    try:
        i = ip.index('/')
        mask = int(ip[i + 1:])
        ip = ip[:i]
    except ValueError:
        mask = 32
    ipaddr_bin = iptoint(ip)
    return (ipaddr_bin, mask)

def subnettoip(subnet):
    assert isinstance(subnet, tuple) or isinstance(subnet, list)
    assert len(subnet) == 2
    assert isinstance(subnet[0], int)
    assert isinstance(subnet[1], int)
    return inttoip(subnet[0]) + '/' + str(subnet[1])

def match_subnet(subnet1, subnet2, minlen, maxlen):
    """Given two subnets, SUBNET1 and SUBNET2, test whether SUBNET1 is
    either a superset or subset of SUBNET2 that falls within the prefix
    length range between MINLEN and MAXLEN."""
    def subnet_test(addr1, addr2, prefixlen):
        """Test two IPv4 addresses, ADDR1 and ADDR2, for equality when
        normalized to a common prefix length PREFIXLEN."""
        mask = maskof(prefixlen)
        return (addr1 & mask) == (addr2 & mask)

    len1 = subnet1[1]
    len2 = subnet2[1]
    containment = subnet_test(subnet1[0], subnet2[0], min(len1, len2))
    return containment and minlen <= len1 <= maxlen

def contains(subnet1, subnet2):
    return match_subnet(subnet1, subnet2, 0, subnet2[1])

def is_contained_in(subnet1, subnet2):
    return match_subnet(subnet1, subnet2, subnet2[1], 32)

def matches_exact(subnet1, subnet2):
    return match_subnet(subnet1, subnet2, subnet2[1], subnet2[1])

if __name__ == '__main__':
    import sys
    assert len(sys.argv) == 5
    ipaddr1 = sys.argv[1]
    ipaddr2 = sys.argv[2]
    minlen = int(sys.argv[3])
    maxlen = int(sys.argv[4])
    print match_subnet(iptosubnet(ipaddr1), iptosubnet(ipaddr2), minlen, maxlen)
    print contains(iptosubnet(ipaddr1), iptosubnet(ipaddr2))
    print is_contained_in(iptosubnet(ipaddr1), iptosubnet(ipaddr2))
    print matches_exact(iptosubnet(ipaddr1), iptosubnet(ipaddr2))
