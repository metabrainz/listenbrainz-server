## TIMEZONE
node.set[:tz] = "Etc/UTC" ## The One True Timezone
include_recipe "timezone-ii"

## NTP
node.set[:ntp][:packages] = ["ntp"]
node.set[:ntp] = {
    "is_server" => "false",
    "restrictions" => [
        "127.0.0.1",
        ## having examined the ntp.conf template, we inject some extra config lines here
        ## we don't want ntp using IPv6, or it falls over with loads of upped IPs.
        "::1\ninterface ignore ipv6\ninterface listen ipv4\n"
    ]
}

node.set[:ntp][:servers] = [
      "0.north-america.pool.ntp.org",
      "1.north-america.pool.ntp.org",
      "2.north-america.pool.ntp.org",
      "3.north-america.pool.ntp.org"
  ]

include_recipe "ntp"

