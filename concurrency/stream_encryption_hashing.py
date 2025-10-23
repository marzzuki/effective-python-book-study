import os
import subprocess


def encrypt(data):
    env = os.environ.copy()
    env["password"] = "some_weak_password"

    proc = subprocess.Popen(
        ["openssl", "enc", "-des3", "-pbkdf2", "-pass", "env:password"],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )

    proc.stdin.write(data)
    proc.stdin.flush()
    return proc


def hash(input_pipe):
    return subprocess.Popen(
        ["openssl", "dgst", "-sha256", "-binary"],
        stdin=input_pipe,
        stdout=subprocess.PIPE,
    )


encrypt_procs = []
hash_procs = []

for _ in range(3):
    data = os.urandom(100)

    enc_p = encrypt(data)
    encrypt_procs.append(enc_p)

    hash_p = hash(enc_p.stdout)
    hash_procs.append(hash_p)

    enc_p.stdout.close()
    enc_p.stdout = None

for proc in encrypt_procs:
    proc.communicate()
    assert proc.returncode == 0

for proc in hash_procs:
    out, _ = proc.communicate()
    print(out[-10:])
    assert proc.returncode == 0
