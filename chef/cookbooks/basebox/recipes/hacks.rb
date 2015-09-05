## Oracle's server often times out when downloading JDK, among others:

## default of 10 mins is a bit low. downloading some assets can timeout
## so we bump it to 30 min:
module Mixlib
    class ShellOut
        DEFAULT_READ_TIMEOUT = 1800
    end
end
