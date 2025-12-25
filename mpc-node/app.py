import os
import hashlib
from flask import Flask, jsonify
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64

app = Flask(__name__)

NODE_ID = os.getenv('NODE_ID', '1')
NODE_PORT = int(os.getenv('NODE_PORT', '8001'))
NODE_SHARD = os.getenv('NODE_SHARD', '')
ENCRYPTION_KEY = os.getenv('SHARD_ENCRYPTION_KEY', '')


def get_encryption_key():
    if not ENCRYPTION_KEY:
        raise Exception('SHARD_ENCRYPTION_KEY not set')
    return hashlib.sha256(ENCRYPTION_KEY.encode()).digest()


def encrypt_shard(shard: str) -> str:
    key = get_encryption_key()
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(shard.encode()) + encryptor.finalize()
    return base64.b64encode(iv + encrypted).decode()


if NODE_SHARD:
    ENCRYPTED_SHARD = encrypt_shard(NODE_SHARD)
    del NODE_SHARD
else:
    ENCRYPTED_SHARD = ''


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'node_id': NODE_ID,
        'port': NODE_PORT,
        'has_shard': bool(ENCRYPTED_SHARD)
    })


@app.route('/get_shard', methods=['GET'])
def get_shard():
    if not ENCRYPTED_SHARD:
        return jsonify({'error': f'NODE_SHARD not set for node {NODE_ID}'}), 500
    
    return jsonify({
        'encrypted_shard': ENCRYPTED_SHARD,
        'node_id': NODE_ID
    })


if __name__ == '__main__':
    print(f"Starting MPC Node {NODE_ID} on port {NODE_PORT}")
    if not ENCRYPTED_SHARD:
        print(f"WARNING: NODE_SHARD is not set!")
    else:
        print(f"Node {NODE_ID}: Shard encrypted and ready")
    app.run(host='0.0.0.0', port=NODE_PORT, debug=False)
