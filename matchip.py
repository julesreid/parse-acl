import socket
import struct

def maskof(prefixlen):
    assert isinstance(prefixlen, int), type(prefixlen)
    r = int(-1 << (32 - prefixlen))
    assert isinstance(r, int), type(r)
    return r

def iptoint(ip):
    assert isinstance(ip, str), type(ip)
    # int() wrapper needed since defined return type of I (unsigned int) is long
    # in Python 2.4 (but not later apparently)
    r = int(struct.unpack("!I", socket.inet_aton(ip))[0])
    assert isinstance(r, int), type(r)
    return r

def inttoip(int_):
    assert isinstance(int_, int), type(int_)
    r = socket.inet_ntoa(struct.pack("!I", int_))
    assert isinstance(r, str), type(r)
    return r

def iptosubnet(ip):
    assert isinstance(ip, str), type(ip)
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
    assert len(subnet) == 2, len(subnet)
    assert isinstance(subnet[0], int), type(subnet[0])
    assert isinstance(subnet[1], int), type(subnet[1])
    r = inttoip(subnet[0]) + '/' + str(subnet[1])
    assert isinstance(r, str), type(r)
    return r

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

def containment(subnet1, subnet2):
    return match_subnet(subnet1, subnet2, 0, 32)

def contains(subnet1, subnet2):
    return match_subnet(subnet1, subnet2, 0, subnet2[1])

def is_contained_in(subnet1, subnet2):
    return match_subnet(subnet1, subnet2, subnet2[1], 32)

def matches_exact(subnet1, subnet2):
    return match_subnet(subnet1, subnet2, subnet2[1], subnet2[1])

if __name__ == '__main__':
    import sys
    assert len(sys.argv) == 5
    ipaddr1 = iptosubnet(sys.argv[1])
    ipaddr2 = iptosubnet(sys.argv[2])
    minlen = int(sys.argv[3])
    maxlen = int(sys.argv[4])

    print "ipaddr1 =", subnettoip(ipaddr1)
    print "ipaddr2 =", subnettoip(ipaddr2)
    results = (("match_subnet", match_subnet(ipaddr1, ipaddr2, minlen, maxlen)),
               ("containment", containment(ipaddr1, ipaddr2)),
               ("contains", contains(ipaddr1, ipaddr2)),
               ("is_contained_in", is_contained_in(ipaddr1, ipaddr2)),
               ("matches_exact", matches_exact(ipaddr1, ipaddr2)))
    for name, result in results:
        print "%-22s  %s" % (name, result)
