"""Refresh Vertex AI OAuth token and update Hermes .env file.
Run this before starting Hermes agents.
Tokens are valid for ~1 hour.
"""
import google.auth
import google.auth.transport.requests
import os

def get_token():
    creds, project = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token

def update_env(env_path, token):
    lines = []
    with open(env_path, 'r') as f:
        lines = f.readlines()

    with open(env_path, 'w') as f:
        for line in lines:
            if line.startswith('OPENROUTER_API_KEY='):
                f.write(f'OPENROUTER_API_KEY={token}\n')
            else:
                f.write(line)

if __name__ == '__main__':
    token = get_token()
    env_path = os.path.join(os.path.dirname(__file__), '..', 'vendor', 'hermes-agent', '.env')
    update_env(os.path.abspath(env_path), token)
    print(f'Token refreshed: {token[:20]}...')
