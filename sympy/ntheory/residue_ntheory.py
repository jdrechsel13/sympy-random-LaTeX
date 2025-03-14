from __future__ import annotations

from sympy.core.function import Function
from sympy.core.singleton import S
from sympy.external.gmpy import gcd, invert, sqrt, legendre, jacobi
from sympy.polys import Poly
from sympy.polys.domains import ZZ
from sympy.polys.galoistools import gf_crt1, gf_crt2, linear_congruence, gf_csolve
from .primetest import isprime
from .factor_ import factorint, trailing, multiplicity, perfect_power
from .modular import crt
from sympy.utilities.misc import as_int
from sympy.core.random import _randint, randint

from itertools import cycle, product


def n_order(a, n):
    """Returns the order of ``a`` modulo ``n``.

    The order of ``a`` modulo ``n`` is the smallest integer
    ``k`` such that ``a**k`` leaves a remainder of 1 with ``n``.

    Parameters
    ==========

    a : integer
    n : integer, n > 1. a and n should be relatively prime

    Examples
    ========

    >>> from sympy.ntheory import n_order
    >>> n_order(3, 7)
    6
    >>> n_order(4, 7)
    3
    """
    from collections import defaultdict
    a, n = as_int(a), as_int(n)
    if n <= 1:
        raise ValueError("n should be an integer greater than 1")
    a = a % n
    # Trivial
    if a == 1:
        return 1
    if gcd(a, n) != 1:
        raise ValueError("The two numbers should be relatively prime")
    # We want to calculate
    # order = totient(n), factors = factorint(order)
    factors = defaultdict(int)
    for px, kx in factorint(n).items():
        if kx > 1:
            factors[px] += kx - 1
        for py, ky in factorint(px - 1).items():
            factors[py] += ky
    order = 1
    for px, kx in factors.items():
        order *= px**kx
    # Now the `order` is the order of the group.
    # The order of `a` divides the order of the group.
    for p, e in factors.items():
        for _ in range(e):
            if pow(a, order // p, n) == 1:
                order //= p
            else:
                break
    return order


def _primitive_root_prime_iter(p):
    """
    Generates the primitive roots for a prime ``p``.

    The primitive roots generated are not necessarily sorted.
    However, the first one is the smallest primitive root.

    Parameters
    ==========

    p : odd prime

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import _primitive_root_prime_iter
    >>> sorted(_primitive_root_prime_iter(19))
    [2, 3, 10, 13, 14, 15]

    References
    ==========

    .. [1] W. Stein "Elementary Number Theory" (2011), page 44

    """
    # it is assumed that p is an int
    if p == 3:
        yield 2
        return
    if p < 41:
        # small case
        if p == 23:
            g = 5
        elif p == 7 or p % 7 == 3:
            # 3 is the smallest primitive root of p = 7,17,31
            g = 3
        else:
            # 2 is the smallest primitive root of p = 5,11,13,19,29,37
            g = 2
    else:
        v = [(p - 1) // i for i in factorint(p - 1).keys()]
        for g in range(2, p):
            if all(pow(g, pw, p) != 1 for pw in v):
                break
    yield g
    # g**k is the primitive root of p iff gcd(p - 1, k) = 1
    for k in range(3, p, 2):
        if gcd(p - 1, k) == 1:
            yield pow(g, k, p)


def _primitive_root_prime_power_iter(p, e):
    """
    Generates the primitive roots of ``p**e``

    Let g be the primitive root of p.
    If pow(g,p-1,p**2)!=1, then g is primitive root of p**e.

    Parameters
    ==========

    p : odd prime
    e : positive integer

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import _primitive_root_prime_power_iter
    >>> sorted(_primitive_root_prime_power_iter(5, 2))
    [2, 3, 8, 12, 13, 17, 22, 23]

    """
    p2 = p**2
    if e == 1:
        yield from _primitive_root_prime_iter(p)
    else:
        for g in _primitive_root_prime_iter(p):
            t = (g - pow(g, 2 - p, p2)) % p2
            for k in range(0, p2, p):
                if k != t:
                    yield from (g + k + m for m in range(0, p**e, p2))


def _primitive_root_prime_power2_iter(p, e):
    """
    Generates the primitive roots of ``2*p**e``

    If g is the primitive root of p**e,
    then the odd one of g and g+p**e is the primitive root of 2*p**e.

    Parameters
    ==========

    p : odd prime
    e : positive integer

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import _primitive_root_prime_power2_iter
    >>> sorted(_primitive_root_prime_power2_iter(5, 2))
    [3, 13, 17, 23, 27, 33, 37, 47]

    """
    for g in _primitive_root_prime_power_iter(p, e):
        if g % 2 == 1:
            yield g
        else:
            yield g + p**e


def primitive_root(p, smallest=True):
    """
    Returns a primitive root of p or None.

    Parameters
    ==========

    p : integer, p > 1
    smallest : if True the smallest primitive root is returned or None

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import primitive_root
    >>> primitive_root(19)
    2
    >>> primitive_root(21) is None
    True

    References
    ==========

    .. [1] W. Stein "Elementary Number Theory" (2011), page 44
    .. [2] P. Hackman "Elementary Number Theory" (2009), Chapter C

    """
    p = as_int(p)
    if p < 2:
        raise ValueError("p should be an integer greater than 1")
    if p <= 4:
        return p - 1
    if not smallest:
        p_even = p % 2 == 0
        if not p_even:
            q = p  # p is odd
        elif p % 4:
            q = p//2  # p had 1 factor of 2
        else:
            return None  # p had more than one factor of 2
        if isprime(q):
            e = 1
        else:
            m = perfect_power(q)
            if not m:
                return None
            q, e = m
            if not isprime(q):
                return None
        if p_even:
            return next(_primitive_root_prime_power2_iter(q, e))
        return next(_primitive_root_prime_power_iter(q, e))
    f = factorint(p)
    if len(f) > 2:
        return None
    if len(f) == 2:
        if 2 not in f or f[2] > 1:
            return None

        # case p = 2*p1**k, p1 prime
        for p1, e1 in f.items():
            if p1 != 2:
                break
        i = 1
        while i < p:
            i += 2
            if i % p1 == 0:
                continue
            if is_primitive_root(i, p):
                return i

    else:
        if 2 in f:
            if p == 4:
                return 3
            return None
        p1, n = list(f.items())[0]
        if n > 1:
            # see Ref [2], page 81
            g = primitive_root(p1)
            if is_primitive_root(g, p1**2):
                return g
            else:
                for i in range(2, g + p1 + 1):
                    if gcd(i, p) == 1 and is_primitive_root(i, p):
                        return i

    return next(_primitive_root_prime_iter(p))


def is_primitive_root(a, p):
    """
    Returns True if ``a`` is a primitive root of ``p``.

    ``a`` is said to be the primitive root of ``p`` if gcd(a, p) == 1 and
    totient(p) is the smallest positive number s.t.

        a**totient(p) cong 1 mod(p)

    Parameters
    ==========

    a : integer
    p : integer, p > 1. a and p should be relatively prime

    Examples
    ========

    >>> from sympy.ntheory import is_primitive_root, n_order, totient
    >>> is_primitive_root(3, 10)
    True
    >>> is_primitive_root(9, 10)
    False
    >>> n_order(3, 10) == totient(10)
    True
    >>> n_order(9, 10) == totient(10)
    False

    """
    a, p = as_int(a), as_int(p)
    if p <= 1:
        raise ValueError("p should be an integer greater than 1")
    a = a % p
    if gcd(a, p) != 1:
        raise ValueError("The two numbers should be relatively prime")
    # Primitive root of p exist only for
    # p = 2, 4, q**e, 2*q**e (q is odd prime)
    if p <= 4:
        # The primitive root is only p-1.
        return a == p - 1
    if p % 2:
        q = p  # p is odd
    elif p % 4:
        q = p//2  # p had 1 factor of 2
    else:
        return False  # p had more than one factor of 2
    if isprime(q):
        group_order = q - 1
        factors = factorint(q - 1).keys()
    else:
        m = perfect_power(q)
        if not m:
            return False
        q, e = m
        if not isprime(q):
            return False
        group_order = q**(e - 1)*(q - 1)
        factors = set(factorint(q - 1).keys())
        factors.add(q)
    return all(pow(a, group_order // prime, p) != 1 for prime in factors)


def _sqrt_mod_tonelli_shanks(a, p):
    """
    Returns the square root in the case of ``p`` prime with ``p == 1 (mod 8)``

    References
    ==========

    .. [1] R. Crandall and C. Pomerance "Prime Numbers", 2nt Ed., page 101

    """
    s = trailing(p - 1)
    t = p >> s
    # find a non-quadratic residue
    while 1:
        d = randint(2, p - 1)
        r = jacobi(d, p)
        if r == -1:
            break
    #assert legendre_symbol(d, p) == -1
    A = pow(a, t, p)
    D = pow(d, t, p)
    m = 0
    for i in range(s):
        adm = A*pow(D, m, p) % p
        adm = pow(adm, 2**(s - 1 - i), p)
        if adm % p == p - 1:
            m += 2**i
    #assert A*pow(D, m, p) % p == 1
    x = pow(a, (t + 1)//2, p)*pow(D, m//2, p) % p
    return x


def sqrt_mod(a, p, all_roots=False):
    """
    Find a root of ``x**2 = a mod p``.

    Parameters
    ==========

    a : integer
    p : positive integer
    all_roots : if True the list of roots is returned or None

    Notes
    =====

    If there is no root it is returned None; else the returned root
    is less or equal to ``p // 2``; in general is not the smallest one.
    It is returned ``p // 2`` only if it is the only root.

    Use ``all_roots`` only when it is expected that all the roots fit
    in memory; otherwise use ``sqrt_mod_iter``.

    Examples
    ========

    >>> from sympy.ntheory import sqrt_mod
    >>> sqrt_mod(11, 43)
    21
    >>> sqrt_mod(17, 32, True)
    [7, 9, 23, 25]
    """
    if all_roots:
        return sorted(sqrt_mod_iter(a, p))
    try:
        p = abs(as_int(p))
        it = sqrt_mod_iter(a, p)
        r = next(it)
        if r > p // 2:
            return p - r
        elif r < p // 2:
            return r
        else:
            try:
                r = next(it)
                if r > p // 2:
                    return p - r
            except StopIteration:
                pass
            return r
    except StopIteration:
        return None


def _product(*iters):
    """
    Cartesian product generator

    Notes
    =====

    Unlike itertools.product, it works also with iterables which do not fit
    in memory. See https://bugs.python.org/issue10109

    Author: Fernando Sumudu
    with small changes
    """
    inf_iters = tuple(cycle(enumerate(it)) for it in iters)
    num_iters = len(inf_iters)
    cur_val = [None]*num_iters

    first_v = True
    while True:
        i, p = 0, num_iters
        while p and not i:
            p -= 1
            i, cur_val[p] = next(inf_iters[p])

        if not p and not i:
            if first_v:
                first_v = False
            else:
                break

        yield cur_val


def sqrt_mod_iter(a, p, domain=int):
    """
    Iterate over solutions to ``x**2 = a mod p``.

    Parameters
    ==========

    a : integer
    p : positive integer
    domain : integer domain, ``int``, ``ZZ`` or ``Integer``

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import sqrt_mod_iter
    >>> list(sqrt_mod_iter(11, 43))
    [21, 22]
    """
    a, p = as_int(a), abs(as_int(p))
    if isprime(p):
        a = a % p
        if a == 0:
            res = _sqrt_mod1(a, p, 1)
        else:
            res = _sqrt_mod_prime_power(a, p, 1)
        if res:
            if domain is ZZ:
                for x in res:
                    yield ZZ(x)
            else:
                for x in res:
                    yield domain(x)
    else:
        f = factorint(p)
        v = []
        pv = []
        for px, ex in f.items():
            if a % px == 0:
                rx = _sqrt_mod1(a, px, ex)
                if not rx:
                    return
            else:
                rx = _sqrt_mod_prime_power(a, px, ex)
                if not rx:
                    return
            v.append(rx)
            pv.append(px**ex)
        mm, e, s = gf_crt1(pv, ZZ)
        if domain is ZZ:
            for vx in _product(*v):
                r = gf_crt2(vx, pv, mm, e, s, ZZ)
                yield r
        else:
            for vx in _product(*v):
                r = gf_crt2(vx, pv, mm, e, s, ZZ)
                yield domain(r)


def _sqrt_mod_prime_power(a, p, k):
    """
    Find the solutions to ``x**2 = a mod p**k`` when ``a % p != 0``.
    If no solution exists, return ``None``.
    Solutions are returned in an ascending list.

    Parameters
    ==========

    a : integer
    p : prime number
    k : positive integer

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import _sqrt_mod_prime_power
    >>> _sqrt_mod_prime_power(11, 43, 1)
    [21, 22]

    References
    ==========

    .. [1] P. Hackman "Elementary Number Theory" (2009), page 160
    .. [2] http://www.numbertheory.org/php/squareroot.html
    .. [3] [Gathen99]_
    """
    pk = p**k
    a = a % pk

    if p == 2:
        # see Ref.[2]
        if a % 8 != 1:
            return None
        # Trivial
        if k <= 3:
            return list(range(1, pk, 2))
        r = 1
        # r is one of the solutions to x**2 - a = 0 (mod 2**3).
        # Hensel lift them to solutions of x**2 - a = 0 (mod 2**k)
        # if r**2 - a = 0 mod 2**nx but not mod 2**(nx+1)
        # then r + 2**(nx - 1) is a root mod 2**(nx+1)
        for nx in range(3, k):
            if ((r**2 - a) >> nx) % 2:
                r += 1 << (nx - 1)
        # r is a solution of x**2 - a = 0 (mod 2**k), and
        # there exist other solutions -r, r+h, -(r+h), and these are all solutions.
        h = 1 << (k - 1)
        return sorted([r, pk - r, (r + h) % pk, -(r + h) % pk])

    # If the Legendre symbol (a/p) is not 1, no solution exists.
    if jacobi(a, p) != 1:
        return None
    if p % 4 == 3:
        res = pow(a, (p + 1) // 4, p)
    elif p % 8 == 5:
        res = pow(a, (p + 3) // 8, p)
        if pow(res, 2, p) != a % p:
            res = res * pow(2, (p - 1) // 4, p) % p
    else:
        res = _sqrt_mod_tonelli_shanks(a, p)
    if k > 1:
        # Hensel lifting with Newton iteration, see Ref.[3] chapter 9
        # with f(x) = x**2 - a; one has f'(a) != 0 (mod p) for p != 2
        px = p
        for _ in range(k.bit_length() - 1):
            px = px**2
            frinv = invert(2*res, px)
            res = (res - (res**2 - a)*frinv) % px
        if k & (k - 1): # If k is not a power of 2
            frinv = invert(2*res, pk)
            res = (res - (res**2 - a)*frinv) % pk
    return sorted([res, pk - res])


def _sqrt_mod1(a, p, n):
    """
    Find solution to ``x**2 == a mod p**n`` when ``a % p == 0``.
    If no solution exists, return ``None``.

    Parameters
    ==========

    a : integer
    p : prime number, p must divide a
    n : positive integer

    References
    ==========

    .. [1] http://www.numbertheory.org/php/squareroot.html
    """
    pn = p**n
    a = a % pn
    if a == 0:
        # case gcd(a, p**k) = p**n
        return range(0, pn, p**((n + 1) // 2))
    # case gcd(a, p**k) = p**r, r < n
    r = multiplicity(p, a)
    if r % 2 == 1:
        return None
    res = _sqrt_mod_prime_power(a // p**r, p, n - r)
    if res is None:
        return None
    m = r // 2
    return (x for rx in res for x in range(rx*p**m, pn, p**(n - m)))


def is_quad_residue(a, p):
    """
    Returns True if ``a`` (mod ``p``) is in the set of squares mod ``p``,
    i.e a % p in set([i**2 % p for i in range(p)]).

    Examples
    ========

    If ``p`` is an odd
    prime, an iterative method is used to make the determination:

    >>> from sympy.ntheory import is_quad_residue
    >>> sorted(set([i**2 % 7 for i in range(7)]))
    [0, 1, 2, 4]
    >>> [j for j in range(7) if is_quad_residue(j, 7)]
    [0, 1, 2, 4]

    See Also
    ========

    legendre_symbol, jacobi_symbol
    """
    a, p = as_int(a), as_int(p)
    if p < 1:
        raise ValueError('p must be > 0')
    if a >= p or a < 0:
        a = a % p
    if a < 2 or p < 3:
        return True
    if not isprime(p):
        if p % 2 and jacobi(a, p) == -1:
            return False
        r = sqrt_mod(a, p)
        if r is None:
            return False
        else:
            return True

    return pow(a, (p - 1) // 2, p) == 1


def is_nthpow_residue(a, n, m):
    """
    Returns True if ``x**n == a (mod m)`` has solutions.

    References
    ==========

    .. [1] P. Hackman "Elementary Number Theory" (2009), page 76

    """
    a = a % m
    a, n, m = as_int(a), as_int(n), as_int(m)
    if m <= 0:
        raise ValueError('m must be > 0')
    if n < 0:
        raise ValueError('n must be >= 0')
    if n == 0:
        if m == 1:
            return False
        return a == 1
    if a == 0:
        return True
    if n == 1:
        return True
    if n == 2:
        return is_quad_residue(a, m)
    return all(_is_nthpow_residue_bign_prime_power(a, n, p, e)
               for p, e in factorint(m).items())


def _is_nthpow_residue_bign_prime_power(a, n, p, k):
    r"""
    Returns True if `x^n = a \pmod{p^k}` has solutions for `n > 2`.

    Parameters
    ==========

    a : positive integer
    n : integer, n > 2
    p : prime number
    k : positive integer

    """
    while a % p == 0:
        a %= pow(p, k)
        if not a:
            return True
        mu = multiplicity(p, a)
        if mu % n:
            return False
        a //= pow(p, mu)
        k -= mu
    if p != 2:
        f = p**(k - 1)*(p - 1) # f = totient(p**k)
        return pow(a, f // gcd(f, n), pow(p, k)) == 1
    if n & 1:
        return True
    c = trailing(n)
    return a % pow(2, min(c + 2, k)) == 1


def _nthroot_mod1(s, q, p, all_roots):
    """
    Root of ``x**q = s mod p``, ``p`` prime and ``q`` divides ``p - 1``.
    Assume that the root exists.

    References
    ==========

    .. [1] A. M. Johnston "A Generalized qth Root Algorithm"

    """
    g = primitive_root(p)
    r = s
    for qx, ex in factorint(q).items():
        f = (p - 1) // qx**ex
        while f % qx == 0:
            f //= qx
        z = f*invert(-f, qx)
        x = (1 + z) // qx
        t = discrete_log(p, pow(r, f, p), pow(g, f*qx, p))
        for _ in range(ex):
            # assert t == discrete_log(p, pow(r, f, p), pow(g, f*qx, p))
            r = pow(r, x, p)*pow(g, -z*t % (p - 1), p) % p
            t //= qx
    res = [r]
    h = pow(g, (p - 1) // q, p)
    #assert pow(h, q, p) == 1
    hx = r
    for _ in range(q - 1):
        hx = (hx*h) % p
        res.append(hx)
    if all_roots:
        res.sort()
        return res
    return min(res)


def _help(m, prime_modulo_method, diff_method, expr_val):
    """
    Helper function for _nthroot_mod_composite.

    Parameters
    ==========

    m : positive integer
    prime_modulo_method : function to calculate the root of the congruence
    equation for the prime divisors of m
    diff_method : function to calculate derivative of expression at any
    given point
    expr_val : function to calculate value of the expression at any
    given point
    """
    from sympy.ntheory.modular import crt
    f = factorint(m)
    dd = {}
    for p, e in f.items():
        tot_roots = set()
        if e == 1:
            tot_roots.update(prime_modulo_method(p))
        else:
            for root in prime_modulo_method(p):
                diff = diff_method(root, p)
                if diff != 0:
                    ppow = p
                    m_inv = invert(diff, p)
                    for j in range(1, e):
                        ppow *= p
                        root = (root - expr_val(root, ppow) * m_inv) % ppow
                    tot_roots.add(root)
                else:
                    new_base = p
                    roots_in_base = {root}
                    while new_base < pow(p, e):
                        new_base *= p
                        new_roots = set()
                        for k in roots_in_base:
                            if expr_val(k, new_base)!= 0:
                                continue
                            while k not in new_roots:
                                new_roots.add(k)
                                k = (k + (new_base // p)) % new_base
                        roots_in_base = new_roots
                    tot_roots = tot_roots | roots_in_base
        if tot_roots == set():
            return []
        dd[pow(p, e)] = tot_roots
    a = []
    m = []
    for x, y in dd.items():
        m.append(x)
        a.append(list(y))
    return sorted({crt(m, list(i))[0] for i in product(*a)})


def _nthroot_mod_composite(a, n, m):
    """
    Find the solutions to ``x**n = a mod m`` when m is not prime.
    """
    return _help(m,
        lambda p: nthroot_mod(a, n, p, True),
        lambda root, p: (pow(root, n - 1, p) * (n % p)) % p,
        lambda root, p: (pow(root, n, p) - a) % p)


def nthroot_mod(a, n, p, all_roots=False):
    """
    Find the solutions to ``x**n = a mod p``.

    Parameters
    ==========

    a : integer
    n : positive integer
    p : positive integer
    all_roots : if False returns the smallest root, else the list of roots

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import nthroot_mod
    >>> nthroot_mod(11, 4, 19)
    8
    >>> nthroot_mod(11, 4, 19, True)
    [8, 11]
    >>> nthroot_mod(68, 3, 109)
    23
    """
    a = a % p
    a, n, p = as_int(a), as_int(n), as_int(p)

    if n == 2:
        return sqrt_mod(a, p, all_roots)
    # see Hackman "Elementary Number Theory" (2009), page 76
    if not isprime(p):
        return _nthroot_mod_composite(a, n, p)
    if a % p == 0:
        return [0]
    if not is_nthpow_residue(a, n, p):
        return [] if all_roots else None
    if (p - 1) % n == 0:
        return _nthroot_mod1(a, n, p, all_roots)
    # The roots of ``x**n - a = 0 (mod p)`` are roots of
    # ``gcd(x**n - a, x**(p - 1) - 1) = 0 (mod p)``
    pa = n
    pb = p - 1
    b = 1
    if pa < pb:
        a, pa, b, pb = b, pb, a, pa
    while pb:
        # x**pa - a = 0; x**pb - b = 0
        # x**pa - a = x**(q*pb + r) - a = (x**pb)**q * x**r - a =
        #             b**q * x**r - a; x**r - c = 0; c = b**-q * a mod p
        q, r = divmod(pa, pb)
        c = pow(b, -q, p) * a % p
        pa, pb = pb, r
        a, b = b, c
    if pa == 1:
        if all_roots:
            res = [a]
        else:
            res = a
    elif pa == 2:
        return sqrt_mod(a, p, all_roots)
    else:
        res = _nthroot_mod1(a, pa, p, all_roots)
    return res


def quadratic_residues(p) -> list[int]:
    """
    Returns the list of quadratic residues.

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import quadratic_residues
    >>> quadratic_residues(7)
    [0, 1, 2, 4]
    """
    p = as_int(p)
    r = {pow(i, 2, p) for i in range(p // 2 + 1)}
    return sorted(r)


def legendre_symbol(a, p):
    r"""
    Returns the Legendre symbol `(a / p)`.

    For an integer ``a`` and an odd prime ``p``, the Legendre symbol is
    defined as

    .. math ::
        \genfrac(){}{}{a}{p} = \begin{cases}
             0 & \text{if } p \text{ divides } a\\
             1 & \text{if } a \text{ is a quadratic residue modulo } p\\
            -1 & \text{if } a \text{ is a quadratic nonresidue modulo } p
        \end{cases}

    Parameters
    ==========

    a : integer
    p : odd prime

    Examples
    ========

    >>> from sympy.ntheory import legendre_symbol
    >>> [legendre_symbol(i, 7) for i in range(7)]
    [0, 1, 1, -1, 1, -1, -1]
    >>> sorted(set([i**2 % 7 for i in range(7)]))
    [0, 1, 2, 4]

    See Also
    ========

    is_quad_residue, jacobi_symbol

    """
    a, p = as_int(a), as_int(p)
    if p == 2 or not isprime(p):
        raise ValueError("p should be an odd prime")
    return int(legendre(a, p))


def jacobi_symbol(m, n):
    r"""
    Returns the Jacobi symbol `(m / n)`.

    For any integer ``m`` and any positive odd integer ``n`` the Jacobi symbol
    is defined as the product of the Legendre symbols corresponding to the
    prime factors of ``n``:

    .. math ::
        \genfrac(){}{}{m}{n} =
            \genfrac(){}{}{m}{p^{1}}^{\alpha_1}
            \genfrac(){}{}{m}{p^{2}}^{\alpha_2}
            ...
            \genfrac(){}{}{m}{p^{k}}^{\alpha_k}
            \text{ where } n =
                p_1^{\alpha_1}
                p_2^{\alpha_2}
                ...
                p_k^{\alpha_k}

    Like the Legendre symbol, if the Jacobi symbol `\genfrac(){}{}{m}{n} = -1`
    then ``m`` is a quadratic nonresidue modulo ``n``.

    But, unlike the Legendre symbol, if the Jacobi symbol
    `\genfrac(){}{}{m}{n} = 1` then ``m`` may or may not be a quadratic residue
    modulo ``n``.

    Parameters
    ==========

    m : integer
    n : odd positive integer

    Examples
    ========

    >>> from sympy.ntheory import jacobi_symbol, legendre_symbol
    >>> from sympy import S
    >>> jacobi_symbol(45, 77)
    -1
    >>> jacobi_symbol(60, 121)
    1

    The relationship between the ``jacobi_symbol`` and ``legendre_symbol`` can
    be demonstrated as follows:

    >>> L = legendre_symbol
    >>> S(45).factors()
    {3: 2, 5: 1}
    >>> jacobi_symbol(7, 45) == L(7, 3)**2 * L(7, 5)**1
    True

    See Also
    ========

    is_quad_residue, legendre_symbol
    """
    m, n = as_int(m), as_int(n)
    return int(jacobi(m, n))


class mobius(Function):
    """
    Mobius function maps natural number to {-1, 0, 1}

    It is defined as follows:
        1) `1` if `n = 1`.
        2) `0` if `n` has a squared prime factor.
        3) `(-1)^k` if `n` is a square-free positive integer with `k`
           number of prime factors.

    It is an important multiplicative function in number theory
    and combinatorics.  It has applications in mathematical series,
    algebraic number theory and also physics (Fermion operator has very
    concrete realization with Mobius Function model).

    Parameters
    ==========

    n : positive integer

    Examples
    ========

    >>> from sympy.ntheory import mobius
    >>> mobius(13*7)
    1
    >>> mobius(1)
    1
    >>> mobius(13*7*5)
    -1
    >>> mobius(13**2)
    0

    References
    ==========

    .. [1] https://en.wikipedia.org/wiki/M%C3%B6bius_function
    .. [2] Thomas Koshy "Elementary Number Theory with Applications"

    """
    @classmethod
    def eval(cls, n):
        if n.is_integer:
            if n.is_positive is not True:
                raise ValueError("n should be a positive integer")
        else:
            raise TypeError("n should be an integer")
        if n.is_prime:
            return S.NegativeOne
        elif n is S.One:
            return S.One
        elif n.is_Integer:
            a = factorint(n)
            if any(i > 1 for i in a.values()):
                return S.Zero
            return S.NegativeOne**len(a)


def _discrete_log_trial_mul(n, a, b, order=None):
    """
    Trial multiplication algorithm for computing the discrete logarithm of
    ``a`` to the base ``b`` modulo ``n``.

    The algorithm finds the discrete logarithm using exhaustive search. This
    naive method is used as fallback algorithm of ``discrete_log`` when the
    group order is very small.

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import _discrete_log_trial_mul
    >>> _discrete_log_trial_mul(41, 15, 7)
    3

    See Also
    ========

    discrete_log

    References
    ==========

    .. [1] "Handbook of applied cryptography", Menezes, A. J., Van, O. P. C., &
        Vanstone, S. A. (1997).
    """
    a %= n
    b %= n
    if order is None:
        order = n
    x = 1
    for i in range(order):
        if x == a:
            return i
        x = x * b % n
    raise ValueError("Log does not exist")


def _discrete_log_shanks_steps(n, a, b, order=None):
    """
    Baby-step giant-step algorithm for computing the discrete logarithm of
    ``a`` to the base ``b`` modulo ``n``.

    The algorithm is a time-memory trade-off of the method of exhaustive
    search. It uses `O(sqrt(m))` memory, where `m` is the group order.

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import _discrete_log_shanks_steps
    >>> _discrete_log_shanks_steps(41, 15, 7)
    3

    See Also
    ========

    discrete_log

    References
    ==========

    .. [1] "Handbook of applied cryptography", Menezes, A. J., Van, O. P. C., &
        Vanstone, S. A. (1997).
    """
    a %= n
    b %= n
    if order is None:
        order = n_order(b, n)
    m = sqrt(order) + 1
    T = {}
    x = 1
    for i in range(m):
        T[x] = i
        x = x * b % n
    z = pow(b, -m, n)
    x = a
    for i in range(m):
        if x in T:
            return i * m + T[x]
        x = x * z % n
    raise ValueError("Log does not exist")


def _discrete_log_pollard_rho(n, a, b, order=None, retries=10, rseed=None):
    """
    Pollard's Rho algorithm for computing the discrete logarithm of ``a`` to
    the base ``b`` modulo ``n``.

    It is a randomized algorithm with the same expected running time as
    ``_discrete_log_shanks_steps``, but requires a negligible amount of memory.

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import _discrete_log_pollard_rho
    >>> _discrete_log_pollard_rho(227, 3**7, 3)
    7

    See Also
    ========

    discrete_log

    References
    ==========

    .. [1] "Handbook of applied cryptography", Menezes, A. J., Van, O. P. C., &
        Vanstone, S. A. (1997).
    """
    a %= n
    b %= n

    if order is None:
        order = n_order(b, n)
    randint = _randint(rseed)

    for i in range(retries):
        aa = randint(1, order - 1)
        ba = randint(1, order - 1)
        xa = pow(b, aa, n) * pow(a, ba, n) % n

        c = xa % 3
        if c == 0:
            xb = a * xa % n
            ab = aa
            bb = (ba + 1) % order
        elif c == 1:
            xb = xa * xa % n
            ab = (aa + aa) % order
            bb = (ba + ba) % order
        else:
            xb = b * xa % n
            ab = (aa + 1) % order
            bb = ba

        for j in range(order):
            c = xa % 3
            if c == 0:
                xa = a * xa % n
                ba = (ba + 1) % order
            elif c == 1:
                xa = xa * xa % n
                aa = (aa + aa) % order
                ba = (ba + ba) % order
            else:
                xa = b * xa % n
                aa = (aa + 1) % order

            c = xb % 3
            if c == 0:
                xb = a * xb % n
                bb = (bb + 1) % order
            elif c == 1:
                xb = xb * xb % n
                ab = (ab + ab) % order
                bb = (bb + bb) % order
            else:
                xb = b * xb % n
                ab = (ab + 1) % order

            c = xb % 3
            if c == 0:
                xb = a * xb % n
                bb = (bb + 1) % order
            elif c == 1:
                xb = xb * xb % n
                ab = (ab + ab) % order
                bb = (bb + bb) % order
            else:
                xb = b * xb % n
                ab = (ab + 1) % order

            if xa == xb:
                r = (ba - bb) % order
                try:
                    e = invert(r, order) * (ab - aa) % order
                    if (pow(b, e, n) - a) % n == 0:
                        return e
                except ZeroDivisionError:
                    pass
                break
    raise ValueError("Pollard's Rho failed to find logarithm")


def _discrete_log_pohlig_hellman(n, a, b, order=None):
    """
    Pohlig-Hellman algorithm for computing the discrete logarithm of ``a`` to
    the base ``b`` modulo ``n``.

    In order to compute the discrete logarithm, the algorithm takes advantage
    of the factorization of the group order. It is more efficient when the
    group order factors into many small primes.

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import _discrete_log_pohlig_hellman
    >>> _discrete_log_pohlig_hellman(251, 210, 71)
    197

    See Also
    ========

    discrete_log

    References
    ==========

    .. [1] "Handbook of applied cryptography", Menezes, A. J., Van, O. P. C., &
        Vanstone, S. A. (1997).
    """
    from .modular import crt
    a %= n
    b %= n

    if order is None:
        order = n_order(b, n)

    f = factorint(order)
    l = [0] * len(f)

    for i, (pi, ri) in enumerate(f.items()):
        for j in range(ri):
            aj = pow(a * pow(b, -l[i], n), order // pi**(j + 1), n)
            bj = pow(b, order // pi, n)
            cj = discrete_log(n, aj, bj, pi, True)
            l[i] += cj * pi**j

    d, _ = crt([pi**ri for pi, ri in f.items()], l)
    return d


def discrete_log(n, a, b, order=None, prime_order=None):
    """
    Compute the discrete logarithm of ``a`` to the base ``b`` modulo ``n``.

    This is a recursive function to reduce the discrete logarithm problem in
    cyclic groups of composite order to the problem in cyclic groups of prime
    order.

    It employs different algorithms depending on the problem (subgroup order
    size, prime order or not):

        * Trial multiplication
        * Baby-step giant-step
        * Pollard's Rho
        * Pohlig-Hellman

    Examples
    ========

    >>> from sympy.ntheory import discrete_log
    >>> discrete_log(41, 15, 7)
    3

    References
    ==========

    .. [1] https://mathworld.wolfram.com/DiscreteLogarithm.html
    .. [2] "Handbook of applied cryptography", Menezes, A. J., Van, O. P. C., &
        Vanstone, S. A. (1997).

    """
    n, a, b = as_int(n), as_int(a), as_int(b)
    if order is None:
        order = n_order(b, n)

    if prime_order is None:
        prime_order = isprime(order)

    if order < 1000:
        return _discrete_log_trial_mul(n, a, b, order)
    elif prime_order:
        if order < 1000000000000:
            return _discrete_log_shanks_steps(n, a, b, order)
        return _discrete_log_pollard_rho(n, a, b, order)

    return _discrete_log_pohlig_hellman(n, a, b, order)



def quadratic_congruence(a, b, c, p):
    """
    Find the solutions to ``a x**2 + b x + c = 0 mod p``.

    Parameters
    ==========

    a : int
    b : int
    c : int
    p : int
        A positive integer.
    """
    a = as_int(a)
    b = as_int(b)
    c = as_int(c)
    p = as_int(p)
    a = a % p
    b = b % p
    c = c % p

    if a == 0:
        return linear_congruence(b, -c, p)
    if p == 2:
        roots = []
        if c % 2 == 0:
            roots.append(0)
        if (a + b + c) % 2 == 0:
            roots.append(1)
        return roots
    if isprime(p):
        inv_a = invert(a, p)
        b *= inv_a
        c *= inv_a
        if b % 2 == 1:
            b = b + p
        d = ((b * b) // 4 - c) % p
        y = sqrt_mod(d, p, all_roots=True)
        res = set()
        for i in y:
            res.add((i - b // 2) % p)
        return sorted(res)
    y = sqrt_mod(b * b - 4 * a * c, 4 * a * p, all_roots=True)
    res = set()
    for i in y:
        root = linear_congruence(2 * a, i - b, 4 * a * p)
        for j in root:
            res.add(j % p)
    return sorted(res)


def _valid_expr(expr):
    """
    return coefficients of expr if it is a univariate polynomial
    with integer coefficients else raise a ValueError.
    """

    if not expr.is_polynomial():
        raise ValueError("The expression should be a polynomial")
    polynomial = Poly(expr)
    if not polynomial.is_univariate:
        raise ValueError("The expression should be univariate")
    if not polynomial.domain == ZZ:
        raise ValueError("The expression should should have integer coefficients")
    return polynomial.all_coeffs()


def polynomial_congruence(expr, m):
    """
    Find the solutions to a polynomial congruence equation modulo m.

    Parameters
    ==========

    coefficients : Coefficients of the Polynomial
    m : positive integer

    Examples
    ========

    >>> from sympy.ntheory import polynomial_congruence
    >>> from sympy.abc import x
    >>> expr = x**6 - 2*x**5 -35
    >>> polynomial_congruence(expr, 6125)
    [3257]

    See Also
    ========

    sympy.polys.galoistools.gf_csolve : low level solving routine used by this routine

    """
    coefficients = _valid_expr(expr)
    coefficients = [num % m for num in coefficients]
    rank = len(coefficients)
    if rank == 3:
        return quadratic_congruence(*coefficients, m)
    if rank == 2:
        return quadratic_congruence(0, *coefficients, m)
    if coefficients[0] == 1 and 1 + coefficients[-1] == sum(coefficients):
        return nthroot_mod(-coefficients[-1], rank - 1, m, True)
    return gf_csolve(coefficients, m)


def binomial_mod(n, m, k):
    """Compute ``binomial(n, m) % k``.

    Explanation
    ===========

    Returns ``binomial(n, m) % k`` using a generalization of Lucas'
    Theorem for prime powers given by Granville [1]_, in conjunction with
    the Chinese Remainder Theorem.  The residue for each prime power
    is calculated in time O(log^2(n) + q^4*log(n)log(p) + q^4*p*log^3(p)).

    Parameters
    ==========

    n : an integer
    m : an integer
    k : a positive integer

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import binomial_mod
    >>> binomial_mod(10, 2, 6)  # binomial(10, 2) = 45
    3
    >>> binomial_mod(17, 9, 10)  # binomial(17, 9) = 24310
    0

    References
    ==========

    .. [1] Binomial coefficients modulo prime powers, Andrew Granville,
        Available: https://web.archive.org/web/20170202003812/http://www.dms.umontreal.ca/~andrew/PDF/BinCoeff.pdf
    """
    if k < 1: raise ValueError('k is required to be positive')
    # We decompose q into a product of prime powers and apply
    # the generalization of Lucas' Theorem given by Granville
    # to obtain binomial(n, k) mod p^e, and then use the Chinese
    # Remainder Theorem to obtain the result mod q
    if n < 0 or m < 0 or m > n: return 0
    factorisation = factorint(k)
    residues = [_binomial_mod_prime_power(n, m, p, e) for p, e in factorisation.items()]
    return crt([p**pw for p, pw in factorisation.items()], residues, check=False)[0]


def _binomial_mod_prime_power(n, m, p, q):
    """Compute ``binomial(n, m) % p**q`` for a prime ``p``.

    Parameters
    ==========

    n : positive integer
    m : a nonnegative integer
    p : a prime
    q : a positive integer (the prime exponent)

    Examples
    ========

    >>> from sympy.ntheory.residue_ntheory import _binomial_mod_prime_power
    >>> _binomial_mod_prime_power(10, 2, 3, 2)  # binomial(10, 2) = 45
    0
    >>> _binomial_mod_prime_power(17, 9, 2, 4)  # binomial(17, 9) = 24310
    6

    References
    ==========

    .. [1] Binomial coefficients modulo prime powers, Andrew Granville,
        Available: https://web.archive.org/web/20170202003812/http://www.dms.umontreal.ca/~andrew/PDF/BinCoeff.pdf
    """
    # Function/variable naming within this function follows Ref.[1]
    # n!_p will be used to denote the product of integers <= n not divisible by
    # p, with binomial(n, m)_p the same as binomial(n, m), but defined using
    # n!_p in place of n!
    modulo = pow(p, q)

    def up_factorial(u):
        """Compute (u*p)!_p modulo p^q."""
        r = q // 2
        fac = prod = 1
        if r == 1 and p == 2 or 2*r + 1 in (p, p*p):
            if q % 2 == 1: r += 1
            modulo, div = pow(p, 2*r), pow(p, 2*r - q)
        else:
            modulo, div = pow(p, 2*r + 1), pow(p, (2*r + 1) - q)
        for j in range(1, r + 1):
            for mul in range((j - 1)*p + 1, j*p):  # ignore jp itself
                fac *= mul
                fac %= modulo
            bj_ = bj(u, j, r)
            prod *= pow(fac, bj_, modulo)
            prod %= modulo
        if p == 2:
            sm = u // 2
            for j in range(1, r + 1): sm += j//2 * bj(u, j, r)
            if sm % 2 == 1: prod *= -1
        prod %= modulo//div
        return prod % modulo

    def bj(u, j, r):
        """Compute the exponent of (j*p)!_p in the calculation of (u*p)!_p."""
        prod = u
        for i in range(1, r + 1):
            if i != j: prod *= u*u - i*i
        for i in range(1, r + 1):
            if i != j: prod //= j*j - i*i
        return prod // j

    def up_plus_v_binom(u, v):
        """Compute binomial(u*p + v, v)_p modulo p^q."""
        prod = div = 1
        for i in range(1, v + 1):
            div *= i
            div %= modulo
        div = invert(div, modulo)
        for j in range(1, q):
            b = div
            for v_ in range(j*p + 1, j*p + v + 1):
                b *= v_
                b %= modulo
            aj = u
            for i in range(1, q):
                if i != j: aj *= u - i
            for i in range(1, q):
                if i != j: aj //= j - i
            aj //= j
            prod *= pow(b, aj, modulo)
            prod %= modulo
        return prod

    factorials = [1]
    def factorial(v):
        """Compute v! modulo p^q."""
        if len(factorials) <= v:
            for i in range(len(factorials), v + 1):
                factorials.append(factorials[-1]*i % modulo)
        return factorials[v]

    def factorial_p(n):
        """Compute n!_p modulo p^q."""
        u, v = divmod(n, p)
        return (factorial(v) * up_factorial(u) * up_plus_v_binom(u, v)) % modulo

    prod = 1
    Nj, Mj, Rj = n, m, n - m
    # e0 will be the p-adic valuation of binomial(n, m) at p
    e0 = carry = eq_1 = j = 0
    while Nj:
        numerator = factorial_p(Nj % modulo)
        denominator = factorial_p(Mj % modulo) * factorial_p(Rj % modulo) % modulo
        Nj, (Mj, mj), (Rj, rj) = Nj//p, divmod(Mj, p), divmod(Rj, p)
        carry = (mj + rj + carry) // p
        e0 += carry
        if j >= q - 1: eq_1 += carry
        prod *= numerator * invert(denominator, modulo)
        prod %= modulo
        j += 1

    mul = pow(1 if p == 2 and q >= 3 else -1, eq_1, modulo)
    return (pow(p, e0, modulo) * mul * prod) % modulo
