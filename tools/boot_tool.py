#!/usr/bin/env python3
"""
boot_tool.py — recovery-as-boot helper for Blackview BV7100 (MT6769, boot header v2).

On this phone ONE boot ramdisk serves both OrangeFox and the normal Android boot.
A ramdisk taken straight from a TWRP/OrangeFox build loses the stock
/first_stage_ramdisk (fstab + snapuserd for Virtual A/B), and Android no longer
boots. This tool therefore:

  * keeps the STOCK kernel, dtb, header, addresses and cmdline untouched,
  * takes the OrangeFox ramdisk,
  * replaces its /first_stage_ramdisk with the STOCK one (byte-identical),
  * compresses with gzip (the stock kernel only has CONFIG_RD_GZIP),
  * refuses to write an image that does not fit the boot partition.

Commands:
  info    <boot.img>
  inject  <stock_boot.img> <orangefox_boot.img | ramdisk(.cpio|.gz|.lz4)> <out.img>
"""
import gzip
import hashlib
import os
import struct
import sys
import zlib

KEEP_FROM_STOCK = ('first_stage_ramdisk',)
PART_SIZE = int(os.environ.get('BOOT_PARTITION_SIZE', '33554432'))


def align(x, a):
    return (x + a - 1) // a * a


class Boot:
    def __init__(self, data):
        if data[:8] != b'ANDROID!':
            raise SystemExit('not an Android boot image')
        (self.kernel_size, self.kernel_addr, self.ramdisk_size, self.ramdisk_addr,
         self.second_size, self.second_addr, self.tags_addr, self.page_size,
         self.version, self.os_version) = struct.unpack_from('<10I', data, 8)
        if self.version > 2:
            raise SystemExit('header v%d not handled here' % self.version)
        self.name = data[48:64]
        self.cmdline = data[64:576]
        self.extra_cmdline = data[608:1632]
        self.recovery_dtbo_size, self.recovery_dtbo_offset, self.header_size = 0, 0, 0
        self.dtb_size, self.dtb_addr = 0, 0
        if self.version >= 1:
            self.recovery_dtbo_size, self.recovery_dtbo_offset, self.header_size = struct.unpack_from('<IQI', data, 1632)
        if self.version >= 2:
            self.dtb_size, self.dtb_addr = struct.unpack_from('<IQ', data, 1648)
        pg = self.page_size
        o = pg
        self.kernel = data[o:o + self.kernel_size]; o += align(self.kernel_size, pg)
        self.ramdisk = data[o:o + self.ramdisk_size]; o += align(self.ramdisk_size, pg)
        self.second = data[o:o + self.second_size]; o += align(self.second_size, pg)
        self.recovery_dtbo = data[o:o + self.recovery_dtbo_size]; o += align(self.recovery_dtbo_size, pg)
        self.dtb = data[o:o + self.dtb_size]; o += align(self.dtb_size, pg)
        self.payload_end = o
        self.raw_header = bytearray(data[:pg])

    def build(self, ramdisk):
        pg = self.page_size
        h = self.raw_header
        struct.pack_into('<I', h, 16, len(ramdisk))
        sha = hashlib.sha1()
        for blob in (self.kernel, ramdisk, self.second):
            sha.update(blob); sha.update(struct.pack('<I', len(blob)))
        if self.version >= 1:
            sha.update(self.recovery_dtbo); sha.update(struct.pack('<I', len(self.recovery_dtbo)))
        if self.version >= 2:
            sha.update(self.dtb); sha.update(struct.pack('<I', len(self.dtb)))
        h[576:608] = sha.digest().ljust(32, b'\0')
        out = bytearray(h)
        for blob in (self.kernel, ramdisk, self.second, self.recovery_dtbo, self.dtb):
            out += blob + b'\0' * (align(len(blob), pg) - len(blob))
        return bytes(out)


def decompress(blob):
    if blob[:2] == b'\x1f\x8b':
        return gzip.decompress(blob)
    if blob[:4] == b'\x02\x21\x4c\x18':          # lz4 legacy
        import lz4.block
        o, out = 4, bytearray()
        while o + 4 <= len(blob):
            n, = struct.unpack_from('<I', blob, o)
            if n == 0x184C2102:
                o += 4; continue
            o += 4
            out += lz4.block.decompress(blob[o:o + n], uncompressed_size=8 << 20)
            o += n
        return bytes(out)
    if blob[:6] == b'070701':
        return blob
    if blob[:3] == b'\x5d\x00\x00':             # legacy .lzma (lzma_alone)
        import lzma
        return lzma.decompress(blob, format=lzma.FORMAT_ALONE)
    raise SystemExit('unknown ramdisk compression: %s' % blob[:6].hex())


def cpio_parse(d):
    """Return list of (name, header_fields(list of 13 ints), data) in newc format."""
    out, o = [], 0
    while o + 110 <= len(d):
        if d[o:o + 6] != b'070701':
            raise SystemExit('bad cpio magic at %d' % o)
        f = [int(d[o + 6 + i * 8:o + 14 + i * 8], 16) for i in range(13)]
        nsize, fsize = f[11], f[6]
        name = d[o + 110:o + 110 + nsize - 1].decode()
        p = align(o + 110 + nsize, 4)
        data = d[p:p + fsize]
        o = align(p + fsize, 4)
        if name == 'TRAILER!!!':
            break
        out.append((name, f, data))
    return out


def cpio_write(entries):
    out = bytearray()
    ino = 300000
    for name, f, data in entries + [('TRAILER!!!', [0] * 13, b'')]:
        f = list(f)
        if name != 'TRAILER!!!':
            ino += 1
            f[0] = ino
        f[4] = f[4] if name != 'TRAILER!!!' else 1   # nlink
        f[6] = len(data)
        f[11] = len(name.encode()) + 1
        hdr = b'070701' + b''.join(b'%08X' % v for v in f)
        out += hdr + name.encode() + b'\0'
        out += b'\0' * (align(len(out), 4) - len(out))
        out += data
        out += b'\0' * (align(len(out), 4) - len(out))
    out += b'\0' * (align(len(out), 512) - len(out))
    return bytes(out)


def norm(n):
    return n[2:] if n.startswith('./') else n.lstrip('/')


def under(name, roots):
    n = norm(name)
    return any(n == r or n.startswith(r + '/') for r in roots)


# ---------------------------------------------------------------- ramdisk trimming
#
# The BV7100 boot partition is 32 MiB and the stock kernel alone takes ~11 MB, so
# the full OrangeFox ramdisk (gzip ~33 MB) does not fit. trim() removes things that
# are not needed on this phone, as listed in ramdisk_trim.txt:
#   rm   <glob>            delete matching files/links
#   keep <glob>            exception for rm
#   link <glob> <target>   replace a file by a symlink (e.g. optional fonts -> Roboto)
# then removes libraries that were used ONLY by deleted programs, checks that every
# remaining program still finds all its libraries, strips symbol tables/mini-debuginfo
# from OrangeFox's own ELF files (never vendor blobs, init or linker) and fixes
# ramdisk-files.txt/.sha256sum (OrangeFox uses them to re-pack itself).

import fnmatch
import stat as statmod
import subprocess
import tempfile

LIB_DIRS = ('system/lib64', 'vendor/lib64', 'system/lib64/hw', 'vendor/lib64/hw',
            'system/lib64/bootstrap', 'apex/com.android.runtime/lib64/bionic')


def elf_needed(data):
    """DT_NEEDED names of an ELF64 little-endian file, or None for non-ELF."""
    if data[:4] != b'\x7fELF' or data[4] != 2 or data[5] != 1:
        return None
    phoff, = struct.unpack_from('<Q', data, 32)
    phentsize, phnum = struct.unpack_from('<HH', data, 54)
    loads, dyn = [], None
    for i in range(phnum):
        p_type, _f, p_off, p_vaddr, _pa, p_filesz, _ms, _al = struct.unpack_from('<IIQQQQQQ', data, phoff + i * phentsize)
        if p_type == 1:
            loads.append((p_vaddr, p_off, p_filesz))
        elif p_type == 2:
            dyn = (p_off, p_filesz)
    if not dyn:
        return []
    needed, strtab = [], None
    for o in range(dyn[0], dyn[0] + dyn[1], 16):
        tag, val = struct.unpack_from('<qQ', data, o)
        if tag == 0:
            break
        if tag == 1:
            needed.append(val)
        elif tag == 5:
            strtab = val
    if strtab is None:
        return []
    for va, off, sz in loads:
        if va <= strtab < va + sz:
            base = strtab - va + off
            break
    else:
        return []
    return [data[base + n:data.index(b'\0', base + n)].decode() for n in needed]


def is_reg(f):
    return statmod.S_ISREG(f[1])


def is_lnk(f):
    return statmod.S_ISLNK(f[1])


def provided_libs(entries):
    return {os.path.basename(norm(n)) for n, f, d in entries
            if (is_reg(f) or is_lnk(f)) and os.path.dirname(norm(n)) in LIB_DIRS}


def unresolved(entries):
    have = provided_libs(entries)
    bad = {}
    for n, f, d in entries:
        if is_reg(f):
            nd = elf_needed(d)
            for lib in nd or ():
                if lib not in have:
                    bad.setdefault(lib, []).append(norm(n))
    return bad


def needed_by(entries):
    users = {}
    for n, f, d in entries:
        if is_reg(f):
            for lib in elf_needed(d) or ():
                users.setdefault(lib, set()).add(norm(n))
    return users


def gzsize(b):
    return len(gzip.compress(b, 6))


def trim(entries, rules_path, log):
    rules = []
    for line in open(rules_path):
        line = line.split('#', 1)[0].split()
        if line:
            rules.append(line)
    keep = [r[1] for r in rules if r[0] == 'keep']
    rm = [r[1] for r in rules if r[0] == 'rm']
    links = [(r[1], r[2]) for r in rules if r[0] == 'link']
    before_users = needed_by(entries)
    before_bad = unresolved(entries)
    out, removed, saved = [], [], 0
    for n, f, d in entries:
        p = norm(n)
        if any(fnmatch.fnmatch(p, g) for g in rm) and not any(fnmatch.fnmatch(p, g) for g in keep):
            removed.append(p); saved += gzsize(d) if is_reg(f) else 0
            continue
        for g, target in links:
            if is_reg(f) and fnmatch.fnmatch(p, g) and os.path.basename(p) != os.path.basename(target):
                saved += gzsize(d)
                f = list(f); f[1] = statmod.S_IFLNK | 0o777
                d = target.encode()
                log('link  %s -> %s' % (p, target))
                break
        out.append((n, f, d))
    for p in removed:
        log('rm    %s' % p)
    # libraries that only deleted programs used
    while True:
        users = needed_by(out)
        orphans = {os.path.basename(norm(n)) for n, f, d in out
                   if is_reg(f) and os.path.dirname(norm(n)) in ('system/lib64',)
                   and os.path.basename(norm(n)) in before_users
                   and not users.get(os.path.basename(norm(n)))}
        if not orphans:
            break
        nxt = []
        for n, f, d in out:
            if os.path.dirname(norm(n)) == 'system/lib64' and os.path.basename(norm(n)) in orphans:
                log('orphan %s (only used by removed files)' % norm(n)); saved += gzsize(d); removed.append(norm(n))
            else:
                nxt.append((n, f, d))
        out = nxt
    after_bad = unresolved(out)
    new_bad = {k: v for k, v in after_bad.items() if k not in before_bad}
    if new_bad:
        raise SystemExit('trim broke library dependencies: %s' % new_bad)
    log('trim: removed %d entries, ~%d KB gzip saved' % (len(removed), saved // 1024))
    return out, set(removed)


STRIP_SKIP = ('first_stage_ramdisk/*', 'vendor/*', 'odm/*', 'system/bin/init', 'system/bin/linker*',
              'system/lib64/bootstrap/*')


def strip_elfs(entries, objcopy, log):
    if not objcopy:
        log('strip: skipped (no OBJCOPY)')
        return entries
    out, saved = [], 0
    with tempfile.TemporaryDirectory() as td:
        src, dst = os.path.join(td, 'in'), os.path.join(td, 'out')
        for n, f, d in entries:
            p = norm(n)
            if is_reg(f) and d[:4] == b'\x7fELF' and not any(fnmatch.fnmatch(p, g) for g in STRIP_SKIP):
                open(src, 'wb').write(d)
                r = subprocess.run([objcopy, '--strip-all', '--remove-section=.gnu_debugdata', src, dst],
                                   capture_output=True)
                if r.returncode == 0:
                    nd = open(dst, 'rb').read()
                    if elf_needed(nd) == elf_needed(d) and len(nd) <= len(d):
                        saved += len(d) - len(nd)
                        d = nd
                else:
                    log('strip failed for %s: %s' % (p, r.stderr.decode(errors='replace').strip()[:200]))
            out.append((n, f, d))
    log('strip: %d KB of symbols/debug data removed' % (saved // 1024))
    return out


def fix_file_lists(entries, removed):
    """Keep OrangeFox's ramdisk-files.txt / .sha256sum consistent (it re-packs itself from them)."""
    names = [norm(n) for n, f, d in entries]
    present = set(names)
    data = {norm(n): d for n, f, d in entries if is_reg(f)}
    out = []
    for n, f, d in entries:
        p = norm(n)
        if p == 'ramdisk-files.txt':
            lines = [l for l in d.decode().splitlines() if l.strip()]
            lines = [l for l in lines if norm(l) in present or l.strip() == '.']
            listed = {norm(l) for l in lines}
            lines += [x for x in names if x not in listed and x != 'ramdisk-files.txt']
            d = ('\n'.join(lines) + '\n').encode()
        elif p == 'ramdisk-files.sha256sum':
            res = []
            for l in d.decode().splitlines():
                parts = l.split(None, 1)
                if len(parts) == 2 and norm(parts[1].strip()) in data:
                    q = norm(parts[1].strip())
                    res.append('%s  ./%s' % (hashlib.sha256(data[q]).hexdigest(), q))
            d = ('\n'.join(res) + '\n').encode()
        out.append((n, f, d))
    return out


def compress(cpio):
    # RD_COMP=lzma only for kernels with CONFIG_RD_LZMA. The BV7100 kernel has gzip only
    # (an lzma ramdisk hangs on the boot logo), so the CI uses zopfli-gzip
    if os.environ.get('RD_COMP') == 'lzma':
        import lzma
        filt = [{'id': lzma.FILTER_LZMA1, 'preset': 9 | lzma.PRESET_EXTREME, 'dict_size': 16 << 20}]
        return lzma.compress(cpio, format=lzma.FORMAT_ALONE, filters=filt), 'lzma'
    it = int(os.environ.get('RD_ZOPFLI', '0'))
    if it > 0:
        try:
            import zopfli.gzip
            return zopfli.gzip.compress(cpio, numiterations=it), 'zopfli(%d)' % it
        except ImportError:
            pass
    return gzip.compress(cpio, compresslevel=9, mtime=0), 'gzip -9'


def add_stock_avb_footer(img, stock_raw):
    """Append the STOCK vbmeta blob + AVB footer (like Magisk does): the hash in it no longer
    matches, which an unlocked bootloader accepts (orange state), but the partition keeps a
    valid footer layout. Returns the image padded to the full partition size."""
    if len(stock_raw) < 64 or stock_raw[-64:-60] != b'AVBf':
        return img
    (_maj, _min, _orig, vb_off, vb_size) = struct.unpack('>2I3Q', stock_raw[-60:-28])
    vbmeta = stock_raw[vb_off:vb_off + vb_size]
    if vbmeta[:4] != b'AVB0':
        return img
    out = bytearray(img)
    out += b'\0' * (align(len(out), 4096) - len(out))
    off = len(out)
    out += vbmeta
    if len(out) + 64 > PART_SIZE:
        return bytes(out)        # caller reports TOO BIG
    out += b'\0' * (PART_SIZE - 64 - len(out))
    footer = b'AVBf' + struct.pack('>2I3Q', 1, 0, len(img), off, len(vbmeta))
    out += footer + b'\0' * (64 - len(footer))
    return bytes(out)


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'info':
        b = Boot(open(sys.argv[2], 'rb').read())
        print('header v%d page %d kernel %d ramdisk %d (%s) dtb %d, payload %d of %d bytes' %
              (b.version, b.page_size, b.kernel_size, b.ramdisk_size, b.ramdisk[:4].hex(), b.dtb_size,
               b.payload_end, PART_SIZE))
        print('cmdline:', b.cmdline.split(b'\0')[0].decode(errors='replace'))
        return
    if cmd != 'inject':
        print(__doc__); sys.exit(1)

    stock_path, src_path, out_path = sys.argv[2:5]
    stock = Boot(open(stock_path, 'rb').read())
    src = open(src_path, 'rb').read()
    fox_rd = Boot(src).ramdisk if src[:8] == b'ANDROID!' else src

    stock_entries = cpio_parse(decompress(stock.ramdisk))
    fox_entries = cpio_parse(decompress(fox_rd))

    keep = [e for e in stock_entries if under(e[0], KEEP_FROM_STOCK)]
    if not keep:
        raise SystemExit('stock ramdisk has no first_stage_ramdisk?!')
    fox = [e for e in fox_entries if not under(e[0], KEEP_FROM_STOCK)]
    log = lambda s: print(s, flush=True)
    removed = set()
    here = os.path.dirname(os.path.abspath(__file__))
    # tier 1 is always applied; further tiers only while the image is still too big
    tiers = os.environ.get('RD_TRIM', ':'.join(os.path.join(here, f) for f in
                           ('ramdisk_trim.txt', 'ramdisk_trim_2.txt', 'ramdisk_trim_3.txt'))).split(':')
    tiers = [t for t in tiers if t and os.path.exists(t)] or [None]
    stock_raw = open(stock_path, 'rb').read()
    for i, rules in enumerate(tiers):
        if rules:
            log('== applying %s' % os.path.basename(rules))
            fox, rem = trim(fox, rules, log)
            removed |= rem
        if i == 0:
            fox = strip_elfs(fox, os.environ.get('OBJCOPY'), log)
        merged = fix_file_lists(fox + keep, removed)
        names = {norm(e[0]) for e in merged}
        for must in ('init', 'system/bin/recovery', 'system/bin/keystore2', 'system/bin/adbd',
                     'system/bin/fastbootd', 'twres/fonts/Roboto-Regular.ttf', 'twres/languages/en.xml',
                     'twres/languages/ru.xml', 'vendor/bin/teed',
                     'first_stage_ramdisk/fstab.mt6768', 'first_stage_ramdisk/system/bin/snapuserd'):
            if must not in names:
                raise SystemExit('merged ramdisk is missing %s' % must)
        cpio = cpio_write(merged)
        comp, how = compress(cpio)
        img = stock.build(comp)
        # keep RD_RESERVE bytes free for Magisk (its overlay + less dense recompression)
        reserve = int(os.environ.get('RD_RESERVE', '0'))
        fits = len(add_stock_avb_footer(img + b'\0' * reserve, stock_raw)) <= PART_SIZE
        log('ramdisk after tier %d: cpio %d bytes -> %s %d bytes, image %s (over by %d bytes)'
            % (i + 1, len(cpio), how, len(comp), 'FITS' if fits else 'too big',
               max(0, len(img) + 8192 - PART_SIZE)))
        if fits:
            break

    # verification: re-parse, compare kernel/dtb/cmdline and stock first-stage files
    chk = Boot(img)
    assert chk.kernel == stock.kernel and chk.dtb == stock.dtb and chk.cmdline == stock.cmdline
    chk_entries = {norm(n): d for n, f, d in cpio_parse(decompress(chk.ramdisk))}
    for n, f, d in keep:
        assert chk_entries[norm(n)] == d, 'first-stage file changed: ' + n

    payload_len = len(img)
    img = add_stock_avb_footer(img, open(stock_path, 'rb').read())
    if len(img) > PART_SIZE:
        raise SystemExit('TOO BIG: %d bytes > boot partition %d (ramdisk gz %d bytes, need to cut %d bytes)' %
                         (len(img), PART_SIZE, len(comp), len(img) - PART_SIZE))
    open(out_path, 'wb').write(img)
    print('OK: %s payload %d bytes (%d%% of boot partition), stock AVB footer kept; ramdisk cpio %d -> gzip %d; kept %d stock first-stage entries'
          % (out_path, payload_len, 100 * payload_len // PART_SIZE, len(cpio), len(comp), len(keep)))


if __name__ == '__main__':
    main()
