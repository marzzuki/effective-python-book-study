import os
import subprocess
import time

import tqdm


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
    proc.stdin.close()
    return proc


def hash(input_pipe):
    return subprocess.Popen(
        ["openssl", "dgst", "-sha256", "-binary"],
        stdin=input_pipe,
        stdout=subprocess.PIPE,
    )


def pipeline_pair(data):
    """Start one encrypt→hash pair."""
    enc_p = encrypt(data)
    hash_p = hash(enc_p.stdout)
    enc_p.stdout.close()
    enc_p.stdout = None
    return enc_p, hash_p


def concurrent_pipeline(runs=1000):
    start = time.perf_counter()
    encrypt_procs = []
    hash_procs = []

    for _ in tqdm.tqdm(range(runs)):
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
        # print(out[-10:])
        assert proc.returncode == 0

    end = time.perf_counter()
    delta = end - start
    print(f"Time Taken: {delta}")


def sequential_pipeline(runs=1000):
    start = time.perf_counter()

    for _ in tqdm.tqdm(range(runs)):
        data = os.urandom(100)

        enc_p = encrypt(data)

        hash_p = hash(enc_p.stdout)
        out, _ = hash_p.communicate()
        enc_p.stdout.close()
        enc_p.stdout = None

        # print(out[-10:])

    end = time.perf_counter()
    delta = end - start
    print(f"Time Taken: {delta}")


def limited_concurrent_pipeline(runs=10000, limit=8):
    """Keep only `limit` active pipelines at a time."""
    start = time.perf_counter()
    encrypt_procs = []
    hash_procs = []
    completed = 0

    for _ in tqdm.tqdm(range(runs)):
        data = os.urandom(100)
        enc_p, hash_p = pipeline_pair(data)
        encrypt_procs.append(enc_p)
        hash_procs.append(hash_p)

        # When limit reached → wait for first batch to finish
        if len(hash_procs) >= limit:
            for p in encrypt_procs:
                p.communicate()
                assert p.returncode == 0
            encrypt_procs.clear()

            for p in hash_procs:
                p.communicate()
                assert p.returncode == 0
            hash_procs.clear()

            completed += limit

    # Wait for leftover processes
    for p in encrypt_procs:
        p.communicate()
        assert p.returncode == 0
    for p in hash_procs:
        p.communicate()
        assert p.returncode == 0

    end = time.perf_counter()
    print(f"Time Taken ({limit} concurrent): {end - start:.2f}s")


print(os.cpu_count())  # 16
# ulimit -n (Kernel limit per process) => 524288 (That means any process (including Python) can only have 524288 file descriptors open.)
# ulimit -u (Kernel (total processes system-wide)) => 126657

limited_concurrent_pipeline(10000, limit=32)  # Time Taken (32 concurrent): 8.89s
sequential_pipeline(10000)  # Time Taken 41.8040830769969
concurrent_pipeline(10000)  # Time Taken: 266.8267484120006 (Lots of context switching)

"""
Most modern CPUs have 8 cores (sometimes 8 physical / 16 logical with hyperthreading).

When you spawn processes that are CPU-bound (like encryption + hashing),
→ each one can only use one core efficiently.

So if you have 8 cores, you can do 8 full-speed things in parallel.
The 9th process won’t speed anything up — it’ll just make the OS juggle context switches.

That’s why “number of cores” ≈ sweet spot for CPU-bound tasks.
"""
