from setuptools import setup

setup(name='faros-streamer',
      version='1.0.0',
      description='Stream Faros (http://www.megaemg.com/products/faros/) data using the Lab Streaming Layer (LSL) (https://github.com/sccn/labstreaminglayer).',
      author='Andreas Henelius, Brain Work Research Center at the Finnish Institute of Occupational Health',
      author_email='andreas.henelius@ttl.fi',
      url='https://github.com/bwrc/faros-streamer-2',
      license='MIT',
      packages=['faros_streamer'],
      package_dir={'faros_streamer': 'faros_streamer'},
      include_package_data=False,
      install_requires = ['pylsl>=1.10.4',
                          'pybluez>=0.22',
                          'construct>=2.5.2',
                          'crc16>=0.1.1'],
      entry_points={"console_scripts":
                    ["faros = faros_streamer_cli"]}
)
