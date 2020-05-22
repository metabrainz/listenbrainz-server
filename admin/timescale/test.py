import json

def remove_empty_keys(listen):

    if "track_metadata" in listen:
        listen["track_metadata"] = remove_empty_keys(listen["track_metadata"])
        if "additional_info" in listen["track_metadata"]:
            listen["track_metadata"]["additional_info"] = remove_empty_keys(listen["track_metadata"]["additional_info"])

    return {k: v for k, v in listen.items() if v }

a = {
    "foo" : {},
    "bar" : 1,
    "track_metadata" : { 
        "rump" : "",
        "sump" : "save me!",
        "plump" : [],
        "additional_info" : {
            "moo" : "",
            "mah" : 1
        }
    }
}


print(json.dumps(remove_empty_keys(a), sort_keys=True, indent=4))
