#!/usr/bin/python3
# test_driver_updates.py - unittests for driver_updates.py

import unittest
import unittest.mock as mock

import os
import tempfile
import shutil

from driver_updates import copy_files, move_files, iter_files, ensure_dir
from driver_updates import append_line, mkdir_seq

def touch(path):
    try:
        open(path, 'x')
    except FileExistsError:
        pass

def makedir(path):
    ensure_dir(path)
    return path

def makefile(path):
    makedir(os.path.dirname(path))
    touch(path)
    return path

def makefiles(*paths):
    return [makefile(p) for p in paths]

class FileTestCaseBase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_driver_updates.")
        self.srcdir = self.tmpdir+'/src/'
        self.destdir = self.tmpdir+'/dest/'

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def makefiles(self, *paths):
        return [makefile(os.path.normpath(self.tmpdir+'/'+p)) for p in paths]

class SelfTestCase(FileTestCaseBase):
    def test_makefiles(self):
        """check test helpers"""
        filepaths = ["sub/dir/test.file", "testfile"]
        self.makefiles(*filepaths)
        for f in filepaths:
            self.assertTrue(os.path.exists(self.tmpdir+'/'+f))

class TestCopyFiles(FileTestCaseBase):
    def test_basic(self):
        """copy_file: copy files into destdir, leaving existing contents"""
        files = self.makefiles("src/file1", "src/subdir/file2")
        self.makefiles("dest/file3")
        copy_files(files, self.destdir)
        result = set(os.listdir(self.destdir))
        self.assertEqual(result, set(["file1", "file2", "file3"]))

    def test_overwrite(self):
        """copy_file: overwrite files in destdir if they have the same name"""
        src, dest = self.makefiles("src/file1", "dest/file1")
        with open(src, 'w') as outf:
            outf.write("srcfile")
        with open(dest, 'w') as outf:
            outf.write("destfile")
        copy_files([src], self.destdir)
        self.assertEqual(os.listdir(self.destdir), ["file1"])
        self.assertEqual(open(dest).read(), "srcfile")

    def test_samefile(self):
        """copy_file: skip files already in destdir"""
        (dest,) = self.makefiles("dest/file1")
        with open(dest, 'w') as outf:
            outf.write("destfile")
        copy_files([dest], self.destdir)
        self.assertEqual(os.listdir(self.destdir), ["file1"])
        self.assertEqual(open(dest).read(), "destfile")

    def test_copy_to_parent(self):
        """copy_file: skip files in subdirs of destdir"""
        files = self.makefiles("dest/subdir/file1")
        copy_files(files, self.destdir)
        self.assertEqual(list(iter_files(self.destdir)), files)

class TestIterFiles(FileTestCaseBase):
    def test_basic(self):
        """iter_files: iterates over full paths to files under topdir"""
        files = set(self.makefiles("src/file1", "dest/file2", "src/sub/file3"))
        makedir(self.tmpdir+'/empty/dir')
        result = set(iter_files(self.tmpdir))
        self.assertEqual(files, result)

    def test_pattern(self):
        """iter_files: match filename against glob pattern"""
        self.makefiles("src/file1.so", "src/sub.ko/file2")
        goodfiles = set(self.makefiles("src/sub/file1.ko", "src/file2.ko.xz"))
        result = set(iter_files(self.tmpdir, pattern="*.ko*"))
        self.assertEqual(result, goodfiles)

class TestMoveFiles(FileTestCaseBase):
    def test_basic(self):
        """move_files: move files to destdir"""
        files = self.makefiles("src/file1", "src/subdir/file2")
        move_files(files, self.destdir)
        self.assertEqual(set(os.listdir(self.destdir)), set(["file1", "file2"]))
        self.assertEqual(list(iter_files(self.srcdir)), [])

    def test_overwrite(self):
        """move_files: overwrite files with the same name"""
        src, dest = self.makefiles("src/file1", "dest/file1")
        with open(src, 'w') as outf:
            outf.write("srcfile")
        with open(dest, 'w') as outf:
            outf.write("destfile")
        move_files([src], self.destdir)
        self.assertEqual(os.listdir(self.destdir), ["file1"])
        self.assertEqual(open(dest).read(), "srcfile")
        self.assertEqual(list(iter_files(self.srcdir)), [])

    def test_samefile(self):
        """move_files: leave files alone if they're already in destdir"""
        (dest,) = self.makefiles("dest/file1")
        with open(dest, 'w') as outf:
            outf.write("destfile")
        move_files([dest], self.destdir)
        self.assertEqual(os.listdir(self.destdir), ["file1"])
        self.assertEqual(open(dest).read(), "destfile")

    def test_move_to_parent(self):
        """move_files: leave files alone if they're in a subdir of destdir"""
        files = set(self.makefiles("dest/subdir/file1", "dest/file2"))
        move_files(files, self.destdir)
        self.assertEqual(set(iter_files(self.destdir)), files)

class TestAppendLine(FileTestCaseBase):
    def test_empty(self):
        """append_line: create file + append \\n when needed"""
        line = "this is a line of text with no newline"
        outfile = self.tmpdir+'/outfile'
        append_line(outfile, line)
        self.assertEqual(open(outfile).read(), line+'\n')

    def test_append(self):
        """append_line: adds a line to the end of an existing file"""
        oldlines = ["line one", "line two", "and I'm line three"]
        outfile = self.tmpdir+'/outfile'
        with open(outfile, 'w') as outf:
            for line in oldlines:
                outf.write(line+'\n')
        line = "this line contains a newline already\n"
        append_line(outfile, line)
        self.assertEqual(open(outfile).read(), '\n'.join(oldlines+[line]))

from driver_updates import read_lines
class TestReadLine(FileTestCaseBase):
    def test_empty(self):
        """read_lines: return [] for empty file"""
        [empty] = self.makefiles("emptyfile")
        self.assertEqual(read_lines(empty), [])

    def test_missing(self):
        """read_lines: return [] for missing file"""
        self.assertEqual(read_lines(self.tmpdir+'/no-such-file'),[])

    def test_readlines(self):
        """read_lines: returns a list of lines without trailing newlines"""
        filedata = 'line one\nline two\n\nline four\n'
        outfile = self.tmpdir+'/outfile'
        with open(outfile, 'w') as outf:
            outf.write(filedata)
        lines = read_lines(outfile)
        self.assertEqual(lines, ['line one', 'line two','','line four'])

class TestMkdirSeq(FileTestCaseBase):
    def test_basic(self):
        """mkdir_seq: first dir ends with 1"""
        newdir = mkdir_seq(self.srcdir+'/DD-')
        self.assertEqual(newdir, self.srcdir+'/DD-1')
        self.assertTrue(os.path.isdir(newdir))

    def test_one_exists(self):
        """mkdir_seq: increment number if file exists"""
        firstdir = mkdir_seq(self.srcdir+'/DD-')
        newdir = mkdir_seq(self.srcdir+'/DD-')
        self.assertEqual(newdir, self.srcdir+'/DD-2')
        self.assertTrue(os.path.isdir(newdir))
        self.assertTrue(os.path.isdir(firstdir))

from driver_updates import find_repos, save_repo, arch
# As far as we know, this is what makes a valid repo: rhdd3 + rpms/`uname -m`/
def makerepo(topdir, desc=None):
    descfile = makefile(topdir+'/rhdd3')
    if not desc:
        desc = os.path.basename(topdir)
    with open(descfile, "w") as outf:
        outf.write(desc+"\n")
    makedir(topdir+'/rpms/'+arch)

class TestFindRepos(FileTestCaseBase):
    def test_basic(self):
        """find_repos: return RPM dir if a valid repo is found"""
        makerepo(self.tmpdir)
        repos = find_repos(self.tmpdir)
        self.assertEqual(repos, [self.tmpdir+'/rpms/'+arch])
        self.assertTrue(os.path.isdir(repos[0]))

    def test_multiple_subdirs(self):
        """find_repos: descend multiple subdirs if needed"""
        makerepo(self.tmpdir+'/driver1')
        makerepo(self.tmpdir+'/sub/driver1')
        makerepo(self.tmpdir+'/sub/driver2')
        repos = find_repos(self.tmpdir)
        self.assertEqual(len(repos),3)

class TestSaveRepo(FileTestCaseBase):
    def test_basic(self):
        """save_repo: copies a directory to /run/install/DD-X"""
        makerepo(self.srcdir)
        [repo] = find_repos(self.srcdir)
        makefile(repo+'/fake-something.rpm')
        saved = save_repo(repo, target=self.destdir)
        self.assertEqual(set(os.listdir(saved)), set(["fake-something.rpm"]))
        self.assertEqual(saved, os.path.join(self.destdir, "DD-1"))

from driver_updates import mount, umount, mounted
class MountTestCase(unittest.TestCase):
    @mock.patch('driver_updates.mkdir_seq')
    @mock.patch('driver_updates.subprocess.check_call')
    def test_basic(self, check_call, mkdir):
        """mount: calls mount(8), makes mountpoint if needed"""
        dev, mnt = '/dev/fake', '/media/DD-1'
        mkdir.return_value = mnt
        mountpoint = mount(dev)
        mkdir.assert_called_once_with('/media/DD-')
        check_call.assert_called_once_with(["mount", dev, mnt])
        self.assertEqual(mnt, mountpoint)

    @mock.patch('driver_updates.mkdir_seq')
    @mock.patch('driver_updates.subprocess.check_call')
    def test_options(self, check_call, mkdir):
        """mount: correctly adds "-o options" if options are added"""
        dev, mnt = '/dev/fake', '/media/fake'
        mount(dev, mnt, options="spicy")
        check_call.assert_called_once_with(["mount", dev, mnt, "-o", "spicy"])
        self.assertFalse(mkdir.called)

    @mock.patch('driver_updates.subprocess.call')
    def test_umount(self, call):
        """umount: calls umount(8)"""
        mnt = '/mnt/fake'
        umount(mnt)
        call.assert_called_once_with(["umount", mnt])

    @mock.patch('driver_updates.mount')
    @mock.patch('driver_updates.umount')
    def test_mount_manager(self, mock_umount, mock_mount):
        """mounted: context manager mounts/umounts as expected"""
        dev, mnt = '/dev/fake', '/media/fake'
        mock_mount.return_value = mnt
        with mounted(dev, mnt) as mountpoint:
            mock_mount.assert_called_once_with(dev, mnt, None)
            self.assertFalse(mock_umount.called)
            self.assertEqual(mountpoint, mnt)
        mock_umount.assert_called_once_with(dev)

# NOTE: dd_list and dd_extract get tested pretty thoroughly in tests/dd_tests,
# so this is a slightly higher-level test case
from driver_updates import dd_list, dd_extract, Driver
fake_module = Driver(
    source='/repo/path/to/fake-driver-1.0-1.rpm',
    name='fake-driver',
    flags='modules firmwares',
    description='Wow this is totally a fake driver.\nHooray for this',
    repo='/repo/path/to'
)
fake_enhancement = Driver(
    source='/repo/path/to/fake-enhancement-1.0-1.rpm',
    name='fake-enhancement',
    flags='binaries libraries',
    description='This is enhancing the crap out of the installer.\n\nYeah.',
    repo=fake_module.repo
)
def dd_list_output(driver):
    out='{0.source}\n{0.name}\n{0.flags}\n{0.description}\n---\n'.format(driver)
    return out.encode('utf-8')

class DDUtilsTestCase(unittest.TestCase):
    @mock.patch("driver_updates.subprocess.check_output")
    def test_dd_list(self, check_output):
        """dd_list: returns a list of Driver objects parsed from output"""
        output = dd_list_output(fake_module)+dd_list_output(fake_enhancement)
        check_output.return_value = output
        anaconda, kernel = '19.0', os.uname()[2]
        result = dd_list(fake_module.repo)
        cmd = check_output.call_args[0][0]
        self.assertIn(kernel, cmd)
        self.assertIn(anaconda, cmd)
        self.assertIn(fake_module.repo, cmd)
        self.assertTrue(cmd[0].endswith("dd_list"))
        self.assertEqual(len(result), 2)
        mod, enh = sorted(result, key=lambda d: d.name)
        self.assertEqual(mod.__dict__, fake_module.__dict__)
        self.assertEqual(enh.__dict__, fake_enhancement.__dict__)

    @mock.patch("driver_updates.subprocess.check_output")
    def test_dd_extract(self, check_output):
        """dd_extract: call binary with expected arguments"""
        rpm = "/some/kind/of/path.rpm"
        outdir = "/output/dir"
        dd_extract(rpm, outdir)
        cmd = check_output.call_args[0][0]
        self.assertIn(os.uname()[2], cmd)
        self.assertIn(rpm, cmd)
        self.assertIn(outdir, cmd)
        self.assertIn("-blmf", cmd)
        self.assertTrue(cmd[0].endswith("dd_extract"))

from driver_updates import extract_repo, grab_driver_files, load_drivers

class ExtractRepoTestCase(unittest.TestCase):
    @mock.patch("driver_updates.append_line")
    @mock.patch("driver_updates.dd_extract")
    @mock.patch("driver_updates.dd_list")
    def test_basic(self, mock_dd_list, mock_dd_extract, mock_append_line):
        """extract_repo: extract drivers listed by dd_list and write pkglist"""
        mock_dd_list.return_value = [fake_enhancement, fake_module]
        repo = "/some/repo/path"
        extract_repo(repo)
        mock_dd_list.assert_called_once_with(repo)
        # extracts all listed modules
        mock_dd_extract.assert_has_calls([
            mock.call(fake_enhancement.source, "/updates"),
            mock.call(fake_module.source, "/updates")
        ], any_order=True)
        pkglist = "/run/install/dd_packages"
        mock_append_line.assert_called_once_with(pkglist, fake_module.name)

class GrabDriverFilesTestCase(FileTestCaseBase):
    def test_basic(self):
        """grab_drivers: copy drivers into place, return module list"""
        # create a bunch of fake extracted files
        outdir = self.tmpdir + '/extract-outdir'
        moddir = outdir + "/lib/modules/%s/kernel/" % os.uname()[2]
        fwdir = outdir + "/lib/firmware/"
        modules = makefiles(moddir+"net/funk.ko", moddir+"fs/lolfs.ko.xz")
        firmware = makefiles(fwdir+"funk.fw")
        makefiles(outdir+"/usr/bin/monkey", outdir+"/other/dir/blah.ko")
        mod_upd_dir = self.tmpdir+'/module-updates'
        fw_upd_dir = self.tmpdir+'/fw-updates'
        # use our updates dirs instead of the default updates dirs
        with mock.patch.multiple("driver_updates",
                                 module_updates_dir=mod_upd_dir,
                                 firmware_updates_dir=fw_upd_dir):
            modnames = grab_driver_files(outdir)
        self.assertEqual(set(modnames), set(["funk", "lolfs"]))
        modfiles = set(['funk.ko', 'lolfs.ko.xz'])
        fwfiles = set(['funk.fw'])
        # modules/firmware are *not* in their old locations
        self.assertEqual([f for f in modules+firmware if os.path.exists(f)], [])
        # modules are in the system's updates dir
        self.assertEqual(set(os.listdir(mod_upd_dir)), modfiles)
        # modules are also in outdir's updates dir
        self.assertEqual(set(os.listdir(outdir+'/'+mod_upd_dir)), modfiles)
        # repeat for firmware
        self.assertEqual(set(os.listdir(fw_upd_dir)), fwfiles)
        self.assertEqual(set(os.listdir(outdir+'/'+fw_upd_dir)), fwfiles)

class LoadDriversTestCase(unittest.TestCase):
    @mock.patch("driver_updates.subprocess.call")
    def test_basic(self, call):
        """load_drivers: runs depmod and modprobes all named modules"""
        modnames = ['mod1', 'mod2']
        load_drivers(modnames)
        call.assert_has_calls([
            mock.call(["depmod", "-a"]),
            mock.call(["modprobe", "-a"] + modnames)
        ])

from driver_updates import process_driver_disk
class ProcessDriverDisk(unittest.TestCase):
    def setUp(self):
        # an iterable that returns fake mountpoints, for mocking mount()
        self.fakemount = ["/mnt/DD-%i" % n for n in range(1,10)]
        # a function that returns a couple of fake repos, for find_repos()
        self.fakerepos = lambda m: [m+'/repo1', m+'/repo/2']
        # a set of directory listings to be returned by os.listdir
        self.dir_listings = {
            '/mnt/DD-1': ['README', 'EATME'],
            '/mnt/DD-2': ['README', 'COPYING'],
            '/mnt/DD-3': ['Windows95']
        }
        listdir = self.dir_listings.get
        # a context-manager object to be returned by the mock mounted()
        mounted_ctx = mock.MagicMock(
            __enter__=mock.MagicMock(side_effect=self.fakemount), # mount
            __exit__=mock.MagicMock(return_value=None),           # umount
        )
        # set up our patches
        patches = (
            mock.patch("driver_updates.mounted", return_value=mounted_ctx),
            mock.patch("driver_updates.find_repos", side_effect=self.fakerepos),
            mock.patch("driver_updates.os.listdir", side_effect=listdir),
            mock.patch("driver_updates.save_repo"),
            mock.patch("driver_updates.extract_repo"),
        )
        self.mocks = {p.attribute:p.start() for p in patches}
        for p in patches: self.addCleanup(p.stop)

    def test_basic(self):
        """process_driver_disk: mount a device and extract all its repos"""
        dev = '/dev/fake'
        process_driver_disk(dev)
        # did we mount the initial device, and then the .iso we find therein?
        self.mocks['mounted'].assert_called_once_with(dev, options=None)
        allrepos = [mock.call(r) for r in self.fakerepos('/mnt/DD-1')]
        self.mocks['save_repo'].assert_has_calls(allrepos)
        self.mocks['extract_repo'].assert_has_calls(allrepos)

    def test_recursive(self):
        """process_driver_disk: recursively process .isos at toplevel"""
        dev = '/dev/fake'
        self.dir_listings['/mnt/DD-1'].append('magic.iso')
        self.dir_listings['/mnt/DD-2'].append('another.iso')
        process_driver_disk(dev)
        # did we mount the initial device, and then the .isos we find therein?
        self.mocks['mounted'].assert_has_calls([
            mock.call(dev, options=None),
            mock.call('/mnt/DD-1/magic.iso', options="loop"),
            mock.call('/mnt/DD-2/another.iso', options="loop"),
        ])
        mounts = self.fakemount[:2]
        allrepos = [mock.call(r) for m in mounts for r in self.fakerepos(m)]
        self.mocks['save_repo'].assert_has_calls(allrepos)
        self.mocks['extract_repo'].assert_has_calls(allrepos)

from driver_updates import handle_dd
class HandleDDTestCase(unittest.TestCase):
    def setUp(self):
        self.all_finished = False
        self.modlist = []
        patches = (
            mock.patch('driver_updates.process_driver_disk'),
            mock.patch('driver_updates.load_drivers'),
            mock.patch('driver_updates.mark_finished'),
            mock.patch('driver_updates.append_line'),
            mock.patch('driver_updates.grab_driver_files',
                                side_effect=lambda: self.modlist),
            mock.patch('driver_updates.all_finished',
                                side_effect=lambda: self.all_finished),
        )
        self.mocks = {p.attribute:p.start() for p in patches}
        for p in patches: self.addCleanup(p.stop)

    def test_basic(self):
        """handle_dd: process, grab + load drivers, check if finished"""
        diskstr = "LABEL=OEMDRV"
        dev = "/dev/sr0"
        self.modlist = ['module', 'anotherone']
        handle_dd("--disk", diskstr, dev)
        self.mocks['process_driver_disk'].assert_called_once_with(dev)
        self.mocks['grab_driver_files'].assert_called_once_with()
        self.mocks['load_drivers'].assert_called_once_with(self.modlist)
        self.mocks['mark_finished'].assert_called_once_with(diskstr)
        self.assertFalse(self.mocks['append_line'].called)

    def test_done(self):
        """handle_dd: check that /tmp/dd.done gets written when finished"""
        url = "http://some.url/wowzers"
        iso = "/tmp/download/driver.iso"
        self.modlist = ['drivers', 'aplenty']
        self.all_finished = True
        handle_dd("--net", url, iso)
        self.mocks['process_driver_disk'].assert_called_once_with(iso, mount_opts="loop")
        self.mocks['grab_driver_files'].assert_called_once_with()
        self.mocks['load_drivers'].assert_called_once_with(self.modlist)
        self.mocks['mark_finished'].assert_called_once_with(url)
        self.mocks['append_line'].assert_called_once_with("/tmp/dd.done", "true")

from driver_updates import all_finished, mark_finished

class FinishedTestCase(FileTestCaseBase):
    def test_mark_finished(self):
        """mark_finished: appends a line to /tmp/dd_finished"""
        requeststr = "WOW SOMETHING OR OTHER"
        mark_finished(requeststr, topdir=self.tmpdir)
        finished = self.tmpdir+'/dd_finished'
        self.assertTrue(os.path.exists(finished))
        self.assertEqual(read_lines(finished), [requeststr])

    def test_all_finished(self):
        """all_finished: True iff all lines from dd_todo are in dd_finished"""
        todo = self.tmpdir+'/dd_todo'
        requests = ['one', 'two', 'final thingy']
        with open(todo, 'w') as outf:
            outf.write(''.join(r+'\n' for r in requests))
        for r in reversed(requests):
            self.assertFalse(all_finished(topdir=self.tmpdir))
            mark_finished(r, topdir=self.tmpdir)
        self.assertTrue(all_finished(topdir=self.tmpdir))

blkid_output = b'''\
DEVNAME=/dev/sda2
UUID=0f21a3d1-dcd3-4ab4-a292-c5556850d561
TYPE=ext4

DEVNAME=/dev/sda1
UUID=C53C-EE46
TYPE=vfat

DEVNAME=/dev/sda3
UUID=4126dbb6-c7d3-47b4-b1fc-9bb461df0067
TYPE=btrfs

DEVNAME=/dev/loop0
UUID=6f16967e-0388-4276-bd8d-b88e5b217a55
TYPE=ext4
'''
disk_labels = {
    '/dev/sdb1': 'metroid_srv',
    '/dev/loop0': 'I\\x20\u262d\\x20COMMUNISM',
    '/dev/sda3': 'metroid_root'
}
from driver_updates import get_deviceinfo
class TestDeviceInfo(unittest.TestCase):
    @mock.patch('driver_updates.subprocess.check_output')
    @mock.patch('driver_updates.get_disk_labels')
    def test_basic(self, get_disk_labels, check_output):
        """get_deviceinfo: parses DeviceInfo from blkid etc."""
        # configure mock objects
        check_output.return_value = blkid_output
        get_disk_labels.return_value = disk_labels
        # now we're getting mock deviceinfo, whee
        disks = get_deviceinfo()
        self.assertEqual(len(disks), 4)
        disks.sort(key=lambda d: d.device)
        loop, efi, boot, root = disks
        self.assertEqual(root.device, '/dev/sda3')
        self.assertEqual(efi.uuid, 'C53C-EE46')
        self.assertEqual(boot.fs_type, 'ext4')
        self.assertEqual(loop.label, 'I\\x20\u262d\\x20COMMUNISM')

# yeab bud let's do this... .. .,,,.
from driver_updates import TextMenu, interactive

# NOTE: mock out __builtin__.input and we can script this fokker...
