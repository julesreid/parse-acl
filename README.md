# parse-acl
## Find prefix ranges in ACLs from a Cisco firewall or router

This command takes the configuration of a Cisco firewall or router and parses it for subnets that meet certain criteria.
A subnet can be a single IP address or can be a subnet with a prefix length that represents the
subnet mask (represented by a slash followed by the prefix length).
An example of an IP address is ```1.2.3.4``` and an example of a subnet is ```1.2.3.0/24```.
Ideally, the subnet is normalized, meaning that the host portion of the subnet is all zeroes.
An example of a normalized subnet is ```1.2.0.0/16```, whereas ```1.2.3.0/16``` is not normalized because the
portion in the third octet is not zero.

The configuration is currently read from standard input.  In a shell environment, this requires using
redirection from a file using ```<```.  For instance, ```parse-acl -s 1.1.1.1 < firewall-configuration```.

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

## Examples

| Argument | Description |
| --- | --- |
| ```1.1.1.1```                 | Look for a single IP address |
| ```1.1.1.0/24```              | Look for a specific subnet |
| ```1.1.1.0/24 le 32```        | Look for any IP address or subnet in a subnet |
| ```1.1.1.0/16 ge 0```         | Look for any supernets of a subnet including the default route |
| ```1.1.0.0/16 ge 1```         | Look for any supernets of a subnet except the default route |
| ```1.1.1.0/24 ge 1 le 32```   | Look for any subnets or supernets of a subnet except the default route |
| ```1.1.1.0/24 ge 32 le 32```  | Look for host IP addresses in a subnet |
