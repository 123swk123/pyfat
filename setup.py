import distutils.core
from distutils.command.sdist import sdist as _sdist
import subprocess
import time

VERSION='0.1.0'
RELEASE='0'

class sdist(_sdist):
    ''' custom sdist command, to prep pyfat.spec file for inclusion '''

    def run(self):
        global VERSION
        global RELEASE

        # Create a development release string for later use
        git_head = subprocess.Popen("git log -1 --pretty=format:%h",
                                    shell=True,
                                    stdout=subprocess.PIPE).communicate()[0].strip()
        date = time.strftime("%Y%m%d%H%M%S", time.gmtime())
        git_release = "%sgit%s" % (date, git_head)

        # Expand macros in pyfat.spec.in and create pyfat.spec
        spec_in = open('pyfat.spec.in', 'r')
        spec = open('pyfat.spec', 'w')
        for line in spec_in.xreadlines():
            if "@VERSION@" in line:
                line = line.replace("@VERSION@", VERSION)
            elif "@RELEASE@" in line:
                # If development release, include date+githash in %{release}
                if RELEASE.startswith('0'):
                    RELEASE += '.' + git_release
                line = line.replace("@RELEASE@", RELEASE)
            spec.write(line)
        spec_in.close()
        spec.close()

        # Run parent constructor
        _sdist.run(self)

distutils.core.setup(name='pyfat',
                     version=VERSION,
                     description='Pure python FAT manipulation library',
                     url='http://github.com/clalancette/pyfat',
                     author='Chris Lalancette',
                     author_email='clalancette@gmail.com',
                     license='LGPLv2',
                     classifiers=['Development Status :: 4 - Beta',
                                  'Intended Audience :: Developers',
                                  'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
                                  'Natural Language :: English',
                                  'Programming Language :: Python :: 2',
                     ],
                     keywords='FAT FAT12 FAT16 FAT32',
                     py_modules=['pyfat'],
                     cmdclass={'sdist': sdist},
)
