import json 
res={
        "message": "searching completed...",
        "result": "result"
    }
with open("responses.json","w") as f:
    json.dump(res,f,indent=4)
