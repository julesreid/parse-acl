#!/usr/bin/env python
#
# Script to find address ranges within a Cisco ACL
#
# The idea is to find all ACLs which apply to a certain host or
# network range.
#
# To do:
#
# * Implement ASA ACLs using the following keywords:
#     object network
#     object service
#     object-group network
#     object-group protocol
#     object-group service
#     access-list

import sys
import re
import socket
import struct
import getopt

### IP address, subnet and prefix list matching

IP_OCTET = r'\b(?:[0-9]|[1-9][0-9]|1[0-9][0-9]|2[0-4][0-9]|25[0-5])\b'
IP_ADDR = IP_OCTET + r'\.' + IP_OCTET + r'\.' + IP_OCTET + r'\.' + IP_OCTET

SUBNET_RE = r'''
    (''' + IP_ADDR + r''')
    (?:
        \/(\d+)
    )?
'''

PREFIX_RE = r'''
    ^
    ''' + SUBNET_RE + r'''
    (?: \s+ ge \s+ (\d+) )?
    (?: \s+ le \s+ (\d+) )?
    $
'''

### ACL matching

# Match the header of a standard or extended ACL
ACL_HEADER = r'^ip\ access-list\ (?:standard|extended)\ (\S+)'

## Standard numbered

# access-list 23 permit 10.1.3.15
# access-list 23 permit 10.2.19.224 0.0.0.31
# access-list 23 permit 10.2.127.0 0.0.0.255
# access-list 23 permit 10.10.0.0 0.0.255.255

## Standard named

# ip access-list standard mgmt-access
#  permit 10.1.3.15
#  permit 10.2.19.224 0.0.0.31
#  permit 10.2.127.0 0.0.0.255
#  permit 10.2.3.0 0.0.0.255
#  permit 10.10.21.0 0.0.0.255

STANDARD_ACL_RE = r'''
    (?:
        access-list
        \s+\d+
    )?
    \s+
    (permit|deny)
    \s+(any|(''' + IP_ADDR + r')(?:\s+(' + IP_ADDR + r'''))?)
'''

## Extended numbered

# access-list 100 remark From HL
# access-list 100 permit ip 10.5.40.64 0.0.0.31 any time-range hlc-rate-limiting
# access-list 101 remark To HL
# access-list 101 permit ip any 10.5.40.64 0.0.0.31 time-range hlc-rate-limiting
#
# access-list 100 permit udp host 10.15.2.8 any eq echo log

## Extended named

# ip access-list extended network-services-in
#  permit udp host 0.0.0.0 eq bootpc host 255.255.255.255 eq bootps log
#  deny   udp any eq bootpc any eq bootps log
#  permit ip any any

EXTENDED_ACL_RE = r'''
    (?:
        access-list
        \s+\d+
    )?
    \s+
    (permit|deny)
    \s+
    (\d+|ip|icmp|tcp|udp|ahp|eigrp|esp|gre|igmp|ipinip|nos|ospf|pcp|pim)
    \s+
    (any|host\s+(''' + IP_ADDR + r')|(' + IP_ADDR + r')\s+(' + IP_ADDR + r'''))
    (?:
        \s+ eq \s+ (\S+)
    |
        \s+ range \s+ \S+ \s+ \S+
    )?
    \s+
    (any|host\s+(''' + IP_ADDR + r')|(' + IP_ADDR + r')\s+(' + IP_ADDR + r'''))
    (?:\s+eq\s+(\S+))?
'''

EXTENDED_IGNORE_RE = r'(?:access-list\ \d+)?\ (?:dynamic|evaluate|remark)\ .*'

### IP address utility functions

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
    assert isinstance(subnet[0], int) or isinstance(subnet[0], long)
    assert isinstance(subnet[1], int)
    return inttoip(subnet[0]) + '/' + str(subnet[1])

def maskof(p):
    return -1 << (32 - p)

def wildtonetmask(wild):
    n = iptoint(wild)
    n = (~n) & 0xffffffff
    return n

def netmasktoprefix(mask):
    prefix = 32

    # Change netmask to a wildcard so that all of the 1s are on the right.
    # Can't use wildtonetmask here since mask is not a string.
    mask = (~mask) & 0xffffffff
    while mask > 0:
        mask >>= 1
        prefix -= 1
    return prefix

### IP subnet matching

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
    """Test if network (a.addr,a.mask) CONTAINS (b.addr,b.mask)

    Caveat: Don't assume that a or b is normalised."""
    return match_subnet(subnet1, subnet2, 0, subnet2[1])

def is_contained_in(subnet1, subnet2):
    """Test if network SUBNET1 IS CONTAINED IN SUBNET2"""
    return match_subnet(subnet1, subnet2, subnet2[1], 32)

def matches_exact(subnet1, subnet2):
    return match_subnet(subnet1, subnet2, subnet2[1], subnet2[1])

### Parsing

# XXX redefine to make more sense (e.g., "host" only is used in extended
# acls but not in standard acls)
def range_to_net(re_range, re_host, re_net, re_mask):
    if re_range.startswith('host '):
        net = iptoint(re_host)
        mask = 32
    elif re_range == "any":
        net, mask = iptosubnet("0.0.0.0/0")
    else:
        net = iptoint(re_net)
        mask = netmasktoprefix(wildtonetmask(re_mask))
    return (net, mask)

# GE: undefined LE: undefined   ge=LEN, le=LEN
# GE: undefined LE: defined     ge=LEN, le=LE
# GE: defined   LE: defined     ge=GE,  le=LE
# GE: defined   LE: undefined   ge=GE,  le=32
def normalize_prefix_lengths(ip, len, ge, le):
    if len is None:
        len = 32
    if le is None:
        if ge is None:
            ge = le = len
        else:
            le = 32
    elif ge is None:
        ge = len
    return ((ip, len), ge, le)

def safe_int(x):
    if x is None:
        return None
    return int(x)

def parse_prefix_list(arg):
    r = re.match(PREFIX_RE, arg, re.X)
    if not r:
        raise SyntaxError
    ip =  iptoint(r.group(1))
    length = safe_int(r.group(2))
    ge =  safe_int(r.group(3))
    le =  safe_int(r.group(4))
    return normalize_prefix_lengths(ip, length, ge, le)

def normalized(subnet):
    """Return True if host portion of the IP address is all zeroes."""
    assert isinstance(subnet, tuple)
    assert len(subnet) == 2
    ip = subnet[0]
    length = subnet[1]
    return ip & maskof(length) == ip

### Main program

def main():
    # Match anything by default
    src_match =   dst_match  = iptosubnet("0.0.0.0/0")
    src_min   =   dst_min    = 0
    src_max   =   dst_max    = 32
    reverse = False

    try:
        opts, parseargs = getopt.getopt(sys.argv[1:], 's:d:x')
    except getopt.GetoptError, err:
        print "%s: %s" % (sys.argv[0], err)
        sys.exit(1)
    #print "DEBUG:", opts, parseargs
    for opt, arg in opts:
        if opt == '-s':
            # Handle source address
            src_match, src_min, src_max = parse_prefix_list(arg)
            if not normalized(src_match):
                print "warning: src ip not normalized (%s)" % subnettoip(src_match)
        elif opt == '-d':
            # Handle destination address
            dst_match, dst_min, dst_max = parse_prefix_list(arg)
            if not normalized(dst_match):
                print "warning: dst ip not normalized (%s)" % subnettoip(dst_match)
        elif opt == '-x':
            reverse = True

    # Assert that 0 <= ge <= le <= 32
    # XXX convert asserts to raise SyntaxError
    assert 0 <= src_min, "Must have src  0 <= ge"
    assert src_min <= src_max, "Must have src ge <= le"
    assert src_max <= 32, "Must have src le <= 32"
    assert 0 <= dst_min, "Must have dst  0 <= ge"
    assert dst_min <= dst_max, "Must have dst ge <= le"
    assert dst_max <= 32, "Must have dst le <= 32"

    if reverse:
        src_match, src_min, src_max, dst_match, dst_min, dst_max = \
            dst_match, dst_min, dst_max, src_match, src_min, src_max

    #print "DEBUG: src: %s ge %d le %d" % (subnettoip(src_match), src_min, src_max)
    #print "DEBUG: dst: %s ge %d le %d" % (subnettoip(dst_match), dst_min, dst_max)

    last_acl_name = None
    current_acl_name = None
    current_acl_line = None
    line_num = 0
    for line in sys.stdin:
        line = line.replace('\n', '')
        line_num += 1
        if re.match(ACL_HEADER, line, re.X):
            #print "DEBUG: ACL_HEADER", line
            current_acl_name = line
            current_acl_line = line_num
            continue
        if re.match(EXTENDED_IGNORE_RE, line, re.X):
            #print "DEBUG: EXTENDED_IGNORE_RE", line
            continue
        r = re.match(EXTENDED_ACL_RE, line, re.X)
        if r:
            # XXX needs to work when both -s and -d specified (logical or)
            # XXX needs error checking
            # XXX $7 and $12 are source or destination ports (if any)
            #print "DEBUG: EXTENDED_ACL_RE", line
            src = range_to_net(r.group(3), r.group(4), r.group(5), r.group(6))
            #print "DEBUG: foo", subnettoip(src)
            dst_range = r.group(8)
            if dst_range is None:
                dst_range = "any"
            dst = range_to_net(dst_range, r.group(9), r.group(10), r.group(11))
            #print "DEBUG: bar", subnettoip(dst)
        else:
            r = re.match(STANDARD_ACL_RE, line, re.X)
            if r:
                #print "DEBUG: STANDARD_ACL_RE", line
                # XXX ugly code
                if r.group(4) is None:
                    src = range_to_net(r.group(2), None, r.group(3), "0.0.0.0")
                    #print "DEBUG: biz", subnettoip(src)
                else:
                    src = range_to_net(r.group(2), None, r.group(3), r.group(4))
                    #print "DEBUG: baz", subnettoip(src)
                dst = iptosubnet("0.0.0.0/0")
                #print "DEBUG: qux", subnettoip(dst)
            else:
                #print "DEBUG: NO MATCH", line
                last_acl_name = None
                current_acl_name = None
                current_acl_line = None
                continue

        if match_subnet(src, src_match, src_min, src_max) and \
           match_subnet(dst, dst_match, dst_min, dst_max):
            if current_acl_name and (last_acl_name is None or last_acl_name != current_acl_name):
                # XXX current_acl_name and current_acl_line may be
                # undefined
                print "%5d %s" % (current_acl_line, current_acl_name)
                last_acl_name = current_acl_name
            print "%5d %s" % (line_num, line)

if __name__ == '__main__':
    main()

# vim: filetype=python et ts=4 wm=0:
