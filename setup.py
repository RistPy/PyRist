from setuptools import setup, find_packages


version = "1.2.1"

with open("README.md", "r") as f:
  long_description = f.read()

if version.endswith(('a', 'b', 'rc')):
  # append version identifier based on commit count
  try:
    import subprocess
    p = subprocess.Popen(['git', 'rev-list', '--count', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if out:
      version += out.decode('utf-8').strip()
    p = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if out:
      version += '+g' + out.decode('utf-8').strip()
  except Exception:
    pass

setup(
  name="RistLang",
  version=version,
  description="A module for compiling RistLang",
  long_description=long_description,
  long_description_content_type="text/markdown",
  license="MIT",
  python_requires=">=3.8",
  entry_points={'console_scripts': ['rist=ristpy.__main__:main']},
  install_requires=["import_expression"],
  packages=find_packages(exclude=[".github", "examples"]),
  classifiers=[
    "Programming Language :: Python",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
  ],
  project_urls={
    "Issue tracker": "https://github.com/RistPy/PyRist/issues"
  },
  url="https://github.com/RistPy/PyRist"
)
