MODULE = {
    "summary": (
        "PQC advisory is cryptography advisory. Before you can scope a migration you need to know what each primitive "
        "does, which ones Shor breaks and which Grover only weakens, how TLS 1.3 and PKI fit together, where keys live "
        "(HSMs, KMS), and where a bank actually uses each primitive. This module builds that map and measures the "
        "classical algorithms you will later compare PQC against (I11)."
    ),
    "concepts": [
        {
            "title": "Symmetric encryption, hashes and MACs",
            "why": (
                "Most bulk data in a bank is protected by symmetric cryptography (AES) and integrity is protected by "
                "hashes and MACs. These are only **weakened** by quantum computers (Grover), not broken, so they are the "
                "part of the estate that mostly needs parameter checks (key length), not algorithm replacement."
            ),
            "how": r"""
* **AES** (FIPS 197) {{c:p5_fips197}}: block cipher, 128-bit block, 128/192/256-bit keys. Use an AEAD mode (**AES-GCM**) which
  gives confidentiality and integrity; never reuse a (key, nonce) pair.
* **Hashes**: SHA-2 (FIPS 180-4), SHA-3 (FIPS 202). Collision resistance $\approx 2^{n/2}$ classically.
* **MAC**: HMAC-SHA-256 (RFC 2104) proves a message came from a key holder. Compare tags in **constant time**.
* Grover gives a square-root search speedup, so a $k$-bit key has roughly $k/2$ bits of quantum security, before
  accounting for Grover's poor parallelisation and long serial depth. AES-256 is the conventional choice for long-term confidentiality. {{c:p5_grover_aes}}
""",
            "code": """import os, time, hmac, hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
key = AESGCM.generate_key(bit_length=256); aes = AESGCM(key); nonce = os.urandom(12)
msg = b"MT103 payment instruction ..." * 10
ct = aes.encrypt(nonce, msg, b"header")
print("ciphertext len", len(ct), "= msg", len(msg), "+ 16-byte tag")
print("decrypt ok:", aes.decrypt(nonce, ct, b"header") == msg)
tag = hmac.new(b"k"*32, msg, hashlib.sha256).digest()
print("HMAC constant-time verify:", hmac.compare_digest(tag, hmac.new(b"k"*32, msg, hashlib.sha256).digest()))
""",
            "impact": (
                "For a client, the symmetric estate is mostly a configuration-hygiene exercise: find AES-128 and 3DES in "
                "long-lived data paths and move to AES-256; find SHA-1. It is cheaper than the asymmetric migration and "
                "a fast early win for the board report."
            ),
        },
        {
            "title": "Public-key cryptography: RSA, Diffie–Hellman, ECC, ECDSA",
            "why": (
                "Public-key cryptography solves key distribution and authentication between parties who never met. It "
                "rests on two problems, **integer factoring** (RSA) and **discrete logarithms** (DH, ECC, ECDSA), and "
                "Shor's algorithm solves both in polynomial time on a large fault-tolerant quantum computer {{c:p5_shor}}. "
                "This is the part of the estate that must be replaced, not reconfigured."
            ),
            "how": r"""
* **RSA**: $n=pq$, $ed\equiv1 \pmod{\varphi(n)}$. Encrypt $c=m^e \bmod n$, decrypt $m=c^d\bmod n$. Security ⇔ hardness of factoring $n$.
  Signatures: $s=H(m)^d$ (with padding: PSS).
* **Diffie–Hellman / ECDH (X25519)**: both sides derive a shared secret from public values; security ⇔ discrete log.
* **ECDSA / EdDSA** (FIPS 186-5): signatures on elliptic curves (P-256, Ed25519). Smaller keys and faster than RSA at equal classical security.
* Classical security: RSA-2048 ≈ 112 bits; P-256 ≈ 128 bits. Quantum: both ≈ 0 once a CRQC exists.
""",
            "code": """p, q = 65519, 65521                        # toy primes
n, phi, e = p*q, (p-1)*(q-1), 65537
d = pow(e, -1, phi)
m = 42; c = pow(m, e, n)
print("n =", n, " decrypt ->", pow(c, d, n))
# break it classically: tiny n factors instantly. Shor does this for 2048-bit n.
f = next(i for i in range(3, int(n**.5)+1, 2) if n % i == 0)
print("factored:", f, n//f)
""",
            "impact": (
                "Every TLS session, every certificate, every code-signing key and most payment authentication rests on RSA "
                "or ECC. The asymmetric inventory is the core of a PQC programme: it determines scope, vendor dependencies "
                "and the critical path."
            ),
        },
        {
            "title": "Digital signatures, certificates, PKI and the TLS 1.3 handshake",
            "why": (
                "Banks do not use raw primitives; they use protocols. TLS 1.3 (RFC 8446) {{c:p5_tls13}} combines an ephemeral key "
                "exchange (confidentiality, forward secrecy) with certificate-based signatures (authentication). The two halves "
                "have different quantum urgency, and migration plans that do not separate them get the priorities wrong."
            ),
            "how": r"""
TLS 1.3 full handshake (1-RTT):
1. ClientHello: supported groups (e.g. X25519, or hybrid X25519+ML-KEM), key share, signature algorithms.
2. ServerHello: chosen group and key share → both derive handshake secrets via HKDF.
3. Server sends Certificate + CertificateVerify (signature over the transcript) + Finished.
4. Client verifies the chain to a trusted root (PKI), checks the signature, sends Finished. Application data flows under AES-GCM or ChaCha20-Poly1305.

* **Key exchange** protects confidentiality → exposed to *harvest now, decrypt later* today.
* **Signatures/certificates** protect authentication at handshake time → exposed only once a CRQC exists (forgery), but long-lived roots and
  firmware/code-signing keys have long lifetimes. Hence PQC key exchange is usually deployed first (hybrid), signatures later.
""",
            "code": """import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
key = ec.generate_private_key(ec.SECP256R1())
name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "lab.qfin.test")])
now = datetime.datetime.now(datetime.timezone.utc)
cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=825)).sign(key, hashes.SHA256()))
print("signature algorithm:", cert.signature_algorithm_oid._name)
print("public key:", type(cert.public_key()).__name__, cert.public_key().curve.name)
print("validity days:", (cert.not_valid_after_utc - cert.not_valid_before_utc).days)
""",
            "impact": (
                "The client message: 'Start with key exchange on externally facing and high-value internal channels, because "
                "recorded traffic can be decrypted later. Plan signatures and PKI next; they take longest because of roots, HSMs, "
                "devices and partners.' That sentence alone often reorders a bank's PQC plan. (Judgement {{c:p5_order_j}})"
            ),
        },
        {
            "title": "HSMs, key management and where banks use each primitive",
            "why": (
                "Keys live in HSMs and KMS, which run vendor firmware with validated algorithm lists. A bank cannot deploy "
                "ML-DSA for card issuance until its HSMs, their firmware and their certifications support it. Key "
                "management is therefore often the critical path, not the algorithm."
            ),
            "how": r"""
* **HSM**: tamper-resistant device holding keys; operations run inside; FIPS 140-3 / PCI PTS HSM validated.
* **KMS**: cloud or enterprise service wrapping HSMs; envelope encryption (data keys wrapped by master keys).
* Typical bank map (Judgement; verify in each inventory {{c:p5_bankmap_j}}):

| Area | Primitives | Quantum exposure |
|---|---|---|
| External APIs, web, mobile | TLS 1.3: ECDHE, RSA/ECDSA certs, AES-GCM | Key exchange (HNDL), certs |
| Card payments (EMV) | RSA for offline data authentication; 3DES/AES for session keys | RSA in cards with multi-year lifetimes |
| Interbank (SWIFT) | PKI, TLS, HSM-held keys | Signatures, key exchange |
| Internal PKI, VPN, SSH | RSA/ECDSA certs, ECDH | All asymmetric |
| Code and firmware signing | RSA/ECDSA | Long-lived signatures |
| Data at rest, backups | AES (key length) | Grover margin only |
""",
            "code": """import time
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives import hashes
for name, gen in [("RSA-2048", lambda: rsa.generate_private_key(65537, 2048)), ("ECDSA P-256", lambda: ec.generate_private_key(ec.SECP256R1()))]:
    t=time.perf_counter(); k=gen(); kg=time.perf_counter()-t
    msg=b"x"*256; t=time.perf_counter()
    sig = k.sign(msg, padding.PKCS1v15(), hashes.SHA256()) if name.startswith("RSA") else k.sign(msg, ec.ECDSA(hashes.SHA256()))
    print(f"{name}: keygen {kg*1e3:.1f} ms, sign {(time.perf_counter()-t)*1e3:.2f} ms, sig {len(sig)} bytes")
""",
            "impact": (
                "Ask every client three HSM questions on day one: which models and firmware, which algorithms are on the "
                "vendor's PQC roadmap with dates (Sourced, dated), and when certification follows. The answers usually set "
                "the earliest credible migration date for payments and PKI."
            ),
        },
    ],
    "lens": {
        "look": "Classify every cryptographic use by primitive (symmetric/hash/asymmetric), purpose (confidentiality/integrity/authentication), data shelf life, and where the key lives.",
        "decision": "Which parts of the estate need replacement (asymmetric), which need parameter changes (symmetric key lengths, hash choice), and in what order.",
        "justified": "Shor breaks factoring and discrete-log schemes; Grover only halves symmetric security; confidentiality is exposed to HNDL now, authentication only later.",
        "mistakes": [
            "Treating AES as 'broken by quantum' and scoping a symmetric replacement programme.",
            "Treating signatures and key exchange as one workstream and missing the HNDL urgency of key exchange.",
            "Ignoring HSM firmware and certification lead times.",
            "Comparing HMAC tags with == (timing leak) or reusing AES-GCM nonces.",
            "Assuming TLS terminates at the bank; ignoring CDNs, load balancers and partners that terminate it.",
        ],
        "impact": "Wasted budget on symmetric replacement; HNDL exposure on long-lived confidential data left unaddressed; migration dates slipping on HSM dependencies.",
        "test": "Lab P5: benchmark AES-GCM, SHA-256, HMAC, RSA-2048, ECDSA P-256 and X25519 on your machine; record key and signature sizes for the I11 comparison.",
    },
    "claims": [
        {"id": "p5_fips197", "tag": "S", "text": "AES is specified in FIPS 197 (block 128 bits; keys 128/192/256).",
         "source": {"title": "FIPS 197: Advanced Encryption Standard (AES), updated", "publisher": "NIST", "date": "2001-11 (update 2023-05)", "url": "https://csrc.nist.gov/pubs/fips/197/final"},
         "last_verified": "2026-10-19"},
        {"id": "p5_shor", "tag": "S", "text": "Shor's algorithm factors integers and computes discrete logarithms in polynomial time on a quantum computer.",
         "source": {"title": "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer", "publisher": "SIAM Journal on Computing 26(5) (P. Shor)", "date": "1997", "url": "https://doi.org/10.1137/S0097539795293172"},
         "last_verified": "2026-10-19"},
        {"id": "p5_tls13", "tag": "S", "text": "TLS 1.3 handshake structure (1-RTT, ephemeral key exchange, CertificateVerify).",
         "source": {"title": "RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3", "publisher": "IETF", "date": "2018-08", "url": "https://www.rfc-editor.org/rfc/rfc8446"},
         "last_verified": "2026-10-19"},
        {"id": "p5_grover_aes", "tag": "S", "text": "NSA CNSA 2.0 specifies AES-256 for symmetric encryption in national security systems.",
         "source": {"title": "Announcing the Commercial National Security Algorithm Suite 2.0", "publisher": "NSA", "date": "2022-09", "url": "https://media.defense.gov/2022/Sep/07/2003071834/-1/-1/0/CSA_CNSA_2.0_ALGORITHMS_.PDF"},
         "last_verified": "2026-10-19"},
        {"id": "p5_order_j", "tag": "J", "text": "Deploy PQC key exchange (hybrid) before signatures for most banks because of HNDL exposure; adjust for each bank's inventory."},
        {"id": "p5_bankmap_j", "tag": "J", "text": "The table of bank cryptographic uses is a typical practitioner map; each bank's inventory must confirm it."},
        {"id": "p5_sizes", "tag": "M", "text": "RSA-2048 signatures are 256 bytes; ECDSA P-256 DER signatures are 70–72 bytes.",
         "check": """from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives import hashes
k=rsa.generate_private_key(65537,2048); assert len(k.sign(b'm',padding.PKCS1v15(),hashes.SHA256()))==256
e=ec.generate_private_key(ec.SECP256R1()); assert 68<=len(e.sign(b'm',ec.ECDSA(hashes.SHA256())))<=72"""},
    ],
    "lab": {
        "id": "p5_lab",
        "title": "Benchmark the classical cryptography that PQC will replace",
        "hypothesis": (
            "H1: ECDSA P-256 signing is faster than RSA-2048 signing on this machine (median of 200). "
            "H2: RSA-2048 verification is faster than RSA-2048 signing by >5× (e=65537 makes verify cheap). "
            "H3: AES-256-GCM throughput exceeds 100 MB/s on 1 MB messages."
        ),
        "thresholds": "Medians over 200 repetitions; H2 ratio > 5; H3 > 100 MB/s.",
        "data": "Random messages generated locally. No external systems touched.",
        "code": r'''import os, time, statistics as st, hashlib, hmac
import pandas as pd
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding, x25519
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from qlab_helpers import record, table

def med(f, n=200):
    ts = []
    for _ in range(n):
        t = time.perf_counter(); f(); ts.append(time.perf_counter() - t)
    return st.median(ts)

msg = os.urandom(512)
rsa_k = rsa.generate_private_key(65537, 2048); rsa_sig = rsa_k.sign(msg, padding.PSS(padding.MGF1(hashes.SHA256()), 32), hashes.SHA256())
ec_k = ec.generate_private_key(ec.SECP256R1()); ec_sig = ec_k.sign(msg, ec.ECDSA(hashes.SHA256()))
pss = padding.PSS(padding.MGF1(hashes.SHA256()), 32)
rows = []
rows.append({"op": "RSA-2048 keygen", "median_ms": 1e3*med(lambda: rsa.generate_private_key(65537, 2048), 20)})
rows.append({"op": "RSA-2048 sign (PSS)", "median_ms": 1e3*med(lambda: rsa_k.sign(msg, pss, hashes.SHA256()))})
rows.append({"op": "RSA-2048 verify", "median_ms": 1e3*med(lambda: rsa_k.public_key().verify(rsa_sig, msg, pss, hashes.SHA256()))})
rows.append({"op": "ECDSA P-256 keygen", "median_ms": 1e3*med(lambda: ec.generate_private_key(ec.SECP256R1()))})
rows.append({"op": "ECDSA P-256 sign", "median_ms": 1e3*med(lambda: ec_k.sign(msg, ec.ECDSA(hashes.SHA256())))})
rows.append({"op": "ECDSA P-256 verify", "median_ms": 1e3*med(lambda: ec_k.public_key().verify(ec_sig, msg, ec.ECDSA(hashes.SHA256())))})
a, b = x25519.X25519PrivateKey.generate(), x25519.X25519PrivateKey.generate()
rows.append({"op": "X25519 key agreement", "median_ms": 1e3*med(lambda: a.exchange(b.public_key()))})
big = os.urandom(1 << 20); aes = AESGCM(AESGCM.generate_key(bit_length=256)); nonce = os.urandom(12)
t_aes = med(lambda: aes.encrypt(nonce, big, None), 30)
rows.append({"op": "AES-256-GCM encrypt 1 MB", "median_ms": 1e3*t_aes})
rows.append({"op": "SHA-256 1 MB", "median_ms": 1e3*med(lambda: hashlib.sha256(big).digest(), 30)})
rows.append({"op": "HMAC-SHA256 1 MB", "median_ms": 1e3*med(lambda: hmac.new(b"k"*32, big, hashlib.sha256).digest(), 30)})
df = pd.DataFrame(rows); table(df.round(4), "Median timings on this machine")

sizes = pd.DataFrame([
    {"algorithm": "RSA-2048", "public key bytes (DER)": len(rsa_k.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)), "signature bytes": len(rsa_sig)},
    {"algorithm": "ECDSA P-256", "public key bytes (DER)": len(ec_k.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)), "signature bytes": len(ec_sig)},
    {"algorithm": "X25519", "public key bytes (DER)": len(a.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)), "signature bytes": None},
])
table(sizes, "Key and signature sizes (baseline for I11 PQC comparison)")
d = dict(zip(df.op, df.median_ms))
record("ecdsa_faster_than_rsa_sign", d["ECDSA P-256 sign"] < d["RSA-2048 sign (PSS)"])
record("rsa_sign_over_verify", d["RSA-2048 sign (PSS)"]/d["RSA-2048 verify"])
record("aes_gcm_MBps", 1/t_aes)
record("timings_ms", d)
print(df.to_string(index=False)); print(sizes.to_string(index=False))
''',
        "expect": {"ecdsa_faster_than_rsa_sign": "x is True", "rsa_sign_over_verify": "x > 5", "aes_gcm_MBps": "x > 100"},
        "report_hints": "These numbers are your machine's. In section 9, translate sizes into TLS handshake bytes and say what PQC will change (I11).",
    },
    "quiz": [
        {"id": "p5q1", "type": "mc", "q": "Which primitive does Shor's algorithm break?", "options": ["AES-256", "SHA-256", "ECDSA P-256", "HMAC-SHA256"], "answer": 2,
         "explain": "Discrete log on elliptic curves.", "tags": ["threat"]},
        {"id": "p5q2", "type": "mc", "q": "Grover's algorithm against a 256-bit AES key gives roughly how many bits of quantum security?",
         "options": ["0", "64", "128", "256"], "answer": 2, "explain": "Square-root search: k/2.", "tags": ["threat"]},
        {"id": "p5q3", "type": "mc", "q": "Which TLS 1.3 component is exposed to harvest-now-decrypt-later?",
         "options": ["Certificate signature", "Ephemeral key exchange", "Finished MAC", "Record padding"], "answer": 1,
         "explain": "Recorded key shares let a future CRQC recover session keys.", "tags": ["tls"]},
        {"id": "p5q4", "type": "mc", "q": "AES-GCM's critical usage rule is:", "options": ["Use 128-bit keys only", "Never reuse a (key, nonce) pair", "Always pad to 16 bytes", "Use ECB for speed"], "answer": 1,
         "explain": "Nonce reuse breaks confidentiality and authenticity.", "tags": ["symmetric"]},
        {"id": "p5q5", "type": "mc", "q": "HMAC tags must be compared with:", "options": ["==", "a constant-time comparison", "a hash of both", "a regex"], "answer": 1,
         "explain": "hmac.compare_digest avoids timing leaks.", "tags": ["symmetric"]},
        {"id": "p5q6", "type": "mc", "q": "RSA-2048's approximate classical security level is:", "options": ["80 bits", "112 bits", "128 bits", "2048 bits"], "answer": 1, "explain": "NIST SP 800-57 equivalence.", "tags": ["public key"]},
        {"id": "p5q7", "type": "mc", "q": "In TLS 1.3, server authentication is proven by:", "options": ["ServerHello", "CertificateVerify signature over the transcript", "The cipher suite", "Session ticket"], "answer": 1,
         "explain": "Signature with the certificate's private key.", "tags": ["tls"]},
        {"id": "p5q8", "type": "mc", "q": "Why is HSM firmware often the PQC critical path?", "options": ["HSMs are slow", "Algorithms must be implemented, validated and certified by the vendor before use", "HSMs only support AES", "Regulators forbid HSMs"], "answer": 1,
         "explain": "Vendor roadmaps and certification lead times.", "tags": ["hsm"]},
        {"id": "p5q9", "type": "mc", "q": "For data at rest under AES-256, the PQC programme typically needs:", "options": ["Algorithm replacement", "Mainly confirmation of key length and key-wrapping (asymmetric) paths", "Nothing ever", "Re-encryption with RSA"], "answer": 1,
         "explain": "Symmetric is fine; check wrapping keys exchanged with RSA/ECDH.", "tags": ["scope"]},
        {"id": "p5q10", "type": "mc", "q": "Which FIPS specifies ECDSA and EdDSA?", "options": ["FIPS 197", "FIPS 180-4", "FIPS 186-5", "FIPS 203"], "answer": 2, "explain": "Digital Signature Standard.", "tags": ["standards"]},
        {"id": "p5q11", "type": "short", "q": "Explain to a CISO why key exchange and signatures have different PQC urgency.",
         "must": [["harvest", "record", "store now", "decrypt later"], ["authenticat", "forg", "signature"], ["now", "today", "later", "future"]],
         "explain": "Key exchange: traffic recorded today can be decrypted later (HNDL). Signatures: forgery requires a CRQC at the time of use, though long-lived keys matter.", "tags": ["tls"]},
        {"id": "p5q12", "type": "short", "q": "Name three places in a bank where RSA or ECC keys typically live beyond web TLS.",
         "must": [["emv", "card", "payment"], ["code sign", "firmware", "code-sign"], ["vpn", "ssh", "internal pki", "swift", "hsm"]],
         "explain": "EMV cards/issuance, code and firmware signing, VPN/SSH/internal PKI, SWIFT PKI, HSM-wrapped keys.", "tags": ["scope"]},
    ],
    "exercise": {
        "id": "p5_ex",
        "title": "Toy RSA, its classical break, and safe MAC verification",
        "prompt": (
            "Implement:\n1. `rsa_keygen(p, q, e=65537)` → (n, e, d).\n2. `rsa_encrypt(m, n, e)` and `rsa_decrypt(c, n, d)`.\n"
            "3. `factor(n)` → (p, q) by trial division (fine for toy n).\n4. `break_rsa(c, n, e)` recovers m using `factor`.\n"
            "5. `verify_tag(key, msg, tag)` HMAC-SHA256 verification with constant-time compare.\n"
            "Use only the standard library (pow(e, -1, phi) gives modular inverses)."
        ),
        "starter": '''import hmac, hashlib

def rsa_keygen(p, q, e=65537):
    raise NotImplementedError

def rsa_encrypt(m, n, e):
    raise NotImplementedError

def rsa_decrypt(c, n, d):
    raise NotImplementedError

def factor(n):
    raise NotImplementedError

def break_rsa(c, n, e):
    raise NotImplementedError

def verify_tag(key, msg, tag):
    raise NotImplementedError
''',
        "solution": '''import hmac, hashlib

def rsa_keygen(p, q, e=65537):
    phi = (p-1)*(q-1)
    return p*q, e, pow(e, -1, phi)

def rsa_encrypt(m, n, e):
    return pow(m, e, n)

def rsa_decrypt(c, n, d):
    return pow(c, d, n)

def factor(n):
    if n % 2 == 0:
        return 2, n//2
    i = 3
    while i*i <= n:
        if n % i == 0:
            return i, n//i
        i += 2
    raise ValueError("prime")

def break_rsa(c, n, e):
    p, q = factor(n)
    d = pow(e, -1, (p-1)*(q-1))
    return pow(c, d, n)

def verify_tag(key, msg, tag):
    return hmac.compare_digest(hmac.new(key, msg, hashlib.sha256).digest(), tag)
''',
        "tests": '''import hmac, hashlib
P, Q = 65521, 65537

def test_roundtrip():
    n, e, d = rsa_keygen(P, Q)
    for m in (0, 1, 42, 123456789):
        assert rsa_decrypt(rsa_encrypt(m, n, e), n, d) == m

def test_factor():
    assert sorted(factor(P*Q)) == [P, Q]

def test_break():
    """the classical break works because n is tiny; Shor removes 'tiny' from that sentence"""
    n, e, d = rsa_keygen(P, Q)
    assert break_rsa(rsa_encrypt(987654321, n, e), n, e) == 987654321

def test_verify_tag():
    k, m = b"k"*32, b"pay 100"
    t = hmac.new(k, m, hashlib.sha256).digest()
    assert verify_tag(k, m, t) and not verify_tag(k, b"pay 900", t)

def test_constant_time_used():
    """inspect source: must use hmac.compare_digest"""
    import inspect
    assert "compare_digest" in inspect.getsource(verify_tag)
''',
    },
    "cards": [
        {"front": "What Shor breaks", "back": "RSA, finite-field DH, ECDH, ECDSA/EdDSA (factoring and discrete log)", "kind": "definition"},
        {"front": "What Grover does to AES-k", "back": "≈ k/2 bits of quantum security; use AES-256", "kind": "number"},
        {"front": "AES standard", "back": "FIPS 197; 128-bit block; 128/192/256-bit keys", "kind": "definition"},
        {"front": "Signature standard (ECDSA, EdDSA, RSA)", "back": "FIPS 186-5 (2023)", "kind": "definition"},
        {"front": "TLS 1.3 RFC", "back": "RFC 8446 (Aug 2018)", "kind": "definition"},
        {"front": "HNDL-exposed part of TLS", "back": "Ephemeral key exchange (confidentiality)", "kind": "definition"},
        {"front": "RSA-2048 classical security", "back": "≈ 112 bits", "kind": "number"},
        {"front": "RSA-2048 signature size", "back": "256 bytes", "kind": "number"},
        {"front": "ECDSA P-256 signature size (DER)", "back": "≈ 70–72 bytes", "kind": "number"},
        {"front": "AES-GCM rule", "back": "Never reuse (key, nonce)", "kind": "mistake"},
        {"front": "HMAC compare", "back": "Constant-time: hmac.compare_digest", "kind": "mistake"},
        {"front": "PQC critical path often is…", "back": "HSM firmware, certification and partner/vendor support", "kind": "definition"},
    ],
    "defend": {
        "persona": "cro",
        "questions": [
            {"q": "Is all our encryption broken by quantum computers?",
             "must": [["no", "not"], ["aes", "symmetric"], ["rsa", "ecc", "public", "asymmetric"]],
             "model": "No. Asymmetric (RSA, ECC) is broken by Shor; symmetric (AES-256) and hashes are only weakened by Grover and remain fine with adequate key lengths."},
            {"q": "Why spend now if no such computer exists?",
             "must": [["harvest", "record", "decrypt later"], ["migration", "years", "long", "mosca"]],
             "model": "Harvest-now-decrypt-later on long-lived data, and migrations take years (Mosca)."},
            {"q": "What do we do first?",
             "must": [["inventory", "discover", "cbom"], ["key exchange", "tls", "hybrid"]],
             "model": "Inventory, then hybrid PQC key exchange on high-value channels, then signatures/PKI."},
            {"q": "What could delay us that's outside our control?",
             "must": [["hsm", "vendor", "firmware"], ["partner", "card scheme", "swift", "third", "certif"]],
             "model": "HSM and vendor firmware/certification, card scheme and SWIFT timelines, third parties terminating TLS."},
            {"q": "Which of our data is most exposed?",
             "must": [["long", "shelf", "lifetime", "years"], ["confidential", "personal", "customer", "strategic", "archive"]],
             "model": "Data with long confidentiality shelf life transmitted over asymmetric key exchange today: customer data, M&A, strategic and archived records."},
        ],
    },
    "glossary": {
        "AES-GCM": "Authenticated encryption mode providing confidentiality and integrity.",
        "HMAC": "Keyed hash-based message authentication code.",
        "ECDSA": "Elliptic-curve digital signature algorithm.",
        "X25519": "Elliptic-curve Diffie–Hellman function on Curve25519.",
        "PKI": "Public key infrastructure: CAs, certificates, trust chains.",
        "HSM": "Hardware security module holding keys and performing crypto operations.",
        "Harvest now, decrypt later (HNDL)": "Recording encrypted traffic today to decrypt once a CRQC exists.",
        "CRQC": "Cryptographically relevant quantum computer.",
    },
}
