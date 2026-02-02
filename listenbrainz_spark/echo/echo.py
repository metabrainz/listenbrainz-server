def handler(message):
    """ Handler that echos its message it receives back to the queue as response as-is """
    return [
        {
            "type": "echo",
            "message": message
        }
    ]
