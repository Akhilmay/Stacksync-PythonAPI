# Stacksync-PythonAPI
Flask API that takes python script, executes it safely inside a sandboxed jail,and captures stdout and returns the JSON value of the script

Base URL: https://stacksync-pythonapi-76hsvrvpoq-uc.a.run.app


POST Request: 
endpoint    : https://stacksync-pythonapi-76hsvrvpoq-uc.a.run.app/execute 
Headers     : "Content-Type: application/json"
Request Body: { 
                "script": "def main():\n    print(\"hello\")\n    return {\"msg\": \"hello\"}" 
              }

Response:
{
  "return": {
    "msg": "hello"
  },
  "stdout": "hello"
}

