pkgs = [
        "molly-guard",
        "rlwrap",
        "vim",
        "curl",
        "ntp",
        "sysstat",
        "iotop",
        "unzip",
        "ack-grep",
        "git",
        "telnet",
        "screen",
        "manpages-dev",
        "build-essential",
        "pkg-config",
        "python-dev",
        "python-pip",
        "libtool",
        "autoconf"
]

apt_package pkgs

#pkgs.each do |pkg|
#    apt_package pkg
#end

