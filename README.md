# parse-acl
## Find prefix ranges in ACLs from a Cisco firewall or router

This command takes the configuration of a Cisco ASA firewall or router and parses it for subnets that meet certain criteria.
The matching arguments use the same syntax as Cisco prefix lists, but
remove restrictions with the allowable lengths to make matching easier.
A subnet can be a single IP address or can be a subnet with a prefix length that represents the
subnet mask (using a slash followed by the prefix length).
An example of an IP address is ```1.2.3.4``` and an example of a subnet is ```1.2.3.0/24```.

Any text that looks like an IP address or subnet is tested to see if it matches.
If it is part of an object, the name of the object is recorded so that it can be shown.  Objects
and standard access lists
are matched by the source prefix range only, and extended access lists are shown only
if both the source and destination prefix ranges match.
If not specified, the source and destination prefix ranges default to ```0.0.0.0/0 le 32```,
which matches any subnet.  Protocols such as ```icmp``` are ignored, as are ```udp```
and ```tcp``` port numbers.  The program is only concerned with layer 3 IPv4 addresses.

Objects and object groups are expanded so that the IP subnets contained in them
are tested whenever the object name is encountered, which matches the behavior of
Cisco firewalls.

The configuration is read from the files listed on the command line, or if there are none, from
standard input.  In a shell environment, this requires using
redirection from a file using ```<```.  For instance, ```parse-acl -s 1.1.1.1 < firewall-configuration```.

Ideally, a subnet is normalized, meaning that the host portion of the subnet is all zeroes.
An example of a normalized subnet is ```1.2.0.0/16```, whereas ```1.2.3.0/16``` is not normalized because the
portion in the third octet is not zero.  A warning is given if an argument is not normalized, and the program
automatically normalizes it when matching.
This is also relevant when dealing with configurations that have an IP address and a subnet mask, such as the
```ip address``` statement:

    ip address 1.2.3.4 255.255.255.0

Because the statement has a subnet mask and is stored as ```1.2.3.4/24```,
it is treated as ```1.2.3.0/24``` when matching.  As a special case, it will also match the IP address
in the statement as a host address (that is, ```1.2.3.4/32```).

## Command-line options

### Synopsis

```parse-acl [-h] [-s SOURCE[,...]] [-d DESTINATION[,...]] [-x] [-p] [-v] [-o OBJECT | -O] [-l] [-n] [-a] [configs [configs ...]] [FILE...]```

### Optional arguments

| Option | Description |
| ------ | ----------- |
| ```-h```, ```--help``` |           show this help message and exit |
| ```-s``` *SOURCE*, ```--source``` *SOURCE* | source to match in configuration |
| ```-d``` *DESTINATION*, ```--destination``` *DESTINATION* | destination to match in configuration |
|  ```-x```, ```--swap``` |        swap the source and destinaton addresses (for convenience) |
|  ```-p```, ```--transpose``` |      add another matching sequence with the source and destination addresses swapped |
| ```-v```, ```--verbose``` |        be verbose |
| ``` -o``` *OBJECT*, ```--show-object``` *OBJECT* |                        show the IP addresses for the object |
| ```-O```, ```--show-objects``` |    show the IP addresses for all objects |
|  ```-l```, ```--resolve```     |    process ```fqdn``` statements by resolving DNS |
|  ```-n```, ```--line-number``` |    prefix each line of output with the 1-based line number within its input file |
|  ```-a```, ```--acl-lines```   |    prefix ACLs with the 1-based line number |

The source or destination can either be a prefix range or a keyword.
A prefix range consists of an IP address (with an optional prefix
length indicating a subnet), and two optional keywords that specify
the minimum and maximum prefix lengths for matches.

*IP*[```/```*LENGTH*] [```ge``` *M*] [```le``` *N*]

The prefix length must be 0 ≤ length ≤ 32, and 0 ≤ ```ge``` ≤ ```le``` ≤ 32.
Because spaces are used in the syntax, in a shell environment the argument must
be quoted.  Example: 

    parse-acl -s '1.2.3.0/24 le 32' -d '192.168.0.0/16 ge 0 le 32' FILE...

Note that unlike Cisco prefix lists, there is no dependency for
```ge``` or ```le``` on the prefix length.  For instance, this will
generate an error on a Cisco router:

    example(config)#ip prefix-list EXAMPLE permit 1.2.3.0/24 ge 1 le 32
    % Invalid prefix range for 1.2.3.0/24, make sure: len < ge-value <= le-value

By removing this restriction, supernets can be found also, which is
useful when verifying routing.

The *SOURCE* and *DESTINATION* arguments can contain multiple prefix
ranges separated by commas.  For example:

    parse-acl -p -s '172.16.0.0/12 le 32,192.0.2.20' FILE...

This is equivalent to running ```parse-acl``` twice and merging the
results.

DNS lookups for ```fqdn``` statements are disabled by default so
that the running of the command is not dependent on the network.
They can be enabled using ```-l```.  If not set, the address 0.0.0.1/32
is substituted instead of the actual IP address or addresses of the FQDN.
If the resolver got an error (non-existent domain, server failure,
etc.), the address 0.0.0.2/32 is substituted.

A keyword represent classes of IP addresses such as global or private
RFC 1918 addresses.  The keywords are based on attributes from the
Python ipaddress module.  The complete list is: ```multicast```,
```private```, ```global```, ```unspecified```, ```reserved```,
```loopback```, and ```link_local```.

## Requirements

- Python 3.8 or later
- Bourne shell (to run tests)

## Examples

### Prefix list examples

| Argument | Description |
| --- | --- |
| ```1.1.1.1```                 | Look for a single IP address |
| ```1.1.1.0/24```              | Look for a specific subnet |
| ```1.1.1.0/24 le 32```        | Look for any IP address or subnet in a subnet |
| ```1.1.1.1 ge 0```            | Look for a single IP address or any other supernets that match |
| ```1.1.1.1 ge 1```            | Look for a single IP address or any other supernets that match except the default route |
| ```1.1.0.0/16 ge 0```         | Look for any supernets of a subnet including the default route |
| ```1.1.0.0/16 ge 1```         | Look for any supernets of a subnet except the default route |
| ```1.1.1.0/24 ge 1 le 32```   | Look for any subnets or supernets of a subnet except the default route |
| ```1.1.1.0/24 ge 32 le 32```  | Look for host IP addresses in a subnet |

### Command line examples

| Command line | Which matches... |
| --- | --- |
| ```parse-acl``` | All IP addresses and subnets |
| ```parse-acl -s 192.0.2.1``` | A single IP address in the source |
| ```parse-acl -s '192.0.2.0/24 le 32'``` | All addresses from a single subnet |
| ```parse-acl -p -s 192.0.2.1``` | Any mention of a single IP address in source or destination |
| ```parse-acl -p -s 192.0.2.1,192.0.2.2``` | Any mention of two IP addresses |
| ```parse-acl -p -s 192.0.2.1 -d 203.0.113.100``` | ACLs between two specific IP addresses (bidirectional) |
| ```parse-acl -s private -d global``` | ACLs from private to global IP addresses (but not vice versa) |
| ```parse-acl -p -s private -d global``` | ACLs from private to global IP addresses (bidirectional) |
| ```parse-acl -o DNS_servers``` | IP addresses in a single object |
| ```parse-acl -O``` | IP addresses in all objects |
