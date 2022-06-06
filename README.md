# parse-acl
## Find prefix ranges in ACLs from a Cisco firewall or router

This command takes the configuration of a Cisco firewall or router and parses it for subnets that meet certain criteria.
The matching arguments use the same syntax as Cisco prefix lists, but
remove restrictions with the allowable lengths to make matching easier.
A subnet can be a single IP address or can be a subnet with a prefix length that represents the
subnet mask (using a slash followed by the prefix length).
An example of an IP address is ```1.2.3.4``` and an example of a subnet is ```1.2.3.0/24```.

The configuration is currently read from standard input.  In a shell environment, this requires using
redirection from a file using ```<```.  For instance, ```parse-acl -s 1.1.1.1 < firewall-configuration```.

Ideally, the subnet is normalized, meaning that the host portion of the subnet is all zeroes.
An example of a normalized subnet is ```1.2.0.0/16```, whereas ```1.2.3.0/16``` is not normalized because the
portion in the third octet is not zero.  A warning is given if an argument is not normalized, but it is treated
as if it were normalized.
This is also relevant when dealing with configurations that have an IP address and a subnet mask, such as the
```ip address``` statement:

    ip address 1.2.3.4 255.255.255.0

Because the statement has a subnet mask, it is treated as ```1.2.3.0/24```, and ```1.2.3.4``` will not match.

## Command-line options

### Synopsis

```parse-acl [-h] [-s SOURCE] [-d DESTINATION] [-x] [-v] [-t SOURCE1 SOURCE1 MINLEN MAXLEN]```

### Optional arguments

| Option | Description |
| ------ | ----------- |
| ```-h```, ```--help``` |           show this help message and exit |
| ```-s``` *SOURCE*, ```--source``` *SOURCE* | source prefix range to match in configuration |
| ```-d``` *DESTINATION*, ```--destination``` *DESTINATION* |                        destination prefix range to match in configuration
|  ```-x```, ```--reverse``` |        swap the source and destinaton addresses (for convenience) |
| ```-v```, ```--verbose``` |        be verbose |
|  ```-t``` *SOURCE1* *SOURCE2* *MINLEN* *MAXLEN*, ```--test``` *SOURCE1* *SOURCE2* *MINLEN* *MAXLEN* | test the arguments from the command line |

A prefix range consists of an IP address (with an optional prefix
length indicating a subnet), and two optional keywords that specify
the minimum and maximum prefix lengths for matches.

*IP*[```/```*LENGTH*] [```ge``` *M*] [```le``` *N*]

The prefix length must be 0 ≤ length ≤ 32, and 0 ≤ ```ge``` ≤ ```le``` ≤ 32.
Because spaces are used in the syntax, in a shell environment the argument must
be quoted.  Example: 

    parse-acl -s '1.2.3.0/24 le 32' -d '192.168.0.0/16 ge 0 le 32' < file

Note that unlike Cisco prefix lists, there is no dependency for
```ge``` or ```le``` on the prefix length.  For instance, this will
generate an error on a Cisco router:

    example(config)#ip prefix-list EXAMPLE permit 1.2.3.0/24 ge 1 le 32
    % Invalid prefix range for 1.2.3.0/24, make sure: len < ge-value <= le-value

By removing this restriction, supernets can be found also, which is
useful when verifying routing.

## Examples

| Argument | Description |
| --- | --- |
| ```1.1.1.1```                 | Look for a single IP address |
| ```1.1.1.0/24```              | Look for a specific subnet |
| ```1.1.1.0/24 le 32```        | Look for any IP address or subnet in a subnet |
| ```1.1.0.0/16 ge 0```         | Look for any supernets of a subnet including the default route |
| ```1.1.0.0/16 ge 1```         | Look for any supernets of a subnet except the default route |
| ```1.1.1.0/24 ge 1 le 32```   | Look for any subnets or supernets of a subnet except the default route |
| ```1.1.1.0/24 ge 32 le 32```  | Look for host IP addresses in a subnet |
